import { NavLink, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import VisualSearch from './pages/VisualSearch'
import ProductDetail from './pages/ProductDetail'
import Chat from './pages/Chat'
import Admin from './pages/Admin'

const TABS = [
  { to: '/', label: '搜索' },
  { to: '/visual', label: '以图搜款' },
  { to: '/chat', label: '导购问答' },
  { to: '/admin', label: '图谱总览' },
]

/** 图谱标记：核心节点 + 邻域连线 */
function Logo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" fill="#1c1917" />
      <path
        d="M16 7.5L7.5 21M16 7.5L24.5 21M7.5 21h17M16 7.5v13.5M12 21l8-9.5M20 21l-8-9.5"
        stroke="#c2410c"
        strokeWidth="1"
        opacity="0.38"
      />
      <circle cx="16" cy="7.5" r="2.6" fill="#f97316" />
      <circle cx="7.5" cy="21" r="2.1" fill="#c2410c" />
      <circle cx="24.5" cy="21" r="2.1" fill="#c2410c" />
      <circle cx="16" cy="21" r="1.6" fill="#fff1e7" />
    </svg>
  )
}

export default function App() {
  return (
    <div className="page-glow mx-auto flex min-h-svh max-w-6xl flex-col">
      <header className="sticky top-0 z-10 border-b border-line-soft bg-paper/85 backdrop-blur-md">
        <div className="flex items-center gap-8 px-6 py-3">
          <NavLink to="/" className="flex items-center gap-2.5">
            <Logo />
            <span className="text-[15px] font-semibold tracking-tight text-ink">
              StyleGraph
            </span>
          </NavLink>
          <nav className="flex items-center gap-0.5 text-sm">
            {TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.to === '/'}
                className={({ isActive }) =>
                  `relative rounded-md px-3 py-1.5 transition-colors ${
                    isActive
                      ? 'bg-ink font-medium text-paper'
                      : 'text-ink-soft hover:bg-line-soft hover:text-ink'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <span className="ml-auto hidden items-center gap-1.5 text-xs text-ink-faint sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
            11,761 商品在库
          </span>
        </div>
      </header>
      <main className="flex-1 px-6 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/visual" element={<VisualSearch />} />
          <Route path="/product/:asin" element={<ProductDetail />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
      <footer className="border-t border-line-soft px-6 py-4 text-xs text-ink-faint">
        <div className="flex items-center justify-between">
          <span>StyleGraph · 电商多模态知识图谱 · Neo4j + CLIP ViT-B-32</span>
          <Logo size={20} />
        </div>
      </footer>
    </div>
  )
}
