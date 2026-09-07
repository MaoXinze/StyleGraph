import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import { type GraphEdge, type GraphNode } from '../api'

const LABEL_COLORS: Record<string, string> = {
  Product: '#9a3412',
  Brand: '#0f766e',
  Category: '#a16207',
  AttributeValue: '#4338ca',
  Occasion: '#be185d',
}

export default function GraphView({ nodes, rels }: { nodes: GraphNode[]; rels: GraphEdge[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || nodes.length === 0) return
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...nodes.map((n) => ({
          data: {
            id: n.id,
            label: String(n.props.asin ?? n.props.name ?? n.props.value ?? n.id.slice(-8)),
            kind: n.labels[0],
          },
        })),
        ...rels.map((r) => ({ data: { id: r.id, source: r.source, target: r.target, kind: r.type } })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(kind)',
            color: '#57534e',
            label: 'data(label)',
            'font-size': 9,
            width: 22,
            height: 22,
            'border-width': 2,
            'border-color': '#ffffff',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#d6d3d1',
            'target-arrow-color': '#d6d3d1',
            'curve-style': 'bezier',
          },
        },
      ],
      layout: { name: 'cose', animate: false, padding: 20 },
    })
    return () => cy.destroy()
  }, [nodes, rels])

  if (nodes.length === 0) return <div className="p-6 text-sm text-ink-soft">暂无图谱数据</div>

  return (
    <div>
      <div ref={ref} className="h-96 w-full rounded-lg border border-line bg-white" />
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-ink-soft">
        {Object.entries(LABEL_COLORS).map(([k, c]) => (
          <span key={k} className="inline-flex items-center gap-1">
            <i className="inline-block size-2.5 rounded-full" style={{ background: c }} />
            {k}
          </span>
        ))}
      </div>
    </div>
  )
}
