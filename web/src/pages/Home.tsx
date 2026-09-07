import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ProductCard as ProductCardType, type SearchHit } from '../api'
import ProductCard from '../components/ProductCard'

const SAMPLES = ['floral summer dress', 'running shoes', 'leather jacket', 'gold necklace']

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
    <div className="space-y-10">
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
            onKeyDown={(e) => e.key === 'Enter' && setQ(q)}
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
            <p className="py-16 text-center text-sm text-ink-soft">
              没有匹配的商品，换个说法试试
            </p>
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
          <section className="rise grid grid-cols-3 gap-3 rounded-2xl border border-line-soft bg-white px-8 py-5 shadow-card">
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

          <section className="rise space-y-4">
            <div className="flex items-baseline justify-between">
              <h2 className="text-base font-semibold tracking-tight text-ink">精选商品</h2>
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

          <section className="rise grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              {
                t: '导购问答',
                d: '说出场景与预算，AI 解析意图后走图谱检索，结合商品价格评分给出建议',
                to: '/chat',
              },
              {
                t: '图谱总览',
                d: '商品、品牌、属性、场合与相似关系的网络全景统计',
                to: '/admin',
              },
            ].map((c) => (
              <Link
                key={c.to}
                to={c.to}
                className="group rounded-xl border border-line-soft bg-white p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-line hover:shadow-lift"
              >
                <div className="text-sm font-medium text-ink">{c.t}</div>
                <div className="mt-1.5 text-xs leading-5 text-ink-soft">{c.d}</div>
                <div className="mt-3 text-xs text-brand opacity-0 transition-opacity group-hover:opacity-100">
                  前往 →
                </div>
              </Link>
            ))}
          </section>
        </>
      )}
    </div>
  )
}
