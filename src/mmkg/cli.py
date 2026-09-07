"""MMKG 命令行入口。

用法示例：
  uv run mmkg init-schema          # 初始化 Neo4j 约束/索引
  uv run mmkg collect              # 拉取数据集 → 过滤 → manifest
  uv run mmkg download-images      # 批量下载商品图
  uv run mmkg load-graph           # manifest → Neo4j
  uv run mmkg ingest               # 顺序执行以上三步
  uv run mmkg status               # 查看清单与图谱状态
"""

import logging

import typer
from rich.console import Console
from rich.table import Table

from mmkg import __version__

app = typer.Typer(help="MMKG — 电商多模态知识图谱平台", no_args_is_help=True, add_completion=False)
console = Console()
err_console = Console(stderr=True)


@app.callback()
def _root(verbose: bool = typer.Option(False, "--verbose", "-v", help="调试日志")) -> None:
    from mmkg.utils.logging import setup_logging

    setup_logging(logging.DEBUG if verbose else logging.INFO)


def _settings():
    from mmkg.config import bootstrap_env, get_settings

    bootstrap_env()  # 必须在导入 HF/datasets 相关模块前执行
    return get_settings()


@app.command("init-schema")
def init_schema_cmd(
    with_vector: bool = typer.Option(False, "--with-vector", help="同时创建向量索引（M2 阶段用）"),
) -> None:
    """初始化 Neo4j 约束与索引（幂等）。"""
    from mmkg.graph import Neo4jStore
    from mmkg.graph.schema import init_schema

    settings = _settings()
    with Neo4jStore.from_settings(settings) as store:
        applied = init_schema(store, with_vector=with_vector)
        info = store.server_info()
    console.print(f"Neo4j {info.get('versions', ['?'])[0] if info else '?'} · 已应用 {len(applied)} 项 schema 定义")


@app.command()
def collect(
    target: int = typer.Option(None, help="目标商品数（默认取配置）"),
) -> None:
    """拉取 Amazon Reviews 2023 元数据 → 过滤 → 标题去重 → manifest。"""
    from mmkg.ingest.pipeline import run_collect

    settings = _settings()
    if target:
        settings.target_products = target
    payload = run_collect(settings)
    console.print(f"[green]collect 完成[/green]：清单共 {payload['manifest']['total']} 商品"
                  f"（新收 {payload['accepted']}，过滤 {payload['rejected']}，重名 {payload['duplicate_titles']}）"
                  f" · {payload['elapsed_sec']}s")


@app.command("download-images")
def download_images_cmd(
    concurrency: int = typer.Option(None, help="并发数（默认取配置）"),
) -> None:
    """批量下载商品图（限速并发、魔法数校验、感知哈希去重、断点续传）。"""
    from mmkg.ingest.pipeline import run_download_images

    settings = _settings()
    if concurrency:
        settings.download_concurrency = concurrency
    payload = run_download_images(settings)
    stats = payload
    console.print(
        f"[green]download 完成[/green]：ok={stats['ok']} 去重={stats['duplicates']} "
        f"失败={stats['failed']} 跳过={stats['skipped']} · {stats['elapsed_sec']}s"
    )
    if stats.get("errors"):
        console.print(f"[yellow]错误分布：{stats['errors']}[/yellow]")


@app.command("load-graph")
def load_graph_cmd() -> None:
    """manifest → Neo4j（Product / Brand / Category 类目树）。"""
    from mmkg.ingest.pipeline import run_load_graph

    settings = _settings()
    payload = run_load_graph(settings)
    console.print(f"[green]load-graph 完成[/green]：写入 {payload['products_written']} 商品 · {payload['elapsed_sec']}s")
    for label, c in payload["graph_counts"].items():
        console.print(f"  {label:<16}{c:>8}")


