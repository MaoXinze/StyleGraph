import { useRef, useState } from 'react'
import { api, type SearchHit } from '../api'
import ProductCard from '../components/ProductCard'

export default function VisualSearch() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-ink">以图搜款</h1>
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          pick(e.dataTransfer.files[0])
        }}
        className="flex h-44 cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-line bg-white text-sm text-ink-soft hover:border-brand hover:text-brand"
      >
        {preview ? (
          <img src={preview} alt="查询图" className="h-full rounded-lg object-contain p-2" />
        ) : (
          '点击或拖入一张商品图片'
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
      {loading && <p className="text-sm text-ink-soft">向量检索中…</p>}

      {hits && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {hits.map((h) => (
            <ProductCard key={h.product.asin} p={h.product} score={h.score} />
          ))}
        </div>
      )}
    </div>
  )
}
