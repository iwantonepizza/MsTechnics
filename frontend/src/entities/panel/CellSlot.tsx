import { cn } from '@/shared/lib/utils'
import type { Cell } from '@/shared/api/types'

// Цвета статусов через CSS vars из tokens.css
const STATUS_BG: Record<string, string> = {
  default:          'var(--bg-3)',
  sent_to_control:  'var(--warn)',
  apply_in_control: 'color-mix(in oklch, var(--warn) 70%, var(--err))',
  sent_to_service:  'color-mix(in oklch, var(--warn) 40%, var(--err))',
  work_in_service:  'var(--accent)',
  done:             'var(--ok)',
  unable:           'var(--err)',
  archive_done:     'var(--bg-4)',
  archive_unable:   'var(--bg-4)',
}

interface CellSlotProps {
  cell: Cell
  selected?: boolean
  onClick?: (cell: Cell) => void
  size?: number
}

export function CellSlot({ cell, selected, onClick, size = 44 }: CellSlotProps) {
  const panel = cell.panel
  const statusName = panel?.application_status_name ?? 'default'
  const bg = STATUS_BG[statusName] ?? 'var(--bg-3)'
  const conditionIcon = panel?.condition?.icon?.unicode_symbol ?? ''
  const hasActiveApp = statusName !== 'default'

  return (
    <button
      onClick={() => onClick?.(cell)}
      title={panel
        ? `${panel.name} · ${panel.condition?.description ?? ''} · поз.${cell.position}`
        : `Ячейка ${cell.position} — пусто`}
      style={{
        width: size, height: size,
        background: bg,
        borderRadius: '3px',
        border: selected ? '2px solid var(--accent)' : '2px solid transparent',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        opacity: panel ? 1 : 0.25,
        transform: selected ? 'scale(1.07)' : 'scale(1)',
        transition: 'transform 80ms linear, border-color 80ms linear',
        outline: 'none',
      }}
    >
      {conditionIcon && (
        <span style={{ fontSize: '9px', lineHeight: 1, marginBottom: '1px' }}>{conditionIcon}</span>
      )}
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '9px',
        color: 'rgba(255,255,255,0.7)', lineHeight: 1,
      }}>
        {cell.position}
      </span>
      {/* Dot — активная заявка */}
      {hasActiveApp && (
        <div style={{
          position: 'absolute', top: '2px', right: '2px',
          width: '5px', height: '5px', borderRadius: '50%',
          background: 'rgba(255,255,255,0.7)',
        }} />
      )}
    </button>
  )
}
