import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type SearchHit } from '../api'
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
      <section className="mx-auto max-w-2xl space-y-5 pt-12 text-center">
        <h1 className="rise text-[34px] font-semibold leading-tight tracking-tight text-ink">
          搜款式，找搭配
        </h1>
        <p className="rise text-sm leading-6 text-ink-soft">
          用一句话描述你想要的款式，从 11,761 件商品中按视觉语义检索
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
          <Link
            to="/visual"
            className="shrink-0 rounded-lg border border-line px-3.5 py-2 text-xs text-ink-soft transition-colors hover:border-brand-mid hover:text-brand"
          >
            以图搜款
          </Link>
        </div>
        <div className="rise flex flex-wrap items-center justify-center gap-2 pt-1">
          {SAMPLES.map((s) => (
            <button
              key={s}
              onClick={() => setQ(s)}
              className="rounded-full border border-line-soft bg-white px-3 py-1 text-xs text-ink-soft transition-colors hover:border-brand-mid hover:text-brand"
            >
              {s}
            </button>
          ))}
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
        <section className="grid grid-cols-1 gap-4 pt-6 sm:grid-cols-3">
          {[
            { t: '以图搜款', d: '上传一张商品图，找出全库同风格单品', to: '/visual' },
            { t: '导购问答', d: '说出场景与预算，AI 结合图谱给出建议', to: '/chat' },
            { t: '图谱总览', d: '商品、品牌、属性与关系网络全景', to: '/admin' },
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
      )}
    </div>
  )
}
