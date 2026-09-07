"""FastAPI 应用：以图搜款 / 搭配推荐 / 导购问答 / 图谱探索 / 统计。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mmkg.config import bootstrap_env, get_settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_env()
    from fastapi.staticfiles import StaticFiles

    from mmkg.utils.logging import setup_logging
    from mmkg.retrieval import SearchEngine

    setup_logging()
    images_dir = get_settings().images_dir
    if images_dir.is_dir():  # 本地商品图静态服务（CDN 部分已 404，本地为权威源）
        app.mount("/img", StaticFiles(directory=str(images_dir)), name="images")
    app.state.engine = SearchEngine(get_settings())
    log.info("StyleGraph API 就绪")
    yield
    app.state.engine.close()


app = FastAPI(title="StyleGraph API", version="0.1.0",
              description="电商多模态知识图谱：以图搜款 · 搭配推荐 · 导购问答",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def stats():
    store = app.state.engine.store
    return {"nodes": store.counts(), "rels": store.rel_counts(), "server": store.server_info()}


@app.get("/api/products/{asin}")
def product_detail(asin: str):
    rows = app.state.engine.store.run(
        """
        MATCH (p:Product {asin: $asin})
        OPTIONAL MATCH (p)-[:HAS_BRAND]->(b:Brand)
        OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
        OPTIONAL MATCH (p)-[r:CO_PURCHASED]-(cp:Product)
        WITH p, b, collect(DISTINCT c{.name, .level}) AS cats,
             collect(DISTINCT {asin: cp.asin, title: cp.title, price: cp.price,
                               image_url: cp.image_url, w: r.weight})[0..8] AS copurchase
        OPTIONAL MATCH (p)-[:HAS_ATTRIBUTE]->(a:AttributeValue)
        OPTIONAL MATCH (p)-[:SUITABLE_FOR]->(o:Occasion)
        RETURN p{.*} AS product,
               b.name AS brand, cats, copurchase,
               collect(DISTINCT a{.facet, .value}) AS attributes,
               collect(DISTINCT o.name) AS occasions
        """,
        asin=asin,
    )
    if not rows:
        raise HTTPException(404, "商品不存在")
    return rows[0]


@app.post("/api/search/visual")
async def search_visual(file: UploadFile = File(...), top_k: int = Query(20, le=50)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "空文件")
    try:
        results = app.state.engine.visual_search(data, top_k=top_k)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"query_image": True, "note": "整图检索（多单品检测待 VLM 抽取启用后开放）", "results": results}


@app.get("/api/search/text")
def search_text(q: str, top_k: int = Query(12, le=30)):
    return {"query": q, "results": app.state.engine.text_search(q, top_k=top_k)}


@app.get("/api/recommend/outfit/{asin}")
def recommend_outfit(asin: str, limit: int = Query(5, le=10)):
    try:
        return app.state.engine.recommend_outfit(asin, limit=limit)
    except ValueError as e:
        raise HTTPException(404, str(e))


class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(400, "问题不能为空")
    return app.state.engine.chat(req.question.strip())


@app.get("/api/graph/explore")
def graph_explore(asin: str):
    """商品邻域子图（品牌/类目树/共购/属性/场合），纯 Cypher 实现（不依赖 APOC）。"""
    rows = app.state.engine.store.run_raw(
        """
        MATCH (p:Product {asin: $asin})
        OPTIONAL MATCH (p)-[r1:HAS_BRAND|IN_CATEGORY|CO_PURCHASED|HAS_ATTRIBUTE|SUITABLE_FOR]-(n1)
        WITH p, collect(DISTINCT n1) AS n1s, collect(DISTINCT r1) AS r1s
        OPTIONAL MATCH tree = (anc:Category)-[:PARENT_OF*0..2]->(c1)
        WHERE c1 IN [n IN n1s WHERE 'Category' IN labels(n)]
        WITH p, n1s, r1s,
             reduce(acc = [], t IN collect(DISTINCT tree) | acc + nodes(t) + relationships(t)) AS tree_items
        RETURN p AS anchor, n1s, r1s, tree_items
        """,
        asin=asin,
    )
    if not rows:
        raise HTTPException(404, "商品不存在")
    row = rows[0]
    props_by_label = {
        "Product": ("asin", "title", "price", "rating", "image_url"),
        "Brand": ("name",),
        "Category": ("name", "level"),
        "AttributeValue": ("facet", "value"),
        "Occasion": ("name",),
    }
    nodes: dict[str, dict] = {}
    rels: dict[str, dict] = {}

    def add_node(n) -> None:
        if n is None or not hasattr(n, "labels"):  # tree_items 混有 Relationship，跳过
            return
        eid = n.element_id
        if eid in nodes:
            return
        label = next((l for l in ("Product", "Brand", "Category", "AttributeValue", "Occasion")
                      if l in n.labels), None)
        nodes[eid] = {"id": eid, "labels": list(n.labels),
                      "props": {k: n.get(k) for k in props_by_label.get(label, ())}}

    def add_rel(r) -> None:
        eid = r.element_id
        if eid in rels or r is None:
            return
        rels[eid] = {"id": eid, "source": r.start_node.element_id,
                     "target": r.end_node.element_id, "type": r.type,
                     "weight": r.get("weight")}

    for obj in [row["anchor"], *row["n1s"], *row["tree_items"]]:
        if obj is not None:
            add_node(obj)
    for r in [*row["r1s"], *row["tree_items"]]:
        if r is not None and hasattr(r, "type"):
            add_rel(r)
    return {"nodes": list(nodes.values()), "rels": list(rels.values())}


def main() -> None:
    import uvicorn

    uvicorn.run("mmkg.api.app:app", host="0.0.0.0", port=8000, reload=False)
