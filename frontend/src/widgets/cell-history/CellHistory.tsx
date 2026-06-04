import { useState } from 'react'
import { useInfiniteActivityLog } from '@/entities/activity/hooks'
import { InfiniteScrollSentinel } from '@/shared/ui/InfiniteScrollSentinel'
import { SkeletonList } from '@/shared/ui/Skeleton'
import { formatRelative } from '@/shared/lib/utils'

type Mode = 'panel' | 'place'

/**
 * T-8-004: история выбранной ячейки.
 * Тумблер «История панели / История места», по умолчанию — панель (если установлена).
 */
export function CellHistory({
  cellId,
  panelId,
}: {
  cellId: number
  panelId: number | null
}) {
  const [mode, setMode] = useState<Mode>(panelId ? 'panel' : 'place')
  const effectiveMode: Mode = panelId ? mode : 'place'

  const historyQuery = useInfiniteActivityLog(
    effectiveMode === 'panel' && panelId ? { panel: panelId } : { cell: cellId },
  )
  const data = historyQuery.entries

  return (
    <div className="pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
      <div className="mb-2 flex gap-1">
        <button
          type="button"
          disabled={!panelId}
          onClick={() => setMode('panel')}
          className="flex-1 rounded px-2 py-1 text-2xs transition-colors disabled:opacity-40"
          style={{
            background: effectiveMode === 'panel' ? 'var(--accent)' : 'var(--bg-2)',
            color: effectiveMode === 'panel' ? 'var(--accent-ink)' : 'var(--fg-dim)',
            border: `1px solid ${effectiveMode === 'panel' ? 'var(--accent-edge)' : 'var(--border-subtle)'}`,
          }}
          data-testid="cell-history-panel"
        >
          История панели
        </button>
        <button
          type="button"
          onClick={() => setMode('place')}
          className="flex-1 rounded px-2 py-1 text-2xs transition-colors"
          style={{
            background: effectiveMode === 'place' ? 'var(--accent)' : 'var(--bg-2)',
            color: effectiveMode === 'place' ? 'var(--accent-ink)' : 'var(--fg-dim)',
            border: `1px solid ${effectiveMode === 'place' ? 'var(--accent-edge)' : 'var(--border-subtle)'}`,
          }}
          data-testid="cell-history-place"
        >
          История места
        </button>
      </div>
      <div className="max-h-48 overflow-y-auto space-y-1">
        {historyQuery.isLoading ? (
          <SkeletonList rows={4} height="26px" />
        ) : data.length === 0 ? (
          <p className="py-2 text-center text-2xs" style={{ color: 'var(--fg-faint)' }}>История пуста</p>
        ) : (
          <>
            {data.map((entry: { id: number; description: string | null; actor_name: string | null; occurred_at: string }) => (
              <div key={entry.id} className="text-xs" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 4 }}>
                <div style={{ color: 'var(--fg-dim)' }}>{entry.description}</div>
                <div className="flex justify-between text-2xs" style={{ color: 'var(--fg-faint)' }}>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{entry.actor_name}</span>
                  <span>{formatRelative(entry.occurred_at)}</span>
                </div>
              </div>
            ))}
            <InfiniteScrollSentinel
              hasMore={Boolean(historyQuery.hasNextPage)}
              loading={historyQuery.isFetchingNextPage}
              onLoadMore={() => void historyQuery.fetchNextPage()}
            />
          </>
        )}
      </div>
    </div>
  )
}
