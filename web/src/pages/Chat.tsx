import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, priceText, type ChatResult } from '../api'

interface Turn {
  q: string
  a?: ChatResult
  err?: string
}

const SUGGESTIONS = ['约会穿什么好看，预算500', '夏天通勤穿什么', '送妈妈什么配饰合适', '户外徒步装备']

export default function Chat() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  async function ask(q: string) {
    const question = q.trim()
    if (!question || busy) return
    setTurns((t) => [...t, { q: question }])
    setInput('')
    setBusy(true)
    try {
      const a = await api.chat(question)
      setTurns((t) => [...t, { q: question, a }])
    } catch {
      setTurns((t) => [...t, { q: question, err: '服务暂不可用，请稍后再试' }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col" style={{ height: 'calc(100svh - 180px)' }}>
      <div className="flex-1 space-y-6 overflow-y-auto pb-4">
        {turns.length === 0 && (
          <div className="pt-16 text-center">
            <h1 className="text-xl font-semibold text-ink">说说你的需求，我来挑</h1>
            <p className="mt-2 text-sm text-ink-soft">从场景、预算、风格任意角度描述</p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-full border border-line bg-white px-3 py-1.5 text-xs text-ink-soft hover:border-brand hover:text-brand"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className="space-y-3">
            <div className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand px-4 py-2.5 text-sm text-white">
                {t.q}
              </div>
            </div>
            {t.a && (
              <div className="space-y-3">
                <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-line bg-white px-4 py-3 text-sm leading-6 text-ink">
                  {t.a.answer}
                </div>
                {t.a.products.length > 0 && (
                  <div className="flex gap-3 overflow-x-auto pb-2">
                    {t.a.products.slice(0, 8).map((p) => (
                      <Link
                        key={p.asin}
                        to={`/product/${p.asin}`}
                        className="w-40 shrink-0 overflow-hidden rounded-lg border border-line bg-white hover:shadow-md"
                      >
                        <div className="aspect-square bg-stone-100">
                          {p.image_url && (
                            <img src={`/img/${p.asin}.jpg`} alt="" loading="lazy" className="h-full w-full object-cover" />
                          )}
                        </div>
                        <div className="space-y-1 p-2">
                          <div className="line-clamp-2 text-[12px] leading-4 text-ink">{p.title}</div>
                          <div className="text-xs font-semibold text-brand">{priceText(p.price)}</div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
            {t.err && <p className="text-sm text-red-700">{t.err}</p>}
          </div>
        ))}
        {busy && <p className="text-sm text-ink-soft">正在检索图谱并生成建议…</p>}
        <div ref={endRef} />
      </div>

      <div className="sticky bottom-0 flex gap-2 border-t border-line bg-paper pt-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ask(input)}
          placeholder="输入你的需求…"
          className="flex-1 rounded-lg border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-brand"
        />
        <button
          onClick={() => ask(input)}
          disabled={busy || !input.trim()}
          className="rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
        >
          发送
        </button>
      </div>
    </div>
  )
}
