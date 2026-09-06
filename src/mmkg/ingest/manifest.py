"""商品清单（manifest）：JSONL 落盘的中间产物，支撑各阶段断点续跑。

文件：data/manifest/products.jsonl，每行一条商品记录。
"""

import json
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


def load_manifest(path: Path) -> dict[str, dict]:
    """读取 manifest，返回 {asin: record}；文件不存在或损坏行自动跳过。"""
    records: dict[str, dict] = {}
    if not path.exists():
        return records
    bad = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records[rec["asin"]] = rec
            except (json.JSONDecodeError, KeyError):
                bad += 1
    if bad:
        log.warning("manifest 中有 %d 行损坏已跳过", bad)
    return records


def save_manifest(path: Path, records: dict[str, dict]) -> None:
    """原子重写 manifest（tmp + rename），避免中断产生半行。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for rec in records.values():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def manifest_stats(records: dict[str, dict]) -> dict:
    by_dl: dict[str, int] = {}
    dup = 0
    for r in records.values():
        by_dl[r.get("download_status", "pending")] = by_dl.get(r.get("download_status", "pending"), 0) + 1
        if r.get("duplicate_of"):
            dup += 1
    return {"total": len(records), "duplicates": dup, "download_status": by_dl}
