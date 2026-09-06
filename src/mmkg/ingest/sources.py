"""数据集来源层。

后端一：modelscope（默认）——魔搭同步的 McAuley-Lab/Amazon-Reviews-2023（国内 CDN 直连）。
    原始 meta jsonl 单文件 ~17GB，绝不全量下载：把文件切成 N 个 Range 区间并行流式读取，
    边下边按行解析，交给上层过滤；凑满目标数即停止所有流（collect 采样语义）。
后端二：hf —— HuggingFace datasets 流式（海外网络环境用）。
"""

import json
import logging
import os
import queue
import threading
from collections.abc import Iterator
from urllib.parse import quote

import httpx

from mmkg.config import HF_MIRROR, Settings

log = logging.getLogger(__name__)

DATASET_ID = "McAuley-Lab/Amazon-Reviews-2023"
CONFIG_META = "raw_meta_Clothing_Shoes_and_Jewelry"

_MS_BASE = "https://modelscope.cn/datasets"
_MS_FILE = "raw/meta_categories/meta_Clothing_Shoes_and_Jewelry.jsonl"
_MS_CHUNK = 1 << 20  # 1MB


def prepare_hf_env(settings: Settings) -> str:
    """探测 HF 官方源连通性，必要时切换镜像。在任何 HF 库导入之前调用。"""
    endpoint = settings.hf_endpoint or os.environ.get("HF_ENDPOINT", "")
    if not endpoint:
        try:
            httpx.get("https://huggingface.co/api/models?limit=1", timeout=5.0)
            endpoint = "https://huggingface.co"
        except httpx.HTTPError:
            endpoint = HF_MIRROR
            log.info("HF 官方源不可达，切换镜像 %s", HF_MIRROR)
    os.environ["HF_ENDPOINT"] = endpoint
    return endpoint


def iter_metadata(settings: Settings) -> Iterator[dict]:
    """按配置的后端迭代商品元数据行（dict）。"""
    if settings.data_backend == "modelscope":
        yield from _iter_modelscope_zones(settings)
    else:
        yield from _iter_hf(settings)


# ———————————————————————————— modelscope 后端 ————————————————————————————

def _ms_url(settings: Settings) -> str:
    return f"{_MS_BASE}/{settings.modelscope_dataset}/resolve/master/{_MS_FILE}"


def _ms_remote_size(settings: Settings) -> int:
    r = httpx.head(_ms_url(settings), timeout=30, follow_redirects=True)
    r.raise_for_status()
    return int(r.headers["content-length"])


def _zone_worker(off: int, byte_cap: int, url: str, out: "queue.Queue",
                 stop: threading.Event, stats: dict, lock: threading.Lock) -> None:
    """单个 Range 区间流：跳过区间头部的残行，逐行 json 解析后推入队列。"""
    try:
        headers = {"Range": f"bytes={off}-", "User-Agent": "mmkg-ingest/0.1"}
        with httpx.stream("GET", url, headers=headers, timeout=httpx.Timeout(30, connect=15),
                          follow_redirects=True) as r:
            if r.status_code not in (200, 206):
                raise RuntimeError(f"HTTP {r.status_code}")
            buf = b""
            downloaded = 0
            first_line_skipped = False
            for chunk in r.iter_raw(chunk_size=_MS_CHUNK):
                if stop.is_set():
                    return
                buf += chunk
                downloaded += len(chunk)
                lines = buf.split(b"\n")
                buf = lines.pop()  # 末段可能不完整，留到下一块
                for raw in lines:
                    if not first_line_skipped:
                        first_line_skipped = True  # 区间起点的半行丢弃
                        continue
                    if not raw.strip():
                        continue
                    try:
                        row = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    out.put(row)
                with lock:
                    stats["bytes"] = stats.get("bytes", 0) + len(chunk)
                if downloaded >= byte_cap:
                    log.info("区间 %d 达到字节上限 %dMB，提前收工", off, byte_cap >> 20)
                    return
    except Exception as e:  # noqa: BLE001 —— 单区间失败不拖垮整体
        log.warning("区间起点 %d 读取失败：%s", off, type(e).__name__)
    finally:
        out.put(None)  # 本 worker 的结束哨兵


def _iter_modelscope_zones(settings: Settings) -> Iterator[dict]:
    size = _ms_remote_size(settings)
    n_zones = settings.collect_zones
    step = size // n_zones
    offsets = [i * step for i in range(n_zones)]
    log.info("ModelScope 采样：文件 %.1fGB 切 %d 区，每区上限 %.0fMB",
             size / 1e9, n_zones, settings.zone_bytes_cap / 1e6)

    out: "queue.Queue" = queue.Queue(maxsize=4000)
    stop = threading.Event()
    stats = {"bytes": 0}
    lock = threading.Lock()

    threads = [
        threading.Thread(target=_zone_worker,
                         args=(off, settings.zone_bytes_cap, _ms_url(settings), out, stop, stats, lock),
                         daemon=True)
        for off in offsets
    ]
    for t in threads:
        t.start()

    alive = n_zones
    try:
        while alive > 0:
            row = out.get()
            if row is None:
                alive -= 1
                continue
            yield row
    finally:
        stop.set()
        # 排空队列让 worker 能写 finish 哨兵退出，避免线程悬挂
        while any(t.is_alive() for t in threads):
            try:
                out.get_nowait()
            except queue.Empty:
                break
        with lock:
            log.info("本次采样共传输 %.2fGB", stats["bytes"] / 1e9)


# ————————————————————————————— hf 后端（备用） ————————————————————————————

def _iter_hf(settings: Settings) -> Iterator[dict]:
    prepare_hf_env(settings)
    from datasets import load_dataset  # 延迟导入：确保 HF_ENDPOINT 已就绪

    ds = load_dataset(DATASET_ID, CONFIG_META, split="full", streaming=True)
    yield from ds
