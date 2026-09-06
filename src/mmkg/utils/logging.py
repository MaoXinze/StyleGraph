"""统一日志：rich 美化输出，第三方库降噪。"""

import logging

import rich.logging


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:  # 幂等
        return
    handler = rich.logging.RichHandler(rich_tracebacks=True, show_path=False, markup=False)
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    root.addHandler(handler)
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "urllib3", "neo4j", "hpack", "filelock",
                  "huggingface_hub", "datasets", "pydantic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
