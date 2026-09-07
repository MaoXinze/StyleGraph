# StyleGraph 交接文档（HANDOFF）

> 交接时间：2026-09-07 凌晨 · 交接对象：下一个接手的 agent
> 项目：StyleGraph（仓库代号 MMKG）· 电商多模态知识图谱平台
> 总体蓝图见 `.zcode/plans/plan-sess_*.md`（已批准），架构细节见 `docs/architecture.md`

## 0. 一句话现状

M1（数据与图谱骨架）**已完成并提交**；M2/M3/M4/M5 代码大部分就绪；有 2 个后台任务在跑（类目补齐、CLIP 向量编码）；**VLM 全量抽取被用户主动暂停**（等额度决策，见 §6）。

## 1. 项目定位与里程碑

- **一句话**：VLM 从商品「图+文」抽取实体关系 → Neo4j 多模态图谱（图+向量一体）→ 以图搜款 / 搭配推荐 / 导购问答（GraphRAG）→ 产品化前端 → 评估迭代。
- **里程碑**：
  - M1 ✅ 数据与图谱骨架（数据接入/图片下载/11761 商品入图/Neo4j schema/单测/文档）
  - M2 🔄 多模态抽取（CLIP 向量索引运行中；VLM 属性抽取**代码就绪但被暂停**，见 §6）
  - M3 🔨 关系与应用 API（CO_PURCHASED+类目亲和建边代码就绪、FastAPI 就绪，等数据）
  - M4 ⬜ 前端（脚手架已建，依赖安装失败待重试，页面未写）
  - M5 ⬜ 评估报告 + 部署文档 + 简历版 README + CI

## 2. 环境事实（必读）

| 项 | 值 |
|---|---|
| 项目根 | `D:\code_space\work_space\zcode\MMKG`（Git 仓库，2 个 commit） |
| Python | uv 0.12.3 管理，venv=`.venv`（Python 3.12），torch==2.13.0+cu130 **CUDA 可用**（RTX 4060 8GB） |
| uv 源 | pyproject 已配阿里云镜像 default + pytorch-cu130 explicit（**uv 不读 pip.ini**，改源只能改 pyproject） |
| Neo4j | Docker compose 分组 `mmkg`，容器 `mmkg-neo4j`（本地已有镜像 neo4j:5.26，勿重新拉取），端口 7474/7687，账密 `neo4j` / `mmkg_dev_2026`（`.env` 与 compose 默认一致） |
| API Key | `DASHSCOPE_API_KEY` 在 **Windows 用户级环境变量**，pydantic-settings 自动读取。**严禁打印到对话/日志/文件**（用户明确要求） |
| 百炼 | base_url `https://dashscope.aliyuncs.com/compatible-mode/v1`；免费额度约 1M token/模型，**大部分 2026-09-07（今天）过期**；详见 §6 |
| 网络可达性 | ✅ modelscope.cn（快）、m.media-amazon.com、openaipublic.azureedge.net（CLIP 权重）、download.pytorch.org、mirrors.aliyun.com；❌ huggingface.co、hf-mirror.com、pypi.org 直连（会挂死）；用户本机代理 127.0.0.1:7897（Clash，HF 走它也不通，规则分流问题） |
| 前端 | node 22 + pnpm（registry 已是 npmmirror），web/ 脚手架已建（Vite8+React19+TS） |

## 3. 数据与图谱现状

- **manifest**：`data/manifest/products.jsonl`，12000 条。字段：asin/title/title_fp/price/rating/rating_count/store/features/description/image_url(已重写 SL500)/image_file/phash/duplicate_of/download_status/category_nodes/bought_scanned（bought_together 抓取中）
- **图片**：`data/images/{asin}.jpg` 共 11761 张（SL500 ~500px）；207 张 CDN 已失效（所有尺寸 404）、16 张重复图
- **图谱**（Neo4j 5.26.30）：Product 11761 · Brand 7271 · Category 1267（最深 6 级）· HAS_BRAND 11726 · IN_CATEGORY 47801 · PARENT_OF 1265
- **类目覆盖**：11000/12000（剩 1000，补丁第三轮运行中，见 §5）
- **向量**：embed_status='ok' 的商品数 = 0（CLIP 权重 338MB 正在从 Azure 慢速下载，任务运行中）
- **数据踩坑备忘**：`categories` 是**扁平字符串列表**表示层级（相邻重名要去重防自环）；`bought_together` 字段存在（共购边数据源）；`images.thumb` 仅 38px 不可用，用图片 ID 改后缀 `._AC_SL500_.jpg`（CDN 按需出图）；`main_category` 字段噪音大不可信

