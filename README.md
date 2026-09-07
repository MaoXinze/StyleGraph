# StyleGraph — 电商多模态知识图谱平台

> 用 VLM 从商品「图片 + 文本」中自动抽取实体与关系，构建多模态知识图谱，提供以图搜款、搭配推荐、导购问答（GraphRAG）三大能力。
>
> 仓库技术代号：MMKG（Multi-Modal Knowledge Graph）

**状态**：✅ M1–M4 完成（数据 / 向量 / 关系 / API / 前端）

## 技术栈

- **多模态向量**：CLIP ViT-B-32（open_clip，RTX 4060 本地 GPU 编码）
- **VLM/LLM**：DeepSeek V4 Flash / V4 Flash Vision（OpenAI 兼容接口，属性抽取与问答）
- **图存储**：Neo4j 5.26（属性图 + 原生向量索引一体，无需独立向量库）
- **后端**：Python 3.12 · FastAPI · Pydantic v2
- **前端**：Vite 8 · React 19 · TypeScript · Tailwind 4 · Cytoscape（图谱可视化）

## 数据规模

| 指标 | 数量 |
|---|---|
| 商品节点（含原图） | 11,761 |
| 属性节点 / 场景节点 | 4,672 / 36 |
| VLM 抽取属性边 HAS_ATTRIBUTE | 55,547 |
| 场景边 SUITABLE_FOR | 25,537 |
| 视觉相似边 SIMILAR_TO（CLIP 近邻） | 61,179 |
| 向量索引（图 + 文，512 维） | 23,522 条 |

## 检索质量评估

留出式评估：随机抽 500 个商品，标题文本向量作为 query，在全库图像向量中检索 top-10（`scripts/eval_retrieval.py`，本地 GPU，零 API 成本）。

| 指标 | 结果 | 含义 |
|---|---|---|
| Recall@10（同类目命中） | **0.874** | 前 10 结果中 87.4% 与查询语义相关（业务口径） |
| Recall@10（精确自命中） | 0.462 | 跨模态严格口径：命中标题对应的商品本身 |

> 同款式商品在库内高度密集（一条连衣裙有数百相似款），自命中口径天然偏严；同类目口径更能反映真实检索体验。

## 功能

- **文本搜款**：自然语言 → CLIP 文本向量 → 全库图像向量余弦检索
- **以图搜款**：上传商品图 → CLIP 图像向量 → 相似款排序
- **搭配推荐**：三层融合——共购信号（保留位）> 视觉相似（SIMILAR_TO）> 跨类目互补配饰（性别一致性过滤）
- **导购问答（GraphRAG）**：意图解析（场景/价格/品类）→ 图谱属性过滤 → 向量召回兜底 → LLM 生成建议
- **图谱探索**：商品邻域子图可视化（品牌/类目树/属性/场合/相似款）

## 快速开始

```bash
# 1. 环境（uv 管理）
uv sync

# 2. 配置（DeepSeek API Key 写入 .env 的 LLM_API_KEY）
cp .env.example .env

# 3. 启动 Neo4j
docker compose up -d

# 4. 构建图谱（数据接入 → VLM 抽取 → 向量索引 → 相似边）
uv run mmkg ingest && uv run mmkg extract && uv run mmkg embed

# 5. 启动 API 与前端
uv run mmkg serve        # API: 8000
cd web && pnpm i && pnpm dev   # 前端: 5173
```

## 文档

- [架构设计](docs/architecture.md)
- [Cypher 查询手册](docs/cypher-cookbook.md)
- [评估报告](docs/eval/)
- [运行报告](docs/runs/)（各阶段 JSON 快照）
