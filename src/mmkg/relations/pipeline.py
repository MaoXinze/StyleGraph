"""关系构建管线（客观信号，不依赖 VLM）：

1. CO_PURCHASED：数据集 bought_together 字段（共同购买，强客观信号）
2. CAT_AFFINITY：类目亲和矩阵 —— 从共购对统计"哪个二级类目常与哪个二级类目一起被买"，
   物化为 Category 节点间的带权边，供搭配推荐做多跳扩展
"""

import logging
import time

from mmkg.config import Settings, get_settings
from mmkg.ingest.manifest import load_manifest
from mmkg.graph import Neo4jStore

log = logging.getLogger(__name__)

_WRITE_CO = """
UNWIND $rows AS row
MATCH (a:Product {asin: row.a}), (b:Product {asin: row.b})
MERGE (a)-[r:CO_PURCHASED]->(b)
SET r.weight = coalesce(r.weight, 0) + 1, r.source = 'dataset'
"""

# 共购对的二级类目亲和（有向计数），物化为类目边
_WRITE_AFFINITY = """
UNWIND $rows AS row
MATCH (ca:Category {id: row.cat_a}), (cb:Category {id: row.cat_b})
MERGE (ca)-[r:CAT_AFFINITY]->(cb)
SET r.weight = coalesce(r.weight, 0) + row.w
"""


def run_relations(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    records = load_manifest(settings.manifest_path)
    t0 = time.perf_counter()

    pairs: dict[tuple[str, str], int] = {}
    scanned_bt = 0
    for rec in records.values():
        for other in rec.get("bought_together") or []:
            if other == rec["asin"] or other not in records:
                continue  # 只连已收录商品，保证边两端都在图内
            key = tuple(sorted((rec["asin"], other)))
            pairs[key] = pairs.get(key, 0) + 1
        if rec.get("bought_scanned"):
            scanned_bt += 1

    rows = [{"a": a, "b": b, "w": w} for (a, b), w in pairs.items()]
    affinity: dict[tuple[str, str], int] = {}

    with Neo4jStore.from_settings(settings) as store:
        store.write_batch(_WRITE_CO, rows, settings.graph_batch_size)
        # 类目亲和：共购对 → 双方二级类目
        cat_rows = []
        for (a, b), w in pairs.items():
            cat_rows.append({"a": a, "b": b, "w": w})
        # 在图内查两边各自的 level-2 类目，再聚合
        result = store.run(
            """
            UNWIND $rows AS row
            MATCH (pa:Product {asin: row.a})-[:IN_CATEGORY]->(ca:Category {level:2})
            MATCH (pb:Product {asin: row.b})-[:IN_CATEGORY]->(cb:Category {level:2})
            RETURN ca.id AS ca, cb.id AS cb, row.w AS w
            """,
            rows=cat_rows,
        )
        for r in result:
            for key in ((r["ca"], r["cb"]), (r["cb"], r["ca"])):  # 无向对称
                affinity[key] = affinity.get(key, 0) + r["w"]
        aff_rows = [{"cat_a": k[0], "cat_b": k[1], "w": v} for k, v in affinity.items()]
        store.write_batch(_WRITE_AFFINITY, aff_rows, settings.graph_batch_size)
        rels = store.rel_counts()

    payload = {
        "stage": "relations", "elapsed_sec": round(time.perf_counter() - t0, 1),
        "bought_scanned": scanned_bt,
        "co_purchase_pairs": len(rows),
        "affinity_edges": len(aff_rows),
        "rel_counts": rels,
    }
    from mmkg.ingest.pipeline import write_run_report
    write_run_report(settings, "relations", payload)
    return payload
