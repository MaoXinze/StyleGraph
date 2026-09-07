"""向量索引管线：Graph 中待编码商品 → CLIP 图文向量 → Neo4j 向量索引。"""

import logging
import time

from mmkg.config import Settings, get_settings
from mmkg.graph import Neo4jStore
from mmkg.graph.schema import init_schema

log = logging.getLogger(__name__)

_FETCH_PENDING = """
MATCH (p:Product)
WHERE p.embed_status = 'pending' AND p.image_file IS NOT NULL
RETURN p.asin AS asin, p.title AS title, p.image_file AS image_file
LIMIT $limit
"""

_WRITE_VECS = """
UNWIND $rows AS row
MATCH (p:Product {asin: row.asin})
SET p.image_embedding = row.image,
    p.text_embedding = row.text,
    p.embed_status = 'ok'
"""


def run_embed(settings: Settings | None = None, limit: int | None = None) -> dict:
    settings = settings or get_settings()
    from mmkg.embeddings.clip import ClipEncoder

    t0 = time.perf_counter()
    encoder = ClipEncoder(settings.clip_model, settings.clip_pretrained)
    ok = failed = 0

    with Neo4jStore.from_settings(settings) as store:
        init_schema(store, with_vector=True)
        while True:
            batch = store.run(_FETCH_PENDING, limit=limit or 1024)
            if not batch:
                break
            paths = [b["image_file"] for b in batch]
            imgs = encoder.encode_images(paths, settings.clip_batch_size)
            texts = encoder.encode_texts([b["title"] for b in batch])
            rows = []
            for b, iv, tv in zip(batch, imgs, texts):
                if iv is None:
                    failed += 1
                    continue
                rows.append({"asin": b["asin"], "image": iv, "text": tv})
                ok += 1
            store.write_batch(_WRITE_VECS, rows, settings.graph_batch_size)
            log.info("已编码 %d（失败 %d）", ok, failed)
            if limit:
                break

    payload = {
        "stage": "embed", "elapsed_sec": round(time.perf_counter() - t0, 1),
        "embedded": ok, "failed": failed, "dim": encoder.dim, "device": encoder.device,
    }
    from mmkg.ingest.pipeline import write_run_report
    write_run_report(settings, "embed", payload)
    return payload