@app.command()
def ingest(
    target: int = typer.Option(None, help="目标商品数"),
) -> None:
    """顺序执行 collect → download-images → load-graph。"""
    from mmkg.ingest.pipeline import run_collect, run_download_images, run_load_graph

    settings = _settings()
    if target:
        settings.target_products = target
    run_collect(settings)
    run_download_images(settings)
    run_load_graph(settings)
    console.print("[green]ingest 全部完成[/green]")


@app.command()
def status() -> None:
    """查看 manifest 与图谱当前状态。"""
    from mmkg.ingest.manifest import load_manifest, manifest_stats
    from mmkg.graph import Neo4jStore

    settings = _settings()
    m = manifest_stats(load_manifest(settings.manifest_path))
    table = Table(title="MMKG 状态", show_header=True)
    table.add_column("项目")
    table.add_column("数值", justify="right")
    table.add_row("manifest 总数", str(m["total"]))
    table.add_row("重复图（去重）", str(m["duplicates"]))
    for k, v in m["download_status"].items():
        table.add_row(f"下载状态 {k}", str(v))
    try:
        with Neo4jStore.from_settings(settings) as store:
            info = store.server_info()
            for k, v in store.counts().items():
                table.add_row(f"图谱 {k}", str(v))
            for k, v in store.rel_counts().items():
                table.add_row(f"关系 {k}", str(v))
            table.add_row("Neo4j 版本", str(info.get("versions", ["?"])[0]))
    except Exception as e:  # noqa: BLE001
        table.add_row("图谱", f"连接失败：{type(e).__name__}")
    console.print(table)


@app.command()
def embed(
    limit: int = typer.Option(None, help="本次最多编码多少商品（默认全部 pending）"),
) -> None:
    """CLIP 图文向量编码 → Neo4j 向量索引（本地 GPU）。"""
    from mmkg.embeddings import run_embed

    settings = _settings()
    payload = run_embed(settings, limit=limit)
    console.print(f"[green]embed 完成[/green]：{payload['embedded']} 成功 / {payload['failed']} 失败"
                  f" · {payload['dim']}维@{payload['device']} · {payload['elapsed_sec']}s")


@app.command()
def extract(
    limit: int = typer.Option(None, help="本次最多抽取多少商品（默认全部 pending）"),
    concurrency: int = typer.Option(None, help="并发数（默认 8）"),
    model: str = typer.Option(None, help="VLM 模型名（默认取配置 vlm_model）"),
) -> None:
    """VLM 属性抽取 → AttributeValue/Occasion 节点 + HAS_ATTRIBUTE/SUITABLE_FOR 边。"""
    from mmkg.extraction import run_extract

    settings = _settings()
    if model:
        settings.vlm_model = model
    payload = run_extract(settings, limit=limit, concurrency=concurrency)
    u = payload["usage"]
    console.print(f"[green]extract 完成[/green]：ok={payload['ok']} failed={payload['failed']}"
                  f" no_image={payload['no_image']} · 调用 {u['calls']} 次"
                  f"（tokens {u['prompt_tokens']}+{u['completion_tokens']}）· {payload['elapsed_sec']}s")


@app.command("build-relations")
def build_relations_cmd() -> None:
    """从 bought_together 构建 CO_PURCHASED + 类目亲和边（客观信号，无需 VLM）。"""
    from mmkg.relations import run_relations

    settings = _settings()
    payload = run_relations(settings)
    console.print(f"[green]relations 完成[/green]：共购对 {payload['co_purchase_pairs']}"
                  f" · 类目亲和边 {payload['affinity_edges']} · {payload['elapsed_sec']}s")


@app.command()
def serve(
    port: int = typer.Option(8000, help="API 端口"),
) -> None:
    """启动 StyleGraph API 服务（uvicorn）。"""
    import uvicorn

    _settings()
    console.print(f"StyleGraph API: http://localhost:{port}/docs")
    uvicorn.run("mmkg.api.app:app", host="0.0.0.0", port=port)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
