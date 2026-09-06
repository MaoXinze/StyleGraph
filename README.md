# StyleGraph — 电商多模态知识图谱平台

> 用 VLM 从商品「图片 + 文本」中自动抽取实体与关系，构建多模态知识图谱，提供以图搜款、搭配推荐、导购问答（GraphRAG）三大能力。
>
> 仓库技术代号：MMKG（Multi-Modal Knowledge Graph）

**状态**：🚧 M1 建设中（数据与图谱骨架）

## 技术栈

- **VLM/LLM**：阿里百炼 Qwen-VL / Qwen（OpenAI 兼容接口）
- **多模态向量**：本地 CLIP（open_clip，RTX 4060 加速）
- **图存储**：Neo4j 5（图 + 原生向量索引一体）
- **后端**：Python 3.12 · FastAPI · Pydantic v2
- **前端**：Vite · React · TypeScript · Tailwind

## 快速开始

```bash
# 1. 环境（uv 管理，torch 与本机其他项目共享缓存，零下载）
uv sync

# 2. 配置（DASHSCOPE_API_KEY 从用户环境变量读取，无需写入文件）
cp .env.example .env

# 3. 启动 Neo4j
docker compose up -d

# 4. 构建图谱（数据接入 → VLM 抽取 → 向量索引）
uv run mmkg ingest
```

## 文档

- [架构设计](docs/architecture.md)
- [Cypher 查询手册](docs/cypher-cookbook.md)
- [评估报告](docs/eval/)
