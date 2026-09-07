"""检索质量评估：文本→图像向量 Recall@K（留出式，本地 GPU，零 API 成本）。

方法：随机抽 N 个商品，其 title 文本向量作为 query，在全库图像向量中检索，
看 top-K 是否命中同一商品（文本与图像同源）；另统计"同类目命中"宽松口径，
衡量语义相关性。

用法：uv run python -u scripts/eval_retrieval.py [--n 300]
"""

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch  # noqa: E402

from mmkg.config import bootstrap_env, get_settings  # noqa: E402
from mmkg.embeddings.clip import ClipEncoder  # noqa: E402
from mmkg.graph.db import Neo4jStore  # noqa: E402


def main() -> None:
    bootstrap_env()
    settings = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    args = ap.parse_args()

    store = Neo4jStore.from_settings(settings)
    rows = store.run(
        "MATCH (p:Product) WHERE p.image_embedding IS NOT NULL AND p.text_embedding IS NOT NULL "
        "RETURN p.asin AS asin, p.title AS title, p.image_embedding AS emb, "
        "[(p)-[:IN_CATEGORY]->(c) | c.id] AS cats"
    )
    asins = [r["asin"] for r in rows]
    titles = [r["title"] or "" for r in rows]
    cat_sets = [set(r["cats"] or []) for r in rows]
    asin2idx = {a: i for i, a in enumerate(asins)}
    print(f"library: {len(asins)} items", flush=True)

    rng = random.Random(42)
    sampled = rng.sample(range(len(rows)), min(args.n, len(rows)))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    mat = torch.tensor([r["emb"] for r in rows], dtype=torch.float32, device=device)
    enc = ClipEncoder(device=device)

    # 批量编码 query 文本
    q_vecs = torch.tensor(enc.encode_texts([titles[i] for i in sampled]), dtype=torch.float32, device=device)

    r10_self = r10_cat = 0
    t0 = time.perf_counter()
    for qi, src in zip(q_vecs, sampled):
        sims = (mat @ qi).flatten()
        top = torch.topk(sims, k=10).indices.tolist()
        if src in top:
            r10_self += 1
        if any(cat_sets[src] & cat_sets[j] for j in top):
            r10_cat += 1

    n = len(sampled)
    print(f"evaluated {n} queries in {time.perf_counter() - t0:.1f}s", flush=True)
    print(f"Recall@10 (self-hit):      {r10_self / n:.3f}", flush=True)
    print(f"Recall@10 (same-category): {r10_cat / n:.3f}", flush=True)
    store.close()


if __name__ == "__main__":
    main()
