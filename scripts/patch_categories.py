"""一次性修补脚本：魔搭 Range 扫描同时回填两类数据（均为幂等增量）：

1. category_nodes —— manifest 中缺失类目的商品
2. bought_together —— 所有商品的共购 ASIN 列表（M3 建边数据源）

带结束边界、超时重试、增量落盘、双任务凑齐即停。
"""

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx  # noqa: E402

from mmkg.config import bootstrap_env, get_settings  # noqa: E402
from mmkg.ingest.filters import row_to_product  # noqa: E402
from mmkg.ingest.manifest import load_manifest, save_manifest  # noqa: E402
from mmkg.ingest.sources import _MS_CHUNK, _ms_url  # noqa: E402


def main() -> None:
    bootstrap_env()
    settings = get_settings()
    records = load_manifest(settings.manifest_path)
    missing_cat = {asin for asin, r in records.items() if not r.get("category_nodes")}
    missing_bt = {asin for asin, r in records.items() if r.get("bought_scanned") is not True}
    print(f"待补类目 {len(missing_cat)}，待补共购 {len(missing_bt)} / 共 {len(records)}", flush=True)

    url = _ms_url(settings)
    size = int(httpx.head(url, timeout=30, follow_redirects=True).headers["content-length"])
    n = settings.collect_zones
    step = size // n
    cap = settings.zone_bytes_cap
    stop = threading.Event()
    lock = threading.Lock()
    stats = {"cat": 0, "bt": 0, "t0": time.time()}

    def on_row(asin: str, row: dict) -> None:
        with lock:
            rec = records.get(asin)
            if rec is None:
                return
            if rec.get("bought_scanned") is not True:
                bt = row.get("bought_together")
                rec["bought_together"] = bt if isinstance(bt, list) else []
                rec["bought_scanned"] = True
                stats["bt"] += 1
                missing_bt.discard(asin)
            if asin in missing_cat:
                cand = row_to_product(row, settings.min_rating_count)
                if cand and cand["category_nodes"]:
                    rec["category_nodes"] = cand["category_nodes"]
                    missing_cat.discard(asin)
                    stats["cat"] += 1
            total = stats["cat"] + stats["bt"]
            if total and total % 2000 == 0:
                save_manifest(settings.manifest_path, records)
                print(f"类目 {stats['cat']} / 共购 {stats['bt']}，"
                      f"剩 类目{len(missing_cat)} 共购{len(missing_bt)}，{time.time()-stats['t0']:.0f}s", flush=True)
            if not missing_cat and not missing_bt:
                save_manifest(settings.manifest_path, records)
                stop.set()
                print(f"全部补齐！耗时 {time.time()-stats['t0']:.0f}s", flush=True)

    def worker(off: int) -> None:
        headers = {"Range": f"bytes={off}-{off + cap - 1}", "User-Agent": "mmkg-ingest/0.1"}
        for attempt in (1, 2):
            if stop.is_set():
                return
            try:
                with httpx.stream("GET", url, headers=headers,
                                  timeout=httpx.Timeout(120, connect=30),
                                  follow_redirects=True) as r:
                    if r.status_code not in (200, 206):
                        return
                    buf = b""
                    first = True
                    for chunk in r.iter_raw(chunk_size=_MS_CHUNK):
                        if stop.is_set():
                            return
                        buf += chunk
                        lines = buf.split(b"\n")
                        buf = lines.pop()
                        for raw in lines:
                            if first:
                                first = False
                                continue
                            try:
                                row = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            asin = row.get("parent_asin") or row.get("asin")
                            if asin in records:
                                on_row(asin, row)
                return
            except httpx.HTTPError as e:
                print(f"区间 {off} 第{attempt}次失败：{type(e).__name__}", flush=True)
                time.sleep(3)

    threads = [threading.Thread(target=worker, args=(i * step,), daemon=True) for i in range(n)]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(0.5)
        if stop.is_set():
            break

    save_manifest(settings.manifest_path, records)
    print(f"结束：类目补 {stats['cat']}（剩 {len(missing_cat)}），"
          f"共购补 {stats['bt']}（剩 {len(missing_bt)}），总耗时 {time.time()-stats['t0']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
