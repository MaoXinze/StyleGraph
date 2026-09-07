"""属性抽取管线：Graph 中待抽取商品 → VLM 结构化抽取 → 属性写回图谱。

- 断点续跑：以 Product.attr_status 为准（pending / ok / failed / no_image）
- 并发线程池 + 客户端内置 429 退避
- 抽样落盘 docs/eval/extraction_samples.jsonl 供质检（QC）
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from mmkg.config import Settings, get_settings
from mmkg.extraction.schema import SYSTEM_PROMPT, ProductAttributes, build_user_prompt
from mmkg.graph import Neo4jStore
from mmkg.llm import LLMClient

log = logging.getLogger(__name__)

_FETCH_PENDING = """
MATCH (p:Product)
WHERE p.attr_status = 'pending' AND p.image_file IS NOT NULL
RETURN p.asin AS asin, p.title AS title, p.image_file AS image_file
LIMIT $limit
"""

_WRITE_ATTR = """
UNWIND $rows AS row
MATCH (p:Product {asin: row.asin})
SET p.attr_status = 'ok', p.attributes = row.attrs
WITH p, row
UNWIND (CASE WHEN size(row.attr_values) > 0 THEN row.attr_values ELSE [null] END) AS av
FOREACH (_ IN CASE WHEN av IS NOT NULL THEN [1] ELSE [] END |
    MERGE (a:AttributeValue {key: av.key})
    SET a.facet = av.facet, a.value = av.value
    MERGE (p)-[:HAS_ATTRIBUTE {source: 'vlm', model: row.model}]->(a))
WITH p, row
UNWIND (CASE WHEN size(row.occasions) > 0 THEN row.occasions ELSE [null] END) AS oc
FOREACH (_ IN CASE WHEN oc IS NOT NULL THEN [1] ELSE [] END |
    MERGE (o:Occasion {name: oc})
    MERGE (p)-[:SUITABLE_FOR {source: 'vlm'}]->(o))
"""

_MARK = "UNWIND $rows AS row MATCH (p:Product {asin: row.asin}) SET p.attr_status = row.status"


def _to_graph_rows(asin: str, attrs: ProductAttributes, model: str) -> dict:
    attr_values = []
    for facet in ("item_type", "gender", "color", "material", "style"):
        value = getattr(attrs, facet)
        if value:
            attr_values.append({"key": f"{facet}:{value}", "facet": facet, "value": value})
    return {"asin": asin, "attrs": attrs.model_dump(), "attr_values": attr_values,
            "occasions": attrs.occasion, "model": model}


def run_extract(settings: Settings | None = None, limit: int | None = None,
                concurrency: int | None = None, qc_sample: int = 200) -> dict:
    settings = settings or get_settings()
    concurrency = concurrency or 8
    client = LLMClient(settings, provider="vlm")  # 看图抽取走百炼 VLM
    t0 = time.perf_counter()
    ok = failed = no_image = 0
    qc_rows: list[dict] = []

    with Neo4jStore.from_settings(settings) as store:
        todo = store.run(_FETCH_PENDING, limit=limit or 10**9)
        log.info("待抽取 %d 商品，模型 %s，并发 %d", len(todo), client.model, concurrency)

        def work(item: dict) -> tuple[str, str, dict | None]:
            path = Path(item["image_file"])
            if not path.exists():
                return item["asin"], "no_image", None
            raw = client.chat_json(SYSTEM_PROMPT, build_user_prompt(item["title"]),
                                   image_path=str(path))
            if raw is None:
                return item["asin"], "failed", None
            try:
                attrs = ProductAttributes.model_validate(raw)
            except Exception:  # noqa: BLE001 —— 校验失败带错误重试一次
                retry = client.chat_json(
                    SYSTEM_PROMPT,
                    build_user_prompt(item["title"])
                    + f"\n\nYour previous output failed validation: {raw!r}\nReturn strictly valid JSON.",
                    image_path=str(path))
                if retry is None:
                    return item["asin"], "failed", None
                attrs = ProductAttributes.model_validate(retry)
            return item["asin"], "ok", attrs

        batch: list[dict] = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(work, item): item for item in todo}
            for fut in as_completed(futures):
                asin, status, attrs = fut.result()
                if status == "ok":
                    ok += 1
                    batch.append(_to_graph_rows(asin, attrs, client.model))
                    if len(qc_rows) < qc_sample:
                        qc_rows.append({"asin": asin, "title": futures[fut]["title"],
                                        "extracted": attrs.model_dump()})
                elif status == "no_image":
                    no_image += 1
                    batch.append({"asin": asin, "status": "no_image"})
                else:
                    failed += 1
                    batch.append({"asin": asin, "status": "failed"})
                if len(batch) >= settings.graph_batch_size:
                    store.write_batch(_WRITE_ATTR, [r for r in batch if "attrs" in r])
                    store.write_batch(_MARK, [r for r in batch if "status" in r])
                    log.info("进度 ok=%d failed=%d no_image=%d", ok, failed, no_image)
                    batch = []
        if batch:
            store.write_batch(_WRITE_ATTR, [r for r in batch if "attrs" in r])
            store.write_batch(_MARK, [r for r in batch if "status" in r])

    from mmkg.ingest.pipeline import write_run_report
    qc_path = Path("docs/eval/extraction_samples.jsonl")
    qc_path.parent.mkdir(parents=True, exist_ok=True)
    with open(qc_path, "w", encoding="utf-8") as f:
        for row in qc_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    payload = {
        "stage": "extract", "elapsed_sec": round(time.perf_counter() - t0, 1),
        "ok": ok, "failed": failed, "no_image": no_image,
        "model": client.model, "usage": client.usage, "qc_sample": str(qc_path),
    }
    write_run_report(settings, "extract", payload)
    return payload
