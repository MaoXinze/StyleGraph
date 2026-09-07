"""检索与推荐引擎：混合检索（向量+图）、搭配推荐（多跳图扩展）、GraphRAG 问答。"""

import base64
import logging
import tempfile
from pathlib import Path

from mmkg.config import Settings

log = logging.getLogger(__name__)

PRODUCT_CARD = """{asin: .asin, title: .title, price: .price, rating: .rating,
rating_count: .rating_count, image_url: .image_url, store: .store}"""

_VISUAL_SEARCH = """
CALL db.index.vector.queryNodes('product_image_vec', $k, $vec)
YIELD node, score
WHERE ($facet_key IS NULL OR EXISTS {
  MATCH (node)-[:HAS_ATTRIBUTE]->(a:AttributeValue) WHERE a.key = $facet_key })
RETURN node{.asin, .title, .price, .rating, .rating_count, .image_url, .store} AS product,
       score ORDER BY score DESC LIMIT $k
"""

_TEXT_SEARCH = """
CALL db.index.vector.queryNodes('product_text_vec', $k, $vec)
YIELD node, score
RETURN node{.asin, .title, .price, .rating, .rating_count, .image_url, .store} AS product,
       score ORDER BY score DESC LIMIT $k
"""

# 搭配推荐：直接共购 + 类目亲和两跳扩展，Python 侧融合排序
_RECO_ANCHOR = """
MATCH (p:Product {asin: $asin})
OPTIONAL MATCH (p)-[co:CO_PURCHASED]-(cp:Product)
WITH p, coalesce(collect(DISTINCT cp.asin), []) AS copurchase
RETURN p{.*} AS anchor, copurchase
"""

_RECO_AFFINITY = """
MATCH (p:Product {asin: $asin})-[:IN_CATEGORY]->(c:Category {level:2})
MATCH (c)-[aff:CAT_AFFINITY]->(c2:Category {level:2})
WHERE c2.id <> c.id
MATCH (cand:Product)-[:IN_CATEGORY]->(c2)
WHERE cand.rating_count >= 5 AND cand.embed_status = 'ok'
RETURN c2.name AS cat, aff.weight AS affw,
       cand{.*} AS product
ORDER BY affw DESC, cand.rating_count DESC
LIMIT $pool
"""

_INTENT_SYSTEM = """你是电商导购查询理解引擎。把用户的中文自然语言解析为 JSON 查询意图，只输出 JSON：
{"category": "英文品类词或null", "gender": "men/women/unisex/kids或null", "color": "英文颜色或null",
 "occasion": "casual/party/work/date/outdoor/sport/travel/home/formal或null",
 "price_max": 数字或null, "price_min": 数字或null, "keywords": ["补充英文关键词，最多3个"]}
用户可能混中英文，需翻译成英文规范值；不确定的字段一律 null，不要编造。"""

_INTENT_QUERY = """
MATCH (p:Product)
WHERE ($price_min IS NULL OR p.price >= $price_min)
  AND ($price_max IS NULL OR p.price <= $price_max)
  AND ($gender IS NULL OR EXISTS {
      MATCH (p)-[:HAS_ATTRIBUTE]->(g:AttributeValue) WHERE g.key = 'gender:' + $gender })
  AND ($color IS NULL OR EXISTS {
      MATCH (p)-[:HAS_ATTRIBUTE]->(c:AttributeValue) WHERE c.key = 'color:' + $color })
  AND ($occasion IS NULL OR EXISTS {
      MATCH (p)-[:SUITABLE_FOR]->(o:Occasion) WHERE o.name = $occasion })
  AND ($item_type IS NULL OR EXISTS {
      MATCH (p)-[:HAS_ATTRIBUTE]->(t:AttributeValue)
      WHERE t.facet = 'item_type' AND t.value CONTAINS $item_type })
WITH p, ($gender IS NULL AND $color IS NULL AND $occasion IS NULL AND $item_type IS NULL) AS no_attr
WHERE NOT no_attr OR
      any(kw IN $keywords WHERE toLower(p.title) CONTAINS kw)
RETURN p{.*} AS product
ORDER BY p.rating_count DESC LIMIT 12
"""

_FALLBACK_TEXT_QUERY = """
CALL db.index.vector.queryNodes('product_text_vec', 12, $vec)
YIELD node, score
RETURN node{.asin, .title, .price, .rating, .rating_count, .image_url, .store} AS product,
       score ORDER BY score DESC
"""