## 4. 代码地图（src/mmkg/）

```
config/settings.py     Settings（pydantic-settings）：模型名/Neo4j/数据后端(modelscope)/collect_zones/zone_bytes_cap
utils/text.py          normalize_title / title_fingerprint / phash_of_image（dHash）
graph/db.py            Neo4jStore（run/write_batch/counts/rel_counts）
graph/schema.py        约束+索引 DDL；VECTOR_INDEXES（image/text 512d cosine）
ingest/sources.py      ⭐ ModelScope Range 分区流式采样（12路并发+哨兵+stop事件）+ HF 备用后端
ingest/filters.py      row_to_product / build_category_nodes / thumb_url_to_large
ingest/manifest.py     JSONL 清单读写（原子重写）
ingest/download.py     异步图片下载（信号量/重试/魔法数校验/dHash 去重/断点续传）
ingest/pipeline.py     run_collect / run_download_images / run_load_graph / write_run_report
llm/client.py          LLMClient（OpenAI 兼容→百炼；chat_json 带重试/429退避/usage 统计）
embeddings/clip.py     ClipEncoder（open_clip ViT-B-32/openai，GPU，容错编码）
embeddings/pipeline.py run_embed：pending 商品→图文向量→写图（向量索引）
extraction/schema.py   ProductAttributes（pydantic 枚举校验/规范化）+ 中英提示词
extraction/pipeline.py run_extract：attr_status 断点续跑→AttributeValue/Occasion 写图→QC 样本落盘
relations/pipeline.py  run_relations：bought_together→CO_PURCHASED；共购对→CAT_AFFINITY 类目亲和边
retrieval.py           SearchEngine：visual_search/text_search(向量)/recommend_outfit(共购+亲和多跳+类目多样性)/chat(意图解析→Cypher→向量兜底→LLM 生成)
api/app.py             FastAPI：/api/health /api/stats /api/products/{asin} /api/search/visual /api/search/text /api/recommend/outfit/{asin} /api/chat /api/graph/explore（纯 Cypher，无 APOC）
cli.py                 typer 命令：init-schema collect download-images load-graph ingest status embed extract build-relations serve
scripts/patch_categories.py  ⭐ 魔搭补丁（幂等）：补 category_nodes + bought_together（双任务版已写入文件）
tests/test_ingest.py   7 个单测（全过）
docs/                  architecture.md / cypher-cookbook.md / runs/*.json（每次运行报告）/ HANDOFF.md
```

## 5. 正在运行的后台任务（交接时点）

1. **类目补齐第三轮**：`COLLECT_ZONES=4 ZONE_BYTES_CAP=3000000000 uv run python -u scripts/patch_categories.py`
   - ⚠️ 运行中的进程加载的是**旧版脚本**（只补类目）；文件已是双任务新版（类目+共购一起抓）。等它结束后**再跑一轮新版**即可把 12000 商品的 `bought_together` 全部抓回（`bought_scanned` 标记判断，幂等增量、限流断点可续）
   - 魔搭 CDN 在持续传输约 1GB 后会限流（ReadTimeout/ConnectTimeout），策略：多跑几轮、每轮能抢多少抢多少；脚本有区间重试+增量落盘
2. **CLIP 全量编码**：`uv run mmkg embed`——权重 338MB 从 openaipublic.azureedge.net 慢速下载中（进程 767MB RAM=已载入）。完成后自动编码 11761 图+文写图。**验证方式**：`MATCH (p:Product {embed_status:'ok'}) RETURN count(*)`（应→11761）；日志经管道缓冲看不到中途输出，直接查 Neo4j
3. **web/ 脚手架**：package.json 已建（vite8/react19/ts/oxlint），**node_modules 为空**——`pnpm install` 首次失败（原因未查明，报错信息被 tail 吞了），需前台重跑 `cd web && pnpm install` 看真实报错；尚未添加 react-router-dom/cytoscape/tailwindcss/@tailwindcss/vite

## 6. ⏸️ 用户决策挂起项：VLM 全量抽取

