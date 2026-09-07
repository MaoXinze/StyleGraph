import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type SearchHit } from '../api'
import ProductCard from '../components/ProductCard'

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
    <div className="space-y-8">
      <section className="mx-auto max-w-2xl space-y-4 pt-10 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-ink">搜款式，找搭配</h1>
        <p className="text-sm text-ink-soft">
          用一句话描述你想要的款式，从 11761 件商品中按视觉语义检索
        </p>
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="例如：floral summer dress / 纯棉白T恤 / leather boots"
            className="flex-1 rounded-lg border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-brand"
          />
          <Link
            to="/visual"
            className="rounded-lg border border-line bg-white px-4 py-2.5 text-sm text-ink-soft hover:border-brand hover:text-brand"
          >
            上传图片搜
          </Link>
        </div>
      </section>

      {error && <p className="text-center text-sm text-red-700">{error}</p>}
      {loading && <p className="text-center text-sm text-ink-soft">检索中…</p>}

      {hits && (
        <section>
          <h2 className="mb-4 text-sm text-ink-soft">共 {hits.length} 个结果</h2>
          {hits.length === 0 ? (
            <p className="py-10 text-center text-sm text-ink-soft">没有匹配的商品，换个说法试试</p>
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
        <section className="pt-4 text-center text-sm text-ink-soft">
          <p>
            试试{' '}
            {['floral dress', 'running shoes', 'leather jacket', 'gold necklace'].map((s) => (
              <button key={s} onClick={() => setQ(s)} className="mx-1 text-brand hover:underline">
                {s}
              </button>
            ))}
          </p>
        </section>
      )}
    </div>
  )
}
