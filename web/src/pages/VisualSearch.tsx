import { useRef, useState } from 'react'
import { api, type SearchHit } from '../api'
import ProductCard from '../components/ProductCard'

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7 text-ink-faint">
      <path
        d="M12 16V7m0 0l-3.5 3.5M12 7l3.5 3.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 15.5V18a2 2 0 002 2h12a2 2 0 002-2v-2.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function VisualSearch() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  function pick(f: File | undefined) {
    if (!f) return
    setPreview(URL.createObjectURL(f))
    setHits(null)
    setError('')
    setLoading(true)
    api
      .visualSearch(f)
      .then((r) => setHits(r.results))
      .catch((e) => setError(e.message === '400' ? '图片无法解析，换一张试试' : String(e)))
      .finally(() => setLoading(false))
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">以图搜款</h1>
        <p className="mt-1 text-sm text-ink-soft">
          上传一张商品图，按 CLIP 视觉向量找出全库同风格单品
        </p>
      </div>

      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          pick(e.dataTransfer.files[0])
        }}
        className={`flex h-52 cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed bg-white transition-all ${
          dragging
            ? 'border-brand-mid bg-brand-soft'
            : 'border-line hover:border-brand-mid hover:bg-brand-soft/40'
        }`}
      >
        {preview ? (
          <img src={preview} alt="查询图" className="h-full rounded-xl object-contain p-3" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-ink-soft">
            <UploadIcon />
            <span className="text-sm">点击或拖入一张商品图片</span>
            <span className="text-xs text-ink-faint">支持 JPG / PNG / WebP</span>
          </div>
        )}
      </div>
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => pick(e.target.files?.[0])}
      />

      {error && <p className="text-sm text-red-700">{error}</p>}

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
        <div className="rise grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {hits.map((h) => (
            <ProductCard key={h.product.asin} p={h.product} score={h.score} />
          ))}
        </div>
      )}
    </div>
  )
}
