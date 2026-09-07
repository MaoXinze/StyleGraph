import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ProductCard as ProductCardType, type SearchHit } from '../api'
import ProductCard from '../components/ProductCard'

const SAMPLES = ['floral summer dress', 'running shoes', 'leather jacket', 'gold necklace']

/** 功能矩阵（MiMo 式产品卡） */
const MATRIX = [
  {
    to: '/visual',
    no: '01',
    name: '以图搜款',
    en: 'Visual Search',
    desc: '上传一张商品图，整图经 CLIP 编码为视觉向量，与全库做余弦相似排序，找出同风格单品。',
    cta: '上传图片',
  },
  {
    to: '/chat',
    no: '02',
    name: '导购问答',
    en: 'Shopping Q&A',
    desc: '自然语言解析为品类、场合与价格意图，走图谱混合检索，结合价格与评分生成建议。',
    cta: '开始提问',
  },
  {
    to: '/admin',
    no: '03',
    name: '图谱总览',
    en: 'Graph Overview',
    desc: '商品、品牌、属性、场合与相似关系的网络全景，实时统计节点与关系规模。',
    cta: '查看图谱',
  },
  {
    to: '/product/B091YQVKS4',
    no: '04',
    name: '搭配推荐',
    en: 'Outfit Engine',
    desc: '视觉相似、跨类目互补与共购信号三层融合，为每件商品生成可穿的搭配方案。',
    cta: '看示例',
  },
]

