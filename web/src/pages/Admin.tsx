import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Admin() {
  const [stats, setStats] = useState<{ nodes: Record<string, number>; rels: Record<string, number> } | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <p className="text-sm text-red-700">{err}</p>
  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-line-soft" />
        ))}
      </div>
    )
  }

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

  const maxRel = Math.max(...Object.values(stats.rels), 1)

  return (
    <div className="rise space-y-10">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">图谱总览</h1>
        <p className="mt-1 text-sm text-ink-soft">Neo4j 中的节点与关系实时统计</p>
      </div>

      <section>
        <h2 className="mb-3 text-sm text-ink-soft">节点</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(stats.nodes).map(([k, v]) => (
            <div
              key={k}
              className="rounded-xl border border-line-soft bg-white p-4 shadow-card transition-shadow hover:shadow-lift"
            >
              <div className="text-[26px] font-semibold tabular-nums tracking-tight text-ink">
                {v.toLocaleString()}
              </div>
              <div className="mt-1 text-xs text-ink-soft">
                {NODE_DESC[k] ?? k} <span className="text-ink-faint">{k}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm text-ink-soft">关系</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Object.entries(stats.rels).map(([k, v]) => (
            <div
              key={k}
              className="rounded-xl border border-line-soft bg-white p-4 shadow-card"
            >
              <div className="flex items-baseline justify-between">
                <div className="text-sm text-ink-soft">
                  {REL_DESC[k] ?? k} <span className="text-ink-faint">{k}</span>
                </div>
                <div className="text-lg font-semibold tabular-nums text-ink">
                  {v.toLocaleString()}
                </div>
              </div>
              <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-line-soft">
                <div
                  className="h-full rounded-full bg-brand-mid/70 transition-all"
                  style={{ width: `${(v / maxRel) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
