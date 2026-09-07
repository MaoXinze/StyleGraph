import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Admin() {
  const [stats, setStats] = useState<{ nodes: Record<string, number>; rels: Record<string, number> } | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <p className="text-sm text-red-700">{err}</p>
  if (!stats) return <p className="text-sm text-ink-soft">加载中…</p>

  const NODE_DESC: Record<string, string> = {
    Product: '商品',
    Brand: '品牌',
    Category: '类目',
    AttributeValue: '属性值',
    Occasion: '场合',
    Outfit: '搭配方案',
  }
  const REL_DESC: Record<string, string> = {
    HAS_BRAND: '属于品牌',
    IN_CATEGORY: '属于类目',
    PARENT_OF: '类目父子',
    HAS_ATTRIBUTE: '具有属性',
    SUITABLE_FOR: '适合场合',
    SIMILAR_TO: '视觉相似',
    CO_PURCHASED: '共同购买',
    CAT_AFFINITY: '类目亲和',
  }

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold text-ink">图谱总览</h1>
      <section>
        <h2 className="mb-3 text-sm text-ink-soft">节点</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(stats.nodes).map(([k, v]) => (
            <div key={k} className="rounded-lg border border-line bg-white p-4">
              <div className="text-2xl font-semibold text-ink">{v.toLocaleString()}</div>
              <div className="mt-1 text-xs text-ink-soft">
                {NODE_DESC[k] ?? k} <span className="text-stone-400">{k}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h2 className="mb-3 text-sm text-ink-soft">关系</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(stats.rels).map(([k, v]) => (
            <div key={k} className="rounded-lg border border-line bg-white p-4">
              <div className="text-2xl font-semibold text-ink">{v.toLocaleString()}</div>
              <div className="mt-1 text-xs text-ink-soft">
                {REL_DESC[k] ?? k} <span className="text-stone-400">{k}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
