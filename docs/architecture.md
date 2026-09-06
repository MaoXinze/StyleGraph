# StyleGraph 架构设计

> 仓库代号 MMKG · 电商多模态知识图谱平台
> 状态：M1（数据与图谱骨架）· 更新于 2026-09

## 1. 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vite + React)                       │
│   以图搜款 │ 搭配推荐 │ 导购问答 │ 图谱探索 │ 管理台/质检            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     API 服务 (FastAPI)                           │
│  /search/visual   /recommend/outfit   /chat   /graph  /stats    │
└───────┬──────────────────┬───────────────────────┬──────────────┘
        │                  │                       │
┌───────▼───────┐  ┌───────▼────────┐    ┌─────────▼─────────┐
│ 混合检索层      │  │ GraphRAG 编排   │    │ VLM/LLM (百炼)     │
│ 向量+图遍历融合 │  │ 意图→查询→生成   │    │ Qwen-VL / Qwen    │
└───────┬───────┘  └───────┬────────┘    └───────────────────┘
        │                  │
┌───────▼──────────────────▼──────────────────────────────────────┐
│              Neo4j 5  （图 + 原生向量索引一体）                     │
│  Product·Brand·Category·AttributeValue·Occasion·Outfit           │
│  image_embedding / text_embedding (CLIP 512d, cosine)            │
└──────────────────────────▲──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                      构建管线 (mmkg CLI)                          │
│  ingest: 数据集→过滤→去重→图片→入图                                 │
│  extract: VLM 属性抽取（schema 校验/重试/限速）                      │
│  relations: 共购+规则+向量候选 → VLM 搭配关系                       │
│  embed: CLIP 图文向量 → 向量索引                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 图谱本体（Ontology）

### 节点

| 标签 | 键 | 主要属性 | 说明 |
|---|---|---|---|
| `Product` | `asin` | title, price, rating, rating_count, store, features, description, image_url, image_file | 构建状态机：`ingest_status` → `attr_status` → `embed_status` |
| `Brand` | `name` | — | 来自数据集 store 字段 |
| `Category` | `id`（类目路径） | name, level | 三级类目树 |
| `AttributeValue` | `key`（facet=value） | value, facet | VLM 抽取，如 color=red / material=cotton / style=minimalist |
| `Occasion` | `name` | — | party / work / date / daily … |
| `Outfit` | `id` | reason, like_count, created_at | LLM 生成的搭配方案，承接用户反馈 |

### 关系

| 关系 | 方向 | 属性 | 来源 |
|---|---|---|---|
| `HAS_BRAND` | Product→Brand | — | 数据集 |
| `IN_CATEGORY` | Product→Category | — | 数据集 |
| `PARENT_OF` | Category→Category | — | 类目树 |
| `HAS_ATTRIBUTE` | Product→AttributeValue | source, confidence | VLM (M2) |
| `SUITABLE_FOR` | Product→Occasion | confidence | VLM (M2) |
| `CO_PURCHASED` | Product↔Product | weight | 数据集共购信号 |
| `PAIRS_WITH` | Product↔Product | reason, confidence | VLM 验证 (M3) |
| `IN_OUTFIT` | Outfit→Product | role | 推荐生成 (M3) |

### 向量索引（M2）

- `product_image_vec`：`Product.image_embedding`，512d（CLIP ViT-B/32），cosine
- `product_text_vec`：`Product.text_embedding`，512d，cosine

## 3. 数据来源与合规

- **数据集**：Amazon Reviews 2023（McAuley Lab, UCSD），学术公开数据集，`Clothing_Shoes_and_Jewelry` 类目（目标 1.2 万商品）
- **获取通道**：魔搭 ModelScope 同步仓（国内 CDN 直连）→ git 稀疏克隆 + LFS resolve 直链；
  HuggingFace 官方源在本机网络不可达，仅作海外备用后端（`DATA_BACKEND=hf`）
- **采集方式**：原始 meta jsonl 单文件 ~16.7GB（未压缩），**不做全量下载**——切成 12 个
  HTTP Range 区间并行流式采样，边下边解析过滤，凑满目标即停止（实测 ~600MB 传输 / 70s）
- **数据事实备忘**（踩坑记录）：
  - `categories` 是**扁平字符串列表**表示层级路径（非路径列表），相邻重名需去重防自环
  - `bought_together` 字段存在（ASIN 列表）→ M3 共购边的直接数据源
  - `images.thumb` 仅 38×50px（不可用于 CLIP）；用图片 ID 动态改写后缀得 `._AC_SL500_.jpg`（CDN 按需出图）
  - 部分商品图片已从 CDN 下架（所有尺寸 404），采集期 207/12000 ≈ 1.7% 属正常损耗
  - `main_category` 字段噪音大（有跨类目错标），以 `categories` 列表为准
- **准入条件**：有图、价格>0、评分数 ≥10、标题去重（规范化指纹）、图像感知哈希去重（dHash）
- **合规**：研究/演示用途；不直接爬取电商站点

## 4. 管线设计要点

1. **幂等断点续跑**：每阶段状态落在 manifest（JSONL）与图节点属性上，中断重跑只补缺口
2. **限速与重试**：图片下载并发信号量 + 两次重试；VLM 调用同样限速（M2）
3. **校验**：图片魔法数（JPEG/PNG/WEBP）+ 最小体积；VLM 输出 pydantic schema 校验，失败带错误重试（M2）
4. **成本控制**：批量抽取用低价模型、抽样质检用旗舰模型；运行报告记录 token/耗时（docs/runs/）
5. **可观测**：每次运行产出 JSON 报告（成功/失败/去重计数、耗时分布）

## 5. 技术决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 图数据库 | Neo4j 5 Community | 原生向量索引免去"图+向量库"两套系统同步；Cypher 生态成熟 |
| 多模态向量 | 本地 CLIP (open_clip) | 零调用成本；RTX 4060 编码 1.2 万图分钟级；图文同空间 |
| VLM/LLM | 阿里百炼 Qwen | 已有 Key 与免费额度；OpenAI 兼容接口降低切换成本 |
| Python 包管理 | uv | 与本机 DevMind-AI-test / sentiment-plus 同为 uv 体系，torch 2.13.0+cu130 wheel 从本地缓存零下载复用 |
| uv 索引 | 阿里云镜像(默认) + pytorch-cu130(explicit) | uv 不读 pip.ini，需在 pyproject 显式声明；torchvision 锁定 cu130 源保证 ABI 一致 |
| Dedup | 标题指纹 + dHash | 标题去重挡"改名同款"，图像哈希挡"同图换标" |
| 去重阈值 | 精确哈希 | M1 先用精确 dHash，M2 评估是否需要汉明距离容忍 |

## 6. 目录结构

见 README；`docs/runs/` 存放每次管线运行的 JSON 报告，`docs/eval/`（M5）存放评估报告。
