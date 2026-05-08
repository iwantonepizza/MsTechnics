import { cn } from '@/shared/lib/utils'

interface BadgeProps {
  label: string
  bgHex?: string      // hex цвет фона (из БД)
  fgHex?: string      // hex цвет текста (из БД)
  icon?: string       // unicode emoji
  variant?: 'ok' | 'warn' | 'err' | 'info' | 'neutral' | 'brand'
  className?: string
}

const VARIANT_STYLES: Record<string, React.CSSProperties> = {
  ok:      { background: 'var(--ok-faint)',   color: 'var(--ok)' },
  warn:    { background: 'var(--warn-faint)', color: 'var(--warn)' },
  err:     { background: 'var(--err-faint)',  color: 'var(--err)' },
  info:    { background: 'var(--info-faint)', color: 'var(--info)' },
  neutral: { background: 'var(--bg-3)',       color: 'var(--fg-dim)' },
  brand:   { background: 'color-mix(in oklch, var(--brand) 18%, transparent)', color: 'var(--brand)' },
}

export function Badge({ label, bgHex, fgHex, icon, variant, className }: BadgeProps) {
  const style: React.CSSProperties = variant
    ? VARIANT_STYLES[variant]
    : {
        background: bgHex ? `${bgHex}22` : 'var(--bg-3)',
        color: fgHex ?? bgHex ?? 'var(--fg-dim)',
        border: bgHex ? `1px solid ${bgHex}44` : '1px solid var(--border-subtle)',
      }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-1.5 h-5 rounded text-2xs font-medium whitespace-nowrap',
        className,
      )}
      style={{ borderRadius: 'var(--r-sm)', ...style }}
    >
      {icon && <span>{icon}</span>}
      {label}
    </span>
  )
}
