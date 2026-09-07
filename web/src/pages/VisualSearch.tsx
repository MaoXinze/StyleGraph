import { useRef, useState } from 'react'
import { api, type ProductCard as ProductCardType, type SearchHit } from '../api'
import PageHeader from '../components/PageHeader'
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

const STEPS = [
  { n: '01', t: '上传图片', d: '本地图或截图，JPG / PNG / WebP 均可' },
  { n: '02', t: 'CLIP 编码', d: '整图经 ViT-B-32 编码为 512 维视觉向量' },
  { n: '03', t: '全库比对', d: '与 11,761 个商品向量做余弦相似排序' },
]

export default function VisualSearch() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [examples, setExamples] = useState<ProductCardType[] | null>(null)
  const examplesLoaded = useRef(false)

  // 首次进入页面拉 4 张精选图作为示例
  if (!examplesLoaded.current) {
    examplesLoaded.current = true
    api.featured(4).then((r) => setExamples(r.products)).catch(() => {})
  }

  async function searchWith(asin: string) {
    try {
      const blob = await fetch(`/img/${asin}.jpg`).then((r) => r.blob())
      pick(new File([blob], `${asin}.jpg`, { type: 'image/jpeg' }))
    } catch {
      setError('示例图加载失败')
    }
  }

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
      <PageHeader
        title="以图搜款"
        en="Visual Search"
        desc="上传一张商品图，按 CLIP 视觉向量找出全库同风格单品"
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div>
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
            className={`grid-texture flex h-64 cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed bg-white transition-all ${
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

          {examples && (
            <div className="mt-4">
              <div className="mb-2 text-xs text-ink-faint">没有图？点一张库内商品试试</div>
              <div className="flex gap-2.5">
                {examples.map((p) => (
                  <button
                    key={p.asin}
                    onClick={() => searchWith(p.asin)}
                    title={p.title}
                    className="h-16 w-16 overflow-hidden rounded-lg border border-line-soft bg-white shadow-card transition-all hover:-translate-y-0.5 hover:border-brand-mid hover:shadow-lift"
                  >
                    <img
                      src={`/img/${p.asin}.jpg`}
                      alt=""
                      loading="lazy"
                      className="h-full w-full object-cover"
                    />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-3">
          {STEPS.map((s) => (
            <div
              key={s.n}
              className="rounded-xl border border-line-soft bg-white p-4 shadow-card"
            >
              <div className="flex items-baseline gap-2.5">
                <span className="text-[11px] font-semibold tabular-nums text-brand-mid">
                  {s.n}
                </span>
                <span className="text-sm font-medium text-ink">{s.t}</span>
              </div>
              <p className="mt-1.5 pl-6 text-xs leading-5 text-ink-soft">{s.d}</p>
            </div>
          ))}
        </aside>
      </div>

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
        <div className="rise">
          <h2 className="mb-4 text-sm text-ink-soft">相似度最高的 {hits.length} 件</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {hits.map((h) => (
              <ProductCard key={h.product.asin} p={h.product} score={h.score} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
