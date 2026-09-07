/** 页头：中文标题 + 英文副标 + 描述（MiMo 式中英混排） */
export default function PageHeader({
  title,
  en,
  desc,
}: {
  title: string
  en: string
  desc?: string
}) {
  return (
    <div>
      <div className="flex items-baseline gap-2.5">
        <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
        <span className="text-xs text-ink-faint">{en}</span>
      </div>
      {desc && <p className="mt-1 text-sm text-ink-soft">{desc}</p>}
    </div>
  )
}
