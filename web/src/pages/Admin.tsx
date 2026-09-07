import { useEffect, useState } from 'react'
import { api } from '../api'
import PageHeader from '../components/PageHeader'

interface Stats {
  nodes: Record<string, number>
  rels: Record<string, number>
  server: { name?: string; versions?: string[] }
}

export default function Admin() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <p className="text-sm text-red-700">{err}</p>
  if (!stats) {
    return (
      <div className="space-y-6">
        <div className="h-16 w-64 animate-pulse rounded-lg bg-line-soft" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-line-soft" />
          ))}
        </div>
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
  const relEntries = Object.entries(stats.rels).sort((a, b) => b[1] - a[1])
  const totalRel = relEntries.reduce((s, [, v]) => s + v, 0)
  const maxRel = Math.max(...relEntries.map(([, v]) => v), 1)

  const sysSpecs = [
    { k: '图数据库', v: `${stats.server?.name ?? 'Neo4j'} ${stats.server?.versions?.[0] ?? ''}` },
    { k: '视觉编码器', v: 'CLIP ViT-B-32 (openai) · 512 维' },
    { k: '图像规模', v: `${(stats.nodes.Product ?? 0).toLocaleString()} 张商品图` },
    { k: '向量索引', v: 'product_image_vec / product_text_vec · cosine' },
  ]

  return (
    <div className="rise space-y-12">
      <PageHeader
        title="图谱总览"
        en="Graph Overview"
        desc="Neo4j 中的节点与关系实时统计"
      />

      {/* 节点：卡片网格 */}
      <section className="space-y-3">
        <h2 className="text-sm text-ink-soft">
          节点 <span className="text-ink-faint">Nodes</span>
        </h2>
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

      {/* 关系：MiMo 式规格表（行式 + 占比） */}
      <section className="space-y-3">
        <h2 className="text-sm text-ink-soft">
          关系 <span className="text-ink-faint">Relationships</span>
          <span className="ml-2 text-xs text-ink-faint">共 {totalRel.toLocaleString()} 条</span>
        </h2>
        <div className="divide-y divide-line-soft overflow-hidden rounded-2xl border border-line-soft bg-white shadow-card">
          {relEntries.map(([k, v]) => (
            <div key={k} className="flex items-center gap-4 px-5 py-3.5">
              <div className="w-40 shrink-0 text-sm text-ink">
                {REL_DESC[k] ?? k}
                <span className="ml-2 text-xs text-ink-faint">{k}</span>
              </div>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line-soft">
                <div
                  className="h-full rounded-full bg-brand-mid/70"
                  style={{ width: `${(v / maxRel) * 100}%` }}
                />
              </div>
              <div className="w-24 shrink-0 text-right text-sm font-medium tabular-nums text-ink">
                {v.toLocaleString()}
              </div>
              <div className="w-14 shrink-0 text-right text-xs tabular-nums text-ink-faint">
                {((v / totalRel) * 100).toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 系统规格（MiMo 式规格块） */}
      <section className="space-y-3">
        <h2 className="text-sm text-ink-soft">
          系统规格 <span className="text-ink-faint">System</span>
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {sysSpecs.map((s) => (
            <div
              key={s.k}
              className="flex items-baseline justify-between rounded-xl border border-line-soft bg-white px-5 py-4 shadow-card"
            >
              <span className="text-sm text-ink-soft">{s.k}</span>
              <span className="text-sm font-medium text-ink">{s.v}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
