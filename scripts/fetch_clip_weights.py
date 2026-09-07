"""CLIP ViT-B-32 原版权重下载（open_clip 原生格式）。

特性：Range 断点续传；直连/会话代理/Clash 三通道自动轮换；
无限重试直到完整；sha256 校验（open_clip 以 URL 中的 hash 为期望前缀）。
下载目标：data/cache/clip/ViT-B-32.pt（settings.clip_cache_dir）。

用法：uv run python -u scripts/fetch_clip_weights.py
"""

import hashlib
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmkg.config import bootstrap_env, get_settings  # noqa: E402

URL = ("https://openaipublic.azureedge.net/clip/models/"
       "40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt")
EXPECTED_SHA_PREFIX = URL.split("/")[-2]

PROXY_CANDIDATES = [
    None,                        # 直连
    "http://127.0.0.1:7138",     # WorkBuddy 会话代理
    "http://127.0.0.1:7897",     # 用户 Clash
]

READ_TIMEOUT = 30
MAX_ATTEMPTS = 200


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def main() -> None:
    bootstrap_env()
    target = get_settings().clip_cache_dir / "ViT-B-32.pt"
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"target: {target}", flush=True)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        pos = target.stat().st_size if target.exists() else 0
        proxy = PROXY_CANDIDATES[(attempt - 1) % len(PROXY_CANDIDATES)]
        tag = "direct" if proxy is None else proxy.rsplit(":", 1)[-1]
        try:
            with httpx.stream(
                "GET", URL,
                headers={"Range": f"bytes={pos}-"} if pos else {},
                timeout=httpx.Timeout(READ_TIMEOUT, connect=15),
                follow_redirects=True, trust_env=False, proxy=proxy,
            ) as r:
                if r.status_code == 416:
                    print("range beyond EOF -> file complete", flush=True)
                    break
                r.raise_for_status()
                if pos and r.status_code == 200:
                    # 服务器不支持 Range，从头来
                    pos = 0
                total = int(r.headers.get("content-length", 0)) + pos
                mode = "ab" if pos else "wb"
                with open(target, mode) as f:
                    n = pos
                    last_report = n
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
                        n += len(chunk)
                        if n - last_report >= 20 << 20:
                            last_report = n
                            pct = f"{n / total * 100:.0f}%" if total else "?"
                            print(f"[{tag}] {human(n)}/{human(total)} ({pct})", flush=True)
            size = target.stat().st_size
            print(f"attempt {attempt}[{tag}] ended at {human(size)}", flush=True)
            if total and size >= total:
                break
        except Exception as e:  # noqa: BLE001
            cur = target.stat().st_size if target.exists() else 0
            print(f"attempt {attempt}[{tag}] @ {human(cur)} failed: "
                  f"{type(e).__name__}: {str(e)[:120]}", flush=True)
            time.sleep(2)
    else:
        raise SystemExit("exhausted all attempts")

    size = target.stat().st_size
    print(f"downloaded: {human(size)} ({size} bytes)", flush=True)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    ok = sha.startswith(EXPECTED_SHA_PREFIX)
    print(f"sha256 prefix match: {ok}", flush=True)
    if not ok:
        target.unlink()
        raise SystemExit("sha256 mismatch, file deleted")
    print("OK", flush=True)


if __name__ == "__main__":
    main()