/** 技术亮点（MiMo 式编号清单） */
const HIGHLIGHTS = [
  {
    no: '01',
    t: '多模态向量索引',
    en: 'Multimodal Embeddings',
    d: 'CLIP ViT-B-32 将 11,761 张商品图与标题编码为 512 维向量，图文同空间对齐，图像即查询。',
  },
  {
    no: '02',
    t: '知识图谱结构',
    en: 'Knowledge Graph',
    d: 'Neo4j 存储商品—品牌—类目—属性—场合的语义网络，6 万+ 视觉相似边连接跨类目单品。',
  },
  {
    no: '03',
    t: 'GraphRAG 问答',
    en: 'GraphRAG Pipeline',
    d: '意图解析 → 图谱属性过滤 → 向量召回兜底 → LLM 生成，四段式管线保证回答有据可依。',
  },
]

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4 shrink-0 text-ink-faint">
      <circle cx="9" cy="9" r="5.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M13.5 13.5L17 17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export default function Home() {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [featured, setFeatured] = useState<ProductCardType[] | null>(null)

  useEffect(() => {
    api.featured(10).then((r) => setFeatured(r.products)).catch(() => {})
  }, [])

  useEffect(() => {
    const t = setTimeout(() => {
      if (q.trim().length < 2) {
        setHits(null)
        return
      }
      setLoading(true)
      setError('')
      api
        .textSearch(q.trim())
        .then((r) => setHits(r.results))
        .catch((e) => setError(String(e)))
        .finally(() => setLoading(false))
    }, 400)
    return () => clearTimeout(t)
  }, [q])

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="mx-auto max-w-2xl space-y-5 pt-10 text-center">
        <h1 className="rise text-[34px] font-semibold leading-tight tracking-tight text-ink">
          搜款式，找搭配
        </h1>
        <p className="rise text-sm leading-6 text-ink-soft">
          用一句话描述你想要的款式，按 CLIP 视觉语义从全库检索
        </p>
        <div className="rise flex items-center gap-2 rounded-xl border border-line bg-white p-1.5 shadow-card transition-shadow focus-within:border-brand-mid focus-within:shadow-lift">
          <span className="pl-2.5">
            <SearchIcon />
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="floral summer dress / 纯棉白T恤 / leather boots"
            className="min-w-0 flex-1 bg-transparent px-1 py-2 text-sm outline-none placeholder:text-ink-faint"
          />
        </div>
        <div className="rise flex flex-wrap items-center justify-center gap-x-4 gap-y-2 pt-0.5 text-xs">
          {SAMPLES.map((s) => (
            <button
              key={s}
              onClick={() => setQ(s)}
              className="text-ink-soft transition-colors hover:text-brand"
            >
              {s}
            </button>
          ))}
          <span className="text-ink-faint">|</span>
          <Link to="/visual" className="text-brand transition-colors hover:text-brand-deep">
            不想打字？上传图片搜款 →
          </Link>
        </div>
      </section>

      {error && <p className="text-center text-sm text-red-700">{error}</p>}

      {loading && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="overflow-hidden rounded-xl border border-line-soft bg-white">
              <div className="aspect-square animate-pulse bg-line-soft" />
              <div className="space-y-2 p-3">
                <div className="h-3 w-full animate-pulse rounded bg-line-soft" />
                <div className="h-3 w-2/3 animate-pulse rounded bg-line-soft" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && hits && (
        <section className="rise">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-sm text-ink-soft">
              「{q.trim()}」共 {hits.length} 个结果
            </h2>
          </div>
          {hits.length === 0 ? (
            <p className="py-16 text-center text-sm text-ink-soft">没有匹配的商品，换个说法试试</p>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              {hits.map((h) => (
                <ProductCard key={h.product.asin} p={h.product} score={h.score} />
              ))}
            </div>
          )}
        </section>
      )}

      {!hits && !loading && (
        <>
          {/* 规格行（MiMo 式） */}
          <section className="rise grid grid-cols-3 divide-x divide-line-soft rounded-2xl border border-line-soft bg-white px-8 py-5 shadow-card">
            {[
              { n: '11,761', l: '商品全图入库' },
              { n: '61,179', l: '视觉相似关系' },
              { n: '512 维', l: 'CLIP 图文向量' },
            ].map((s) => (
              <div key={s.l} className="text-center">
                <div className="text-xl font-semibold tabular-nums tracking-tight text-ink">
                  {s.n}
                </div>
                <div className="mt-0.5 text-xs text-ink-soft">{s.l}</div>
              </div>
            ))}
          </section>

          {/* 功能矩阵（MiMo 式产品卡） */}
          <section className="rise space-y-5">
            <div className="text-center">
              <h2 className="text-lg font-semibold tracking-tight text-ink">功能矩阵</h2>
              <p className="mt-1 text-xs text-ink-soft">
                从向量检索到智能问答，StyleGraph 提供端到端的电商检索体验
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {MATRIX.map((m) => (
                <Link
                  key={m.no}
                  to={m.to}
                  className="group flex flex-col rounded-2xl border border-line-soft bg-white p-6 shadow-card transition-all hover:-translate-y-0.5 hover:border-line hover:shadow-lift"
                >
                  <div className="flex items-baseline gap-3">
                    <span className="text-[11px] font-semibold tabular-nums text-brand-mid">
                      {m.no}
                    </span>
                    <span className="text-[15px] font-medium text-ink">{m.name}</span>
                    <span className="text-xs text-ink-faint">{m.en}</span>
                  </div>
                  <p className="mt-3 flex-1 text-xs leading-5 text-ink-soft">{m.desc}</p>
                  <div className="mt-4 flex items-center justify-between text-xs">
                    <span className="text-brand">{m.cta}</span>
                    <span className="text-ink-faint transition-transform group-hover:translate-x-0.5">
                      →
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* 技术亮点（MiMo 式编号清单） */}
          <section className="rise space-y-5">
            <div className="text-center">
              <h2 className="text-lg font-semibold tracking-tight text-ink">引擎之下</h2>
              <p className="mt-1 text-xs text-ink-soft">三层技术栈如何协同工作</p>
            </div>
            <div className="divide-y divide-line-soft rounded-2xl border border-line-soft bg-white shadow-card">
              {HIGHLIGHTS.map((h) => (
                <div key={h.no} className="flex gap-6 p-6">
                  <span className="text-2xl font-semibold tabular-nums text-brand-mid/60">
                    {h.no}
                  </span>
                  <div>
                    <div className="flex items-baseline gap-2.5">
                      <span className="text-sm font-medium text-ink">{h.t}</span>
                      <span className="text-xs text-ink-faint">{h.en}</span>
                    </div>
                    <p className="mt-1.5 text-xs leading-5 text-ink-soft">{h.d}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 精选橱窗 */}
          <section className="rise space-y-4">
            <div className="flex items-baseline justify-between">
              <h2 className="text-lg font-semibold tracking-tight text-ink">精选商品</h2>
              <span className="text-xs text-ink-faint">按评价数排序</span>
            </div>
            {featured ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
                {featured.map((p) => (
                  <ProductCard key={p.asin} p={p} />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className="overflow-hidden rounded-xl border border-line-soft bg-white"
                  >
                    <div className="aspect-square animate-pulse bg-line-soft" />
                    <div className="space-y-2 p-3">
                      <div className="h-3 w-full animate-pulse rounded bg-line-soft" />
                      <div className="h-3 w-2/3 animate-pulse rounded bg-line-soft" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 品牌叙事（MiMo 式） */}
          <section className="rise mx-auto max-w-xl py-6 text-center">
            <p className="text-sm leading-7 text-ink-soft">
              从图像与文本中提炼款式规律，
              <br />
              把检索变成理解，把商品连成网络。
            </p>
            <p className="mt-3 text-xs text-ink-faint">
              StyleGraph · 电商多模态知识图谱 · 与你一同探索穿搭的边界
            </p>
          </section>
        </>
      )}
    </div>
  )
}
