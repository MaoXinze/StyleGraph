"""构建管线编排：collect（拉取+过滤）→ download（图片）→ load-graph（入图）。

每个阶段幂等可断点续跑，状态以 manifest + 图谱节点属性为准。
"""

import json
import logging
import time
from datetime import datetime, timezone

from rich.progress import (
    BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn,
)

from mmkg.config import Settings, get_settings
from mmkg.ingest.filters import row_to_product
from mmkg.ingest.manifest import load_manifest, manifest_stats, save_manifest
from mmkg.ingest.sources import iter_metadata

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_run_report(settings: Settings, stage: str, payload: dict) -> str:
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    path = settings.runs_dir / f"run_{stage}_{_now()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("运行报告已写入 %s", path)
    return str(path)


# ———————————————————————————————— collect ————————————————————————————————

def run_collect(settings: Settings | None = None) -> dict:
    """流式拉取数据集元数据 → 过滤 → 标题去重 → 写 manifest。"""
    settings = settings or get_settings()
    settings.ensure_dirs()
    records = load_manifest(settings.manifest_path)
    seen_fp = {r["title_fp"] for r in records.values()}
    t0 = time.perf_counter()
    scanned = accepted = rejected = dup_title = 0

    with Progress(SpinnerColumn(), "[progress.description]{task.description}",
                  BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(),
                  transient=True) as progress:
        task = progress.add_task("collect", total=settings.target_products)
        progress.update(task, completed=len(records))
        for row in iter_metadata(settings):
            scanned += 1
            rec = row_to_product(row, settings.min_rating_count)
            if rec is None:
                rejected += 1
            elif rec["asin"] in records:
                continue  # 已在清单（断点续跑）
            elif rec["title_fp"] in seen_fp:
                dup_title += 1
            else:
                records[rec["asin"]] = rec
                seen_fp.add(rec["title_fp"])
                accepted += 1
                progress.update(task, completed=len(records))
                if len(records) >= settings.target_products:
                    break
            if scanned % 5000 == 0:
                progress.update(task, completed=len(records))

    save_manifest(settings.manifest_path, records)
    payload = {
        "stage": "collect", "finished_at": _now(),
        "elapsed_sec": round(time.perf_counter() - t0, 1),
        "scanned": scanned, "accepted": accepted, "rejected": rejected,
        "duplicate_titles": dup_title, "manifest": manifest_stats(records),
    }
    write_run_report(settings, "collect", payload)
    return payload


# ——————————————————————————————— download ————————————————————————————————

def run_download_images(settings: Settings | None = None) -> dict:
    """下载全部待下载图片，带感知哈希去重与断点续传。"""
    from mmkg.ingest.download import download_images

    settings = settings or get_settings()
    settings.ensure_dirs()
    records = load_manifest(settings.manifest_path)
    pending = [r for r in records.values() if r.get("download_status") in ("pending", "failed")]
    log.info("待下载 %d / 共 %d", len(pending), len(records))
    t0 = time.perf_counter()
    stats = download_images(pending, settings.images_dir, settings.download_concurrency)
    save_manifest(settings.manifest_path, records)
    payload = {
        "stage": "download", "finished_at": _now(),
        "elapsed_sec": round(time.perf_counter() - t0, 1),
        **stats.__dict__,
    }
    write_run_report(settings, "download", payload)
    return payload


# ——————————————————————————————— load-graph ———————————————————————————————

_LOAD_PRODUCT = """
UNWIND $rows AS row
MERGE (p:Product {asin: row.asin})
SET p.title = row.title,
    p.price = row.price,
    p.rating = row.rating,
    p.rating_count = row.rating_count,
    p.store = row.store,
    p.features = row.features,
    p.description = row.description,
    p.image_url = row.image_url,
    p.image_file = row.image_file,
    p.ingest_status = 'ok',
    p.attr_status = 'pending',
    p.embed_status = 'pending'
FOREACH (_ IN CASE WHEN row.store IS NOT NULL THEN [1] ELSE [] END |
    MERGE (b:Brand {name: row.store})
    MERGE (p)-[:HAS_BRAND]->(b))
WITH p, row
UNWIND (CASE WHEN size(row.category_nodes) > 0 THEN row.category_nodes ELSE [null] END) AS cn
FOREACH (_ IN CASE WHEN cn IS NOT NULL THEN [1] ELSE [] END |
    MERGE (c:Category {id: cn.id})
    SET c.name = cn.name, c.level = cn.level
    MERGE (p)-[:IN_CATEGORY]->(c))
"""

_LOAD_CATEGORY_EDGES = """
UNWIND $rows AS row
MATCH (parent:Category {id: row.parent}), (child:Category {id: row.child})
MERGE (parent)-[:PARENT_OF]->(child)
"""


def run_load_graph(settings: Settings | None = None) -> dict:
    """manifest → Neo4j（Product / Brand / Category 类目树）。"""
    from mmkg.graph import Neo4jStore
    from mmkg.graph.schema import init_schema
    from mmkg.ingest.filters import category_edges

    settings = settings or get_settings()
    records = load_manifest(settings.manifest_path)
    usable = [r for r in records.values()
              if r.get("download_status") == "ok" and not r.get("duplicate_of")]
    log.info("可入图商品 %d（跳过重复/下载失败）", len(usable))
    t0 = time.perf_counter()

    with Neo4jStore.from_settings(settings) as store:
        init_schema(store)
        n = store.write_batch(_LOAD_PRODUCT, usable, settings.graph_batch_size)
        edges = []
        for r in usable:
            edges.extend(category_edges(r["category_nodes"]))
        store.write_batch(_LOAD_CATEGORY_EDGES, edges, settings.graph_batch_size)
        counts, rels, server = store.counts(), store.rel_counts(), store.server_info()

    payload = {
        "stage": "load_graph", "finished_at": _now(),
        "elapsed_sec": round(time.perf_counter() - t0, 1),
        "products_written": n, "category_edges": len(edges),
        "graph_counts": counts, "rel_counts": rels, "server": server,
    }
    write_run_report(settings, "load_graph", payload)
    return payload
