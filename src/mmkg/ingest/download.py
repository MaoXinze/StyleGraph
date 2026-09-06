"""图片批量下载：并发限速、魔法数校验、感知哈希去重、断点续传。"""

import asyncio
import logging
import pathlib
from dataclasses import dataclass, field

import httpx
from PIL import Image

from mmkg.utils.text import phash_of_image

log = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_MAGIC = (b"\xff\xd8", b"\x89PNG", b"RIFF")  # JPEG / PNG / WEBP


def _valid_image(content: bytes) -> bool:
    if len(content) < 3 * 1024:  # MIN_IMAGE_BYTES
        return False
    return content[:2] == _MAGIC[0] or content[:4] in (_MAGIC[1], _MAGIC[2])


@dataclass
class DownloadStats:
    ok: int = 0
    failed: int = 0
    skipped: int = 0
    duplicates: int = 0
    errors: dict = field(default_factory=dict)


async def _fetch(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> bytes | None:
    async with sem:
        for attempt in (1, 2):
            try:
                r = await client.get(url, headers={"User-Agent": UA})
                if r.status_code == 200 and _valid_image(r.content):
                    return r.content
                err = f"HTTP {r.status_code}"
            except httpx.HTTPError as e:
                err = type(e).__name__
            if attempt == 1:
                await asyncio.sleep(1.0)
        raise RuntimeError(err)


async def _download_one(client, sem, rec, images_dir, seen_phash, stats):
    asin = rec["asin"]
    target = images_dir / f"{asin}.jpg"
    if rec.get("download_status") == "ok" and target.exists() and rec.get("phash"):
        stats.skipped += 1  # 断点续传
        return
    if rec.get("duplicate_of"):
        stats.skipped += 1
        return
    try:
        content = await _fetch(client, sem, rec["image_url"])
        target.write_bytes(content)
        phash = phash_of_image(Image.open(target))
        owner = seen_phash.get(phash)
        if owner and owner != asin:
            rec.update(download_status="duplicate", duplicate_of=owner,
                       image_file=None, phash=phash)
            target.unlink(missing_ok=True)
            stats.duplicates += 1
        else:
            seen_phash[phash] = asin
            rec.update(download_status="ok", duplicate_of=None,
                       image_file=str(target), phash=phash)
            stats.ok += 1
    except Exception as e:  # noqa: BLE001 —— 单张失败不阻断整体
        rec.update(download_status="failed", error=str(e))
        stats.failed += 1
        stats.errors[type(e).__name__] = stats.errors.get(type(e).__name__, 0) + 1
        if pathlib.Path(target).exists():
            pathlib.Path(target).unlink(missing_ok=True)


async def _run_download(records, images_dir, concurrency, stats, log_every=500):
    sem = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(20.0, connect=8.0)
    limits = httpx.Limits(max_connections=concurrency * 2)
    done = 0
    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True) as client:
        tasks = [asyncio.create_task(_download_one(client, sem, rec, images_dir, seen, stats))
                 for rec, seen in records]
        for fut in asyncio.as_completed(tasks):
            await fut
            done += 1
            if done % log_every == 0:
                log.info("下载进度 %d/%d  ok=%d dup=%d failed=%d",
                         done, len(tasks), stats.ok, stats.duplicates, stats.failed)


def download_images(records: list[dict], images_dir, concurrency: int = 16) -> DownloadStats:
    """下载清单中所有待下载图片；phash 去重基于本次全量记录。返回统计。"""
    seen_phash = {r["phash"]: r["asin"] for r in records if r.get("phash") and not r.get("duplicate_of")}
    stats = DownloadStats()
    asyncio.run(_run_download([(r, seen_phash) for r in records], images_dir, concurrency, stats))
    return stats
