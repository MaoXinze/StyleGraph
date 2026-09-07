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
      <header className="sticky top-0 z-10 border-b border-line bg-paper/90 backdrop-blur">
        <div className="flex items-center gap-6 px-6 py-3">
          <NavLink to="/" className="text-lg font-semibold tracking-tight text-ink">
            StyleGraph
          </NavLink>
          <nav className="flex gap-1 text-sm">
            {TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.to === '/'}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 ${isActive ? 'bg-brand-soft font-medium text-brand' : 'text-ink-soft hover:text-ink'}`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 px-6 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/visual" element={<VisualSearch />} />
          <Route path="/product/:asin" element={<ProductDetail />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
      <footer className="border-t border-line px-6 py-3 text-xs text-ink-soft">
        StyleGraph · 多模态知识图谱 · Neo4j + CLIP
      </footer>
    </div>
  )
}
