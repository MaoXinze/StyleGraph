import { Link } from 'react-router-dom'
import { priceText, productImage, type ProductCard } from '../api'

export default function ProductCard({ p, score, badge }: { p: ProductCard; score?: number; badge?: string }) {
  return (
    <Link
      to={`/product/${p.asin}`}
      className="group block overflow-hidden rounded-lg border border-line bg-white transition-shadow hover:shadow-md"
    >
      <div className="relative aspect-square bg-stone-100">
        {p.image_url ? (
          <img
            src={productImage(p)}
            alt={p.title}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-ink-soft">无图</div>
        )}
        {badge && (
          <span className="absolute left-2 top-2 rounded bg-brand px-1.5 py-0.5 text-[11px] text-white">
            {badge}
          </span>
        )}
      </div>
      <div className="space-y-1 p-3">
        <div className="line-clamp-2 min-h-10 text-[13px] leading-5 text-ink group-hover:text-brand">
          {p.title}
        </div>
        <div className="flex items-baseline justify-between">
          <span className="font-semibold text-brand">{priceText(p.price)}</span>
          <span className="text-xs text-ink-soft">
            {p.rating != null ? p.rating.toFixed(1) : '—'}
            {p.rating_count != null ? ` · ${p.rating_count} 评` : ''}
          </span>
        </div>
        {score != null && <div className="text-[11px] text-ink-soft">匹配度 {(score * 100).toFixed(1)}%</div>}
      </div>
    </Link>
  )
}
