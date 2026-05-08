import { Badge } from '@/shared/ui/Badge'
import { formatRelative } from '@/shared/lib/utils'
import type { ApplicationListItem } from '@/shared/api/types'

interface ApplicationCardProps {
  application: ApplicationListItem
  selected?: boolean
  onClick?: () => void
  compact?: boolean
}

export function ApplicationCard({ application: app, selected, onClick, compact }: ApplicationCardProps) {
  const status = app.status
  const baseStyle: React.CSSProperties = {
    width: '100%', textAlign: 'left', cursor: 'pointer',
    background: selected ? 'var(--bg-3)' : 'transparent',
    border: 'none', outline: 'none',
    transition: 'background 80ms linear',
  }

  if (compact) {
    return (
      <button
        onClick={onClick}
        style={{ ...baseStyle, display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 10px', borderRadius: 'var(--r-sm)', borderLeft: selected ? `2px solid var(--accent)` : '2px solid transparent' }}
        onMouseOver={e => { if (!selected) e.currentTarget.style.background = 'var(--bg-2)' }}
        onMouseOut={e => { if (!selected) e.currentTarget.style.background = 'transparent' }}
      >
        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: status.color.hex }} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--fg-faint)', minWidth: '36px' }}>
          #{app.id}
        </span>
        <span className="flex-1 text-left truncate" style={{ fontSize: '12px', color: 'var(--fg-dim)' }}>
          {app.display.description ?? app.display.slug}
        </span>
        <span style={{ fontSize: '11px', color: 'var(--fg-faint)', flexShrink: 0 }}>
          {formatRelative(app.last_update_date_time)}
        </span>
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      style={{
        ...baseStyle,
        display: 'flex', flexDirection: 'column', gap: '6px',
        padding: '10px', borderRadius: 'var(--r-md)',
        margin: '2px 4px',
        border: `1px solid ${selected ? 'var(--accent-edge)' : 'var(--border-subtle)'}`,
        background: selected ? 'var(--bg-2)' : 'transparent',
      }}
      onMouseOver={e => { if (!selected) e.currentTarget.style.background = 'var(--bg-2)'; e.currentTarget.style.borderColor = 'var(--border)' }}
      onMouseOut={e => { if (!selected) e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'var(--border-subtle)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--fg-faint)' }}>#{app.id}</span>
          <Badge
            label={status.description ?? status.name}
            bgHex={status.color.hex}
            fgHex={status.color_text.hex}
            icon={status.icon?.unicode_symbol}
          />
        </div>
        <span style={{ fontSize: '11px', color: 'var(--fg-faint)' }}>
          {formatRelative(app.last_update_date_time)}
        </span>
      </div>
      <div className="flex items-center gap-2" style={{ fontSize: '12px', color: 'var(--fg-dim)' }}>
        <span className="truncate">{app.display.description ?? app.display.slug}</span>
        <span style={{ color: 'var(--border)' }}>·</span>
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg-faint)', fontSize: '11px' }}>
          {app.panel.name}/{app.cell.position}
        </span>
      </div>
    </button>
  )
}
