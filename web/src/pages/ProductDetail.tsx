import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, priceText, productImage, type GraphEdge, type GraphNode, type RecommendItem } from '../api'
import GraphView from '../components/GraphView'
import ProductCard from '../components/ProductCard'

const KIND_LABEL: Record<string, string> = {
  co_purchased: '经常一起买',
  similar: '同风格相似款',
  complement: '搭配配饰',
}

interface Detail {
  product: Record<string, string | number | null>
  brand: string | null
  cats: { name: string; level: number }[]
  copurchase: Record<string, unknown>[]
  attributes: { facet: string; value: string }[]
  occasions: string[]
}

export default function ProductDetail() {
  const { asin = '' } = useParams()
  const [d, setD] = useState<Detail | null>(null)
  const [reco, setReco] = useState<RecommendItem[] | null>(null)
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; rels: GraphEdge[] } | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setD(null)
    setReco(null)
    setGraph(null)
    setError('')
    api.product<Detail>(asin).then(setD).catch(() => setError('商品不存在或已下架'))
    api.recommend(asin).then((r) => setReco(r.items)).catch(() => {})
    api.graphExplore(asin).then(setGraph).catch(() => {})
  }, [asin])

  if (error) return <p className="py-20 text-center text-sm text-ink-soft">{error}</p>
  if (!d) return <p className="py-20 text-center text-sm text-ink-soft">加载中…</p>

  const p = d.product
  return (
    <div className="space-y-10">
      <section className="grid gap-8 md:grid-cols-[380px_1fr]">
        <div className="overflow-hidden rounded-xl border border-line bg-white">
          {p.image_url ? (
            <img src={productImage({ asin: String(p.asin), image_url: p.image_url as string })} alt="" className="w-full object-cover" />
          ) : (
            <div className="flex aspect-square items-center justify-center text-ink-soft">无图</div>
          )}
        </div>
        <div className="space-y-4">
          <h1 className="text-xl font-semibold leading-7 text-ink">{String(p.title)}</h1>
          <div className="flex items-baseline gap-4">
            <span className="text-2xl font-semibold text-brand">{priceText(p.price as number)}</span>
            <span className="text-sm text-ink-soft">
              评分 {p.rating ?? '—'}
              {p.rating_count ? `（${p.rating_count} 条）` : ''}
            </span>
          </div>
          {d.brand && <p className="text-sm text-ink-soft">品牌：{d.brand}</p>}
          {d.cats.length > 0 && (
            <p className="text-sm text-ink-soft">
              类目：{d.cats.map((c) => c.name).join(' / ')}
            </p>
          )}
          {d.occasions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {d.occasions.map((o) => (
                <span key={o} className="rounded-full bg-brand-soft px-2.5 py-0.5 text-xs text-brand">
                  {o}
                </span>
              ))}
            </div>
          )}
          {d.attributes.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {d.attributes.map((a) => (
                <span key={a.facet + a.value} className="rounded border border-line bg-white px-2 py-0.5 text-xs text-ink-soft">
                  {a.facet}: {a.value}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {reco && reco.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-base font-semibold text-ink">搭配推荐</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {reco.map((it) => (
              <ProductCard
                key={it.product.asin}
                p={it.product}
                score={it.kind === 'similar' ? it.score : undefined}
                badge={KIND_LABEL[it.kind]}
              />
            ))}
          </div>
        </section>
      )}

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-ink">图谱邻域</h2>
        <GraphView nodes={graph?.nodes ?? []} rels={graph?.rels ?? []} />
      </section>
    </div>
  )
}
