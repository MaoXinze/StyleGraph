import { Link } from 'react-router-dom'
import { priceText, productImage, type ProductCard as ProductCardType } from '../api'

function Star({ fill }: { fill: number }) {
  return (
    <svg viewBox="0 0 16 16" className="h-3 w-3">
      <defs>
        <linearGradient id={`sg${fill}`}>
          <stop offset={`${fill}%`} stopColor="#d97706" />
          <stop offset={`${fill}%`} stopColor="#e7e5e4" />
        </linearGradient>
      </defs>
      <path
        d="M8 1.5l1.9 3.9 4.3.6-3.1 3 .7 4.2L8 11.2l-3.8 2 .7-4.2-3.1-3 4.3-.6z"
        fill={`url(#sg${fill})`}
      />
    </svg>
  )
}

export default function ProductCard({
  p,
  score,
  badge,
}: {
  p: ProductCardType
  score?: number
  badge?: string
}) {
  return (
    <Link
      to={`/product/${p.asin}`}
      className="group block overflow-hidden rounded-xl border border-line-soft bg-white shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-line hover:shadow-lift"
    >
      <div className="relative aspect-square overflow-hidden bg-line-soft">
        {p.image_url ? (
          <img
            src={productImage(p)}
            alt={p.title}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-ink-faint">无图</div>
        )}
        {badge && (
          <span className="absolute left-2 top-2 rounded-md bg-brand px-1.5 py-0.5 text-[11px] font-medium text-white shadow-sm">
            {badge}
          </span>
        )}
      </div>
      <div className="space-y-1.5 p-3">
        <div className="line-clamp-2 min-h-10 text-[13px] leading-5 text-ink group-hover:text-brand-deep">
          {p.title}
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[15px] font-semibold tracking-tight text-brand-deep">
            {priceText(p.price)}
          </span>
          <span className="flex items-center gap-1 text-[11px] text-ink-soft">
            {p.rating != null && (
              <Star fill={Math.round((p.rating / 5) * 100)} />
            )}
            {p.rating != null ? p.rating.toFixed(1) : '—'}
            {p.rating_count != null && (
              <span className="text-ink-faint">· {p.rating_count} 评</span>
            )}
          </span>
        </div>
        {score != null && (
          <div className="flex items-center gap-2">
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-line-soft">
              <div
                className="h-full rounded-full bg-brand-mid/70"
                style={{ width: `${Math.min(score * 100, 100)}%` }}
              />
            </div>
            <span className="text-[11px] tabular-nums text-ink-faint">
              {(score * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </Link>
  )
}
