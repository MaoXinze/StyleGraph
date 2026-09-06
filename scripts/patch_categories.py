"""一次性修补脚本：为 manifest 中缺失 category_nodes 的记录回填类目。

魔搭 Range 采样（区间带结束边界 + 超时重试 + 增量落盘 + 凑齐即停）。
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
    missing = {asin for asin, r in records.items() if not r.get("category_nodes")}
    print(f"待补类目：{len(missing)} / {len(records)}", flush=True)

    url = _ms_url(settings)
    size = int(httpx.head(url, timeout=30, follow_redirects=True).headers["content-length"])
    n = settings.collect_zones
    step = size // n
    cap = settings.zone_bytes_cap
    stop = threading.Event()
    lock = threading.Lock()
    stats = {"patched": 0, "t0": time.time()}

    def on_row(asin: str, row: dict) -> None:
        with lock:
            rec = row_to_product(row, settings.min_rating_count)
            if not (rec and rec["category_nodes"]) or asin not in missing:
                return
            records[asin]["category_nodes"] = rec["category_nodes"]
            missing.discard(asin)
            stats["patched"] += 1
            if stats["patched"] % 1000 == 0:
                save_manifest(settings.manifest_path, records)  # 增量落盘
                el = time.time() - stats["t0"]
                print(f"已补 {stats['patched']}，剩余 {len(missing)}，{el:.0f}s", flush=True)
            if not missing:
                stop.set()
                print(f"全部补齐！耗时 {time.time()-stats['t0']:.0f}s", flush=True)

    def worker(off: int) -> None:
        headers = {"Range": f"bytes={off}-{off + cap - 1}", "User-Agent": "mmkg-ingest/0.1"}
        for attempt in (1, 2):  # 区间级超时重试一次
            if stop.is_set():
                return
            try:
                with httpx.stream("GET", url, headers=headers,
                                  timeout=httpx.Timeout(60, connect=15),
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
                                first = False  # 区间起点的半行丢弃
                                continue
                            try:
                                row = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            asin = row.get("parent_asin") or row.get("asin")
                            if asin in missing:
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
    print(f"结束：补齐 {stats['patched']}，剩余缺失 {len(missing)}，总耗时 {time.time()-stats['t0']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
