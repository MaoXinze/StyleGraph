/** StyleGraph API 客户端封装 */

export interface ProductCard {
  asin: string
  title: string
  price: number | null
  rating: number | null
  rating_count: number | null
  image_url: string | null
  store: string | null
}

export interface SearchHit {
  product: ProductCard
  score: number
}

export interface RecommendItem {
  product: ProductCard
  score: number
  kind: 'co_purchased' | 'similar' | 'complement'
}

export interface GraphNode {
  id: string
  labels: string[]
  props: Record<string, unknown>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  weight: number | null
}

export interface ChatResult {
  intent: Record<string, unknown>
  products: ProductCard[]
  answer: string
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  stats: () =>
    fetch('/api/stats').then((r) =>
      json<{
        nodes: Record<string, number>
        rels: Record<string, number>
        server: { name?: string; versions?: string[] }
      }>(r),
    ),

  featured: (limit = 10) =>
    fetch(`/api/products/featured?limit=${limit}`).then((r) => json<{ products: ProductCard[] }>(r)),

  product: <T = Record<string, unknown>>(asin: string) =>
    fetch(`/api/products/${asin}`).then((r) => json<T>(r)),

  textSearch: (q: string, topK = 24) =>
    fetch(`/api/search/text?q=${encodeURIComponent(q)}&top_k=${topK}`).then((r) =>
      json<{ query: string; results: SearchHit[] }>(r),
    ),

  visualSearch: (file: File, topK = 24) => {
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`/api/search/visual?top_k=${topK}`, { method: 'POST', body: fd }).then((r) =>
      json<{ results: SearchHit[] }>(r),
    )
  },

  recommend: (asin: string, limit = 5) =>
    fetch(`/api/recommend/outfit/${asin}?limit=${limit}`).then((r) =>
      json<{ anchor: ProductCard; items: RecommendItem[] }>(r),
    ),

  chat: (question: string) =>
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }).then((r) => json<ChatResult>(r)),

  graphExplore: (asin: string) =>
    fetch(`/api/graph/explore?asin=${asin}`).then((r) =>
      json<{ nodes: GraphNode[]; rels: GraphEdge[] }>(r),
    ),
}

/** 商品图取本地静态服务（CDN 部分已 404，本地为权威源） */
export function productImage(p: ProductCard | { asin?: string; image_url?: string | null }): string {
  return p.image_url ? `/img/${p.asin}.jpg` : ''
}

export function priceText(v: number | null | undefined): string {
  return v == null ? '—' : `¥${v.toFixed(2)}`
}
