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

export default function App() {
  return (
    <div className="mx-auto flex min-h-svh max-w-6xl flex-col">
      <header className="sticky top-0 z-10 border-b border-line-soft bg-paper/85 backdrop-blur-md">
        <div className="flex items-center gap-8 px-6 py-3.5">
          <NavLink to="/" className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand text-[13px] font-bold text-white">
              S
            </span>
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
        StyleGraph · 电商多模态知识图谱 · Neo4j + CLIP ViT-B-32
      </footer>
    </div>
  )
}
