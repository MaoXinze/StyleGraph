"""content-based 相似款建边：CLIP 图像向量近邻 → SIMILAR_TO 边。

双轨方案 B 轨第一块：不依赖行为数据（bought_together 在 2023 版数据集为 null）。
全量向量一次载入 GPU，余弦相似度矩阵一次算完（11761² ≈ 0.7 GFLOP，秒级）。
每商品保留 top-k 近邻（排除自身），score 阈值过滤后批量写 Neo4j。

用法：uv run python -u scripts/build_similar.py [--topk 8] [--min-score 0.85]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch  # noqa: E402

from mmkg.config import bootstrap_env, get_settings  # noqa: E402
from mmkg.graph.db import Neo4jStore  # noqa: E402

_WRITE_EDGE = """
UNWIND $rows AS row
MATCH (a:Product {asin: row.src}), (b:Product {asin: row.dst})
MERGE (a)-[r:SIMILAR_TO]->(b)
SET r.score = row.score
"""


def main() -> None:
    bootstrap_env()
    settings = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--min-score", type=float, default=0.85)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    store = Neo4jStore.from_settings(settings)
    t0 = time.perf_counter()

    rows = store.run("MATCH (p:Product) WHERE p.image_embedding IS NOT NULL "
                     "RETURN p.asin AS asin, p.image_embedding AS emb")
    print(f"loaded embeddings: {len(rows)}", flush=True)

    asins = [r["asin"] for r in rows]
    mat = torch.tensor([r["emb"] for r in rows], dtype=torch.float32, device=device)
    # 已归一化向量：点积即余弦
    sim = mat @ mat.T
    sim.fill_diagonal_(-1.0)

    k = min(args.topk, len(asins) - 1)
    scores, idx = torch.topk(sim, k=k, dim=1)
    scores, idx = scores.cpu(), idx.cpu()

    edges = []
    for i, (ss, ii) in enumerate(zip(scores.tolist(), idx.tolist())):
        for s, j in zip(ss, ii):
            if s >= args.min_score:
                edges.append({"src": asins[i], "dst": asins[j], "score": round(s, 4)})
    print(f"edges to write: {len(edges)} (min_score={args.min_score}, "
          f"elapsed {time.perf_counter() - t0:.1f}s)", flush=True)

    written = store.write_batch(_WRITE_EDGE, edges, batch_size=2000)
    print(f"written: {written} rows in {time.perf_counter() - t0:.1f}s", flush=True)

    cnt = store.run("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS c")[0]["c"]
    print(f"total SIMILAR_TO edges in graph: {cnt}", flush=True)
    store.close()


if __name__ == "__main__":
    main()