用户看过百炼额度页（约 1M token/模型，**多数 9/7 当天过期**）后暂停了抽取，未选方案。已做技术准备：
- 抽取代码就绪：先试抽 `uv run mmkg extract --limit 20` 看质量（schema 校验/重试/QC 样本落盘 `docs/eval/extraction_samples.jsonl`），再全量
- **成本事实**：1.2 万商品 × 约 900 token/次（图 384px+文本）≈ 1100 万 token，单模型免费额度不够；VL 模型免费池（qwen-vl-plus 867k / qwen3-vl-flash / qwen3-vl-30b-a3b-instruct / qwen3-vl-235b-a22b-instruct / qwen3-vl-plus / qwen3-vl-flash-2025-10-15 等约 800 万 token）可轮换覆盖约 9-11k 商品
- 待实现（若恢复全量）：LLMClient.chat_json 里对 image 先 PIL 降采样到 ~384px JPEG（省一半 token）；ModelPool 多模型按 usage 轮换；QC 用旗舰模型判 100 样本
- 用户三个选项：A 立刻吃免费额度池（今晚过期） / B 付费全量（qwen-vl-plus 约 15-30 元） / C 小样本 1500-2000（免费）——**问用户，别自作主张花钱**

## 7. 接手后待办（建议顺序）

1. **盯两个后台任务**（§5）：embed 完成后跑向量检索冒烟（`SearchEngine.text_search("floral summer dress")` 应返回合理结果）；类目补齐结束后跑新版补丁脚本抓 `bought_together`
2. **M3 建边**：bought_together 齐了 → `uv run mmkg build-relations`（CO_PURCHASED + CAT_AFFINITY 物化边）→ 验证 `/api/recommend/outfit/{asin}` 推荐质量
3. **M3 API**：`uv run mmkg serve`（端口 8000，/docs 有 Swagger）→ curl 冒烟每个端点；`/api/chat` 每次只耗几百 token（小规模使用没问题）
4. **M4 前端**：重跑 `pnpm install` 排错 → 补装依赖（react-router-dom cytoscape tailwindcss @tailwindcss/vite）→ vite.config.ts 挂 @tailwindcss/vite 插件 + index.css `@import "tailwindcss";` + dev 代理 /api→localhost:8000 → 五个页面（Home 搜索入口 / VisualSearch 上传搜款 / ProductDetail 商品+图谱邻居(cytoscape)+搭配推荐 / Chat 导购问答 / Admin 统计）→ `pnpm build`
5. **M2 收尾（等用户决策）**：VLM 抽取（§6）→ QC 报告 v1（LLM-judge 抽样 100 条，用 text LLM 对 title 一致性 + VL 模型看图复核）
6. **M5**：评估（抽取 F1 / 检索 Recall@10（留出图作 query）/ 问答 30 题评分集）→ `docs/eval/` 报告 → docker-compose 加 api/web 服务 → GitHub Actions（ruff+pytest）→ README 简历版（架构图+评估数字+GIF）
7. **每个里程碑 git commit**（user.name=maoxi / user.email=maoxi@local 已在用）；`.env`/`data/`/`web/node_modules` 均已 gitignore

## 8. 验证命令速查

```bash
uv run pytest tests/ -q                                  # 7 passed
uv run mmkg status                                       # manifest+图谱总览
uv run python -c "..."                                   # 查 Neo4j 计数（embed 进度等）
uv run mmkg serve                                        # API: http://localhost:8000/docs
curl -X POST localhost:8000/api/search/visual -F file=@某图.jpg
curl "localhost:8000/api/recommend/outfit/B091YQVKS4"
curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" -d '{"question":"约会穿什么好看，预算500"}'
```

## 9. 工程教训（别踩重复的坑）

- **Bash CWD 跨调用持久**：永远用绝对路径 `cd /d/code_space/work_space/zcode/MMKG`
- **管道 `| tail` 吞退出码 + 缓冲输出**：判断成败要看真实状态（文件/Neo4j/进程），别信空日志
- **严禁 `taskkill //F //IM python.exe`**（全杀，会误伤其他进程）——只按 PID 杀
- **rich Progress 非 TTY 无输出**：脚本内用 `print(..., flush=True)`
- **魔搭限流**：突发 ~1GB 后 ReadTimeout；分区并发数越小越稳；脚本幂等可反复跑
- **uv 安装卡死 = pypi.org 直连挂死**：镜像配置在 pyproject（[[tool.uv.index]] default），别删
- **Neo4j Community 无 APOC**（未启用插件）：图查询用纯 Cypher（graph_explore 已是纯 Cypher 实现）
- **后台任务的日志文件**在 `C:\Users\maoxi\.zcode\cli\exec\sess_*/call_*-stdout.log`
- **Key 安全**：DASHSCOPE_API_KEY 只存在于用户环境变量，不写入任何文件、不打印（连前缀都少打）
