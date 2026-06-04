import { useCallback } from 'react'
import { CellSlot } from '@/entities/panel/CellSlot'
import { Skeleton } from '@/shared/ui/Skeleton'
import { useDisplayDetail } from '@/entities/display/hooks'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import type { Cell } from '@/shared/api/types'

interface DisplayGridProps {
  displaySlug: string
  onCellSelect?: (cell: Cell) => void
  selectedCellId?: number | null
}

function GridSkeleton({ rows, cols }: { rows: number; cols: number }) {
  return (
    <div className="space-y-0.5">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-0.5">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} style={{ width: '44px', height: '44px', borderRadius: '3px' }} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function DisplayGrid({ displaySlug, onCellSelect, selectedCellId }: DisplayGridProps) {
  const { data: display, isLoading, error } = useDisplayDetail(displaySlug)
  const showSkeleton = useDeferredLoading(isLoading)

  const handleClick = useCallback((cell: Cell) => {
    onCellSelect?.(cell)
  }, [onCellSelect])

  if (error) return (
    <div className="flex items-center justify-center h-40 text-xs" style={{ color: 'var(--err)' }}>
      Ошибка загрузки
    </div>
  )

  if (showSkeleton) return <GridSkeleton rows={10} cols={10} />

  if (!display) return null

  // Группируем ячейки по рядам
  const rows: Cell[][] = []
  for (let r = 1; r <= display.rows; r++) {
    rows.push(display.cells.filter(c => c.row === r).sort((a, b) => a.col - b.col))
  }

  const cellSize = Math.max(26, Math.min(52, Math.floor(660 / display.cols)))

  return (
    <div>
      {/* Legend */}
      <div className="flex items-center gap-4 mb-3">
        {[
          { color: 'var(--bg-3)',   label: 'Норма' },
          { color: 'var(--warn)',   label: 'Заявка' },
          { color: 'var(--warn)',   label: 'В работе' },
          { color: 'var(--ok)',     label: 'Выполнено' },
          { color: 'var(--err)',    label: 'Невозможно' },
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1 text-2xs" style={{ color: 'var(--fg-faint)' }}>
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>

      {/* Grid */}
      <div className="inline-block">
        {rows.map((row, ri) => (
          <div key={ri} className="flex gap-0.5 mb-0.5">
            {row.map(cell => (
              <CellSlot
                key={cell.id}
                cell={cell}
                size={cellSize}
                selected={cell.id === selectedCellId}
                onClick={handleClick}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
