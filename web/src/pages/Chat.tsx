import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, priceText, type ChatResult } from '../api'

interface Turn {
  q: string
  a?: ChatResult
  err?: string
}

const SUGGESTIONS = ['约会穿什么好看，预算500', '夏天通勤穿什么', '送妈妈什么配饰合适', '户外徒步装备']

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm border border-line-soft bg-white px-4 py-3">
      {[0, 1, 2].map((i) => (
        <span key={i} className="typing-dot h-1.5 w-1.5 rounded-full bg-brand-mid" />
      ))}
    </div>
  )
}

export default function Chat() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, busy])

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
    <div className="mx-auto flex max-w-3xl flex-col" style={{ height: 'calc(100svh - 200px)' }}>
      <div className="flex-1 space-y-7 overflow-y-auto pb-4">
        {turns.length === 0 && (
          <div className="rise pt-16 text-center">
            <h1 className="text-[22px] font-semibold tracking-tight text-ink">
              说说你的需求，我来挑
            </h1>
            <p className="mt-2 text-sm text-ink-soft">从场景、预算、风格任意角度描述</p>
            <div className="mt-7 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-full border border-line bg-white px-3.5 py-1.5 text-xs text-ink-soft transition-colors hover:border-brand-mid hover:text-brand"
                >
                  {s}
                </button>
              ))}
            </div>
            <div className="mx-auto mt-10 grid max-w-xl grid-cols-1 gap-3 text-left sm:grid-cols-3">
              {[
                { t: '理解意图', d: '自然语言解析为品类、场合、价格区间' },
                { t: '图谱检索', d: '属性边 + 场景边 + 向量召回混合取数' },
                { t: '生成建议', d: '结合价格与评分解释推荐理由' },
              ].map((c) => (
                <div
                  key={c.t}
                  className="rounded-xl border border-line-soft bg-white p-4 shadow-card"
                >
                  <div className="text-xs font-medium text-brand">{c.t}</div>
                  <p className="mt-1.5 text-xs leading-5 text-ink-soft">{c.d}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className="rise space-y-4">
            <div className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-sm leading-6 text-white">
                {t.q}
              </div>
            </div>
            {t.a && (
              <div className="space-y-4">
                <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-line-soft bg-white px-4 py-3 text-sm leading-6 text-ink shadow-card">
                  {t.a.answer}
                </div>
                {t.a.products.length > 0 && (
                  <div className="flex gap-3 overflow-x-auto pb-2">
                    {t.a.products.slice(0, 8).map((p) => (
                      <Link
                        key={p.asin}
                        to={`/product/${p.asin}`}
                        className="w-40 shrink-0 overflow-hidden rounded-xl border border-line-soft bg-white shadow-card transition-all hover:-translate-y-0.5 hover:shadow-lift"
                      >
                        <div className="aspect-square overflow-hidden bg-line-soft">
                          {p.image_url && (
                            <img
                              src={`/img/${p.asin}.jpg`}
                              alt=""
                              loading="lazy"
                              className="h-full w-full object-cover"
                            />
                          )}
                        </div>
                        <div className="space-y-1 p-2.5">
                          <div className="line-clamp-2 text-[12px] leading-4 text-ink">
                            {p.title}
                          </div>
                          <div className="text-xs font-semibold text-brand-deep">
                            {priceText(p.price)}
                          </div>
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
        {busy && <TypingDots />}
        <div ref={endRef} />
      </div>

      <div className="sticky bottom-0 bg-paper pt-3">
        <div className="flex items-center gap-2 rounded-2xl border border-line bg-white p-1.5 shadow-card transition-shadow focus-within:border-brand-mid focus-within:shadow-lift">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask(input)}
            placeholder="输入你的需求…"
            className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-ink-faint"
          />
          <button
            onClick={() => ask(input)}
            disabled={busy || !input.trim()}
            className="shrink-0 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-deep disabled:cursor-not-allowed disabled:opacity-35"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}