class SearchEngine:
    """无状态检索服务；CLIP 编码器懒加载（首次以图搜款/文本检索时载入 GPU）。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        from mmkg.graph import Neo4jStore

        self.store = Neo4jStore.from_settings(settings)
        self._encoder = None

    @property
    def encoder(self):
        if self._encoder is None:
            from mmkg.embeddings.clip import ClipEncoder

            self._encoder = ClipEncoder(self.settings.clip_model, self.settings.clip_pretrained)
        return self._encoder

    def close(self):
        self.store.close()

    def _embed_ready(self) -> bool:
        """向量索引是否有数据（避免向量未就绪时触发 CLIP 懒加载/权重下载而挂起）。"""
        rows = self.store.run(
            "MATCH (p:Product {embed_status:'ok'}) WITH count(p) AS c LIMIT 1 RETURN c")
        return bool(rows and rows[0].get("c"))

    # —— 检索 ——

    def visual_search(self, image_bytes: bytes, top_k: int = 20) -> list[dict]:
        if not self._embed_ready():
            raise ValueError("向量索引未就绪：先运行 `uv run mmkg embed` 完成编码")
        tmp = Path(tempfile.gettempdir()) / "mmkg_query.jpg"
        tmp.write_bytes(image_bytes)
        vec = self.encoder.encode_images([tmp])[0]
        if vec is None:
            raise ValueError("无法解析上传的图片")
        return self.store.run(_VISUAL_SEARCH, vec=vec, k=top_k,
                              facet_key=None)

    def text_search(self, query: str, top_k: int = 12) -> list[dict]:
        if not self._embed_ready():
            log.info("向量索引未就绪（embed_ok=0），文本检索返回空结果")
            return []
        vec = self.encoder.encode_texts([query])[0]
        return self.store.run(_TEXT_SEARCH, vec=vec, k=top_k)

    # —— 搭配推荐 ——

    def recommend_outfit(self, asin: str, limit: int = 5) -> dict:
        anchor_row = self.store.run(_RECO_ANCHOR, asin=asin)
        if not anchor_row:
            raise ValueError(f"商品不存在: {asin}")
        anchor, copurchase = anchor_row[0]["anchor"], set(anchor_row[0]["copurchase"])

        pool = self.store.run(_RECO_AFFINITY, asin=asin, pool=limit * 12)
        scored: dict[str, dict] = {}
        for r in pool:
            p = r["product"]
            aid = p["asin"]
            s = min(r["affw"] / 30.0, 3.0) + (p["rating"] or 0) / 2 + min((p["rating_count"] or 0) / 2000, 1.0)
            if aid in copurchase:
                s += 4.0  # 直接共购强加权
            cur = scored.get(aid)
            if cur is None or s > cur["score"]:
                scored[aid] = {"product": {k: p.get(k) for k in
                                           ("asin", "title", "price", "rating", "rating_count",
                                            "image_url", "store")},
                               "category": r["cat"], "score": round(s, 3),
                               "co_purchased": aid in copurchase}
        items = sorted(scored.values(), key=lambda x: -x["score"])
        picked, seen_cats = [], {}
        for item in items:  # 类目多样性：每个目标类目最多 2 件
            c = item["category"]
            if seen_cats.get(c, 0) >= 2:
                continue
            seen_cats[c] = seen_cats.get(c, 0) + 1
            picked.append(item)
            if len(picked) >= limit:
                break
        return {"anchor": {k: anchor.get(k) for k in
                           ("asin", "title", "price", "rating", "image_url", "store")},
                "items": picked}

    # —— GraphRAG 问答 ——

    def chat(self, question: str) -> dict:
        from mmkg.llm import LLMClient

        client = LLMClient(self.settings)  # DeepSeek 纯文本（意图解析 + 生成回答）
        intent = client.chat_json(_INTENT_SYSTEM, question) or {}

        rows = self.store.run(
            _INTENT_QUERY,
            gender=intent.get("gender"), color=intent.get("color"),
            occasion=intent.get("occasion"), item_type=intent.get("category"),
            price_min=intent.get("price_min"), price_max=intent.get("price_max"),
            keywords=[k.lower() for k in (intent.get("keywords") or [])],
        )
        if not rows and self._embed_ready():  # 属性过滤无结果 → 向量文本召回兜底
            vec = self.encoder.encode_texts([question])[0]
            rows = self.store.run(_FALLBACK_TEXT_QUERY, vec=vec)

        products = [r["product"] for r in rows]
        ctx = json_dumps([{"title": p.get("title"), "price": p.get("price"),
                           "rating": p.get("rating"), "store": p.get("store")}
                          for p in products[:10]])
        answer = client.chat_json(
            "你是中文电商导购助手。根据检索到的商品候选（JSON）回答用户问题，"
            "用两三句话给出建议并解释理由（结合价格/评分/品类），不要编造候选之外的商品。"
            "最后输出 {\"answer\": \"...\"}。",
            f"用户问题：{question}\n候选商品：{ctx}") or {}
        return {"intent": intent, "products": products,
                "answer": answer.get("answer") or "以下是相关商品："}


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)
