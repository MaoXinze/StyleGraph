"""全局配置。

优先级：进程环境变量 > 项目根 .env > 默认值。
DASHSCOPE_API_KEY 存在于 Windows 用户级环境变量，无需写入 .env。
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 官方源不可达时自动切换的镜像（国内网络）
HF_MIRROR = "https://hf-mirror.com"


def find_project_root() -> Path:
    """从 cwd 向上查找含 pyproject.toml 的目录；找不到则返回 cwd。"""
    cur = Path.cwd().resolve()
    for p in (cur, *cur.parents):
        if (p / "pyproject.toml").exists():
            return p
    return cur


def bootstrap_env() -> Path:
    """CLI/服务入口最先调用：加载 .env 并把 HF 缓存重定向到 D 盘项目目录。

    必须在任何 huggingface/datasets 模块导入之前执行。
    返回项目根目录。
    """
    root = find_project_root()
    load_dotenv(root / ".env", override=False)
    if not os.environ.get("HF_HOME"):
        os.environ["HF_HOME"] = str(root / "data" / "cache" / "huggingface")
    return root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # —— 模型服务（百炼 DashScope，OpenAI 兼容）——
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    vlm_model: str = "qwen-vl-plus"
    llm_model: str = "qwen-plus"

    # —— 图数据库 ——
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "mmkg_dev_2026"

    # —— 数据与缓存 ——
    data_dir: Path = Field(default_factory=lambda: find_project_root() / "data")
    hf_endpoint: str = ""  # 空 = 先试官方源，运行时探测失败自动切镜像
    clip_model: str = "ViT-B-32"
    clip_pretrained: str = "openai"
    clip_batch_size: int = 64

    # —— 管线参数 ——
    target_products: int = 12000
    min_rating_count: int = 10
    download_concurrency: int = 16
    graph_batch_size: int = 500

    # —— 数据后端 ——
    # modelscope：魔搭国内 CDN，Range 分区采样（当前网络默认）；
    # hf：HuggingFace datasets 流式（海外网络用）。
    data_backend: str = "modelscope"
    modelscope_dataset: str = "McAuley-Lab/Amazon-Reviews-2023"
    collect_zones: int = 12          # 文件切多少个并行 Range 区间
    zone_bytes_cap: int = 1_200_000_000  # 单区间最多传输字节（~1.2GB）

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifest" / "products.jsonl"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def runs_dir(self) -> Path:
        return find_project_root() / "docs" / "runs"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.images_dir, self.manifest_path.parent,
                  self.cache_dir, self.runs_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
