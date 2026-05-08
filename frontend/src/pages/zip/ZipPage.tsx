import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Clock, Package, Plus } from 'lucide-react'
import { usePanels } from '@/entities/panel/hooks'
import { useStorage } from '@/entities/storage/hooks'
import { useActivityLog } from '@/entities/activity/hooks'
import { useDisplays } from '@/entities/display/hooks'
import { Skeleton, SkeletonList } from '@/shared/ui/Skeleton'
import { EmptyState } from '@/shared/ui/EmptyState'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { formatRelative } from '@/shared/lib/utils'
import type { Panel } from '@/shared/api/types'

const DEPARTMENTS = [
  { key: 'zip',     label: 'ЗИП',         emoji: '📦' },
  { key: 'hand',    label: 'На руках',     emoji: '✋' },
  { key: 'service', label: 'Сервис',       emoji: '🔧' },
  { key: 'monitor', label: 'На экранах',   emoji: '📺' },
]

function PanelChip({ panel, selected, onSelect }: { panel: Panel; selected: boolean; onSelect: (panel: Panel) => void }) {
  return (
    <button
      type="button"
      className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-2xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      title={panel.comment ?? undefined}
      onClick={() => onSelect(panel)}
      style={{
        background: selected ? 'var(--bg-3)' : 'var(--bg-2)',
        border: `1px solid ${selected ? 'var(--accent-edge)' : 'transparent'}`,
        borderRadius: 'var(--r-sm)',
        outlineColor: 'var(--accent)',
      }}
    >
      <span className="truncate" style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg-dim)' }}>{panel.name}</span>
      <span className="shrink-0">{panel.condition?.icon?.unicode_symbol ?? '—'}</span>
    </button>
  )
}

function PanelColumn({
  dept,
  displayId,
  selectedPanelId,
  onPanelSelect,
}: {
  dept: { key: string; label: string; emoji: string }
  displayId: string | null
  selectedPanelId: number | null
  onPanelSelect: (panel: Panel) => void
}) {
  const { data = [], isLoading } = usePanels({ department: dept.key, display: displayId })
  const show = useDeferredLoading(isLoading)

  return (
    <div
      className="flex flex-col min-h-0"
      style={{ borderRight: '1px solid var(--border-subtle)' }}
    >
      <div
        className="flex items-center justify-between px-3 py-2 shrink-0"
        style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-1)' }}
      >
        <div className="flex items-center gap-1.5 text-xs font-medium" style={{ color: 'var(--fg-dim)' }}>
          <span>{dept.emoji}</span>
          <span>{dept.label}</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--fg-faint)' }}>
          {data.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
        {show ? (
          <SkeletonList rows={4} height="22px" />
        ) : data.length === 0 ? (
          <div className="text-2xs text-center py-4" style={{ color: 'var(--fg-faint)' }}>Пусто</div>
        ) : (
          data.map(p => (
            <PanelChip
              key={p.id}
              panel={p}
              selected={p.id === selectedPanelId}
              onSelect={onPanelSelect}
            />
          ))
        )}
      </div>
    </div>
  )
}

function StorageSection({ displaySlug }: { displaySlug: string | null }) {
  const lamels = useStorage('lamels', displaySlug)
  const hubs = useStorage('hubs', displaySlug)
  const wires = useStorage('wires', displaySlug)

  const sections = [
    { label: '🧩 Ламели', data: lamels.data ?? [], loading: lamels.isLoading },
    { label: '🔌 Хабы',   data: hubs.data ?? [],   loading: hubs.isLoading },
    { label: '🔗 Провода',data: wires.data ?? [],   loading: wires.isLoading },
  ]

  return (
    <div
      className="flex flex-col min-h-0"
      style={{ borderRight: '1px solid var(--border-subtle)' }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 text-xs font-medium shrink-0"
        style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-1)', color: 'var(--fg-dim)' }}
      >
        <Package size={12} />
        Расходники
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {sections.map(sec => (
          <div key={sec.label}>
            <p className="text-2xs font-medium mb-1" style={{ color: 'var(--fg-mute)' }}>{sec.label}</p>
            {sec.loading ? (
              <SkeletonList rows={2} height="20px" />
            ) : sec.data.length === 0 ? (
              <p className="text-2xs" style={{ color: 'var(--fg-faint)' }}>Пусто</p>
            ) : (
              <div className="space-y-0.5">
                {sec.data.map((item: any) => (
                  <div key={item.id} className="flex justify-between text-xs">
                    <span style={{ color: 'var(--fg-dim)' }}>{item.name}</span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        color: item.count === 0 ? 'var(--err)' : 'var(--ok)',
                      }}
                    >
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function PanelDetails({ panel }: { panel: Panel | null }) {
  if (!panel) {
    return (
      <div className="p-3 text-2xs" style={{ color: 'var(--fg-faint)', borderBottom: '1px solid var(--border-subtle)' }}>
        Выберите панель для деталей
      </div>
    )
  }

  return (
    <div className="space-y-2 p-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs" style={{ color: 'var(--fg)' }}>{panel.name}</span>
        <span className="text-xs">{panel.condition?.icon?.unicode_symbol ?? '—'}</span>
      </div>
      <div className="grid grid-cols-[80px_1fr] gap-y-1 text-2xs">
        <span style={{ color: 'var(--fg-mute)' }}>Состояние</span>
        <span style={{ color: 'var(--fg-dim)' }}>{panel.condition?.description ?? panel.condition?.name ?? '—'}</span>
        <span style={{ color: 'var(--fg-mute)' }}>Отдел</span>
        <span style={{ color: 'var(--fg-dim)' }}>{panel.department_name ?? '—'}</span>
        <span style={{ color: 'var(--fg-mute)' }}>Экран</span>
        <span style={{ color: 'var(--fg-dim)' }}>{panel.display_id ?? '—'}</span>
        <span style={{ color: 'var(--fg-mute)' }}>Ячейка</span>
        <span style={{ color: 'var(--fg-dim)' }}>{panel.cell_id ?? '—'}</span>
      </div>
      {panel.comment && (
        <div className="rounded p-2 text-2xs" style={{ background: 'var(--bg-2)', color: 'var(--fg-dim)' }}>
          {panel.comment}
        </div>
      )}
    </div>
  )
}

function HistoryRail({ displaySlug, selectedPanel }: { displaySlug: string | null; selectedPanel: Panel | null }) {
  const { data = [], isLoading } = useActivityLog({ display: displaySlug ?? undefined, kind: 'panel.' })
  const show = useDeferredLoading(isLoading)

  return (
    <div className="flex flex-col min-h-0">
      <div
        className="flex items-center gap-2 px-3 py-2 text-xs font-medium shrink-0"
        style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-1)', color: 'var(--fg-dim)' }}
      >
        <Clock size={12} />
        История перемещений
      </div>
      <PanelDetails panel={selectedPanel} />
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {show ? (
          <SkeletonList rows={6} />
        ) : data.length === 0 ? (
          <p className="text-2xs text-center py-4" style={{ color: 'var(--fg-faint)' }}>
            {displaySlug ? 'История пуста' : 'Выберите экран'}
          </p>
        ) : (
          data.map((entry: any) => (
            <div key={entry.id} className="px-2 py-1.5 text-xs" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center gap-1.5 mb-0.5">
                <span style={{ color: 'var(--fg-dim)', fontSize: '11px' }}>▷</span>
                <span style={{ color: 'var(--fg-dim)' }}>{entry.description}</span>
              </div>
              <div className="flex justify-between text-2xs" style={{ color: 'var(--fg-faint)' }}>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{entry.actor_name}</span>
                <span>{formatRelative(entry.occurred_at)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export function ZipPage() {
  const { displaySlug } = useParams<{ displaySlug?: string }>()
  const navigate = useNavigate()
  const { data: displays = [] } = useDisplays()
  const [selectedDisplay, setSelectedDisplay] = useState<string | null>(displaySlug ?? null)
  const [selectedPanel, setSelectedPanel] = useState<Panel | null>(null)

  useEffect(() => {
    setSelectedDisplay(displaySlug ?? null)
  }, [displaySlug])

  const selectedDisplayModel = useMemo(
    () => displays.find(display => display.slug === selectedDisplay) ?? null,
    [displays, selectedDisplay],
  )
  const selectedDisplayId = selectedDisplayModel ? String(selectedDisplayModel.id) : null

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--bg-0)' }}>
      {/* Title bar */}
      <div
        className="flex items-center justify-between px-4 shrink-0"
        style={{ height: 'var(--h-header)', borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-3">
          <h1 className="text-md font-semibold" style={{ color: 'var(--fg)' }}>
            ЗИП — {selectedDisplayModel ? selectedDisplayModel.description ?? selectedDisplayModel.name : 'все экраны'}
          </h1>
          {/* Фильтр по экрану */}
          <select
            value={selectedDisplay ?? ''}
            onChange={e => {
              const next = e.target.value || null
              setSelectedPanel(null)
              navigate(next ? `/zip/${next}` : '/zip')
            }}
            className="text-xs"
            style={{
              background: 'var(--bg-2)', border: '1px solid var(--border)',
              borderRadius: 'var(--r-sm)', color: 'var(--fg-dim)',
              padding: '3px 8px', height: 'var(--h-btn-sm)', cursor: 'pointer',
            }}
          >
            <option value="">Все экраны</option>
            {displays.map(d => (
              <option key={d.id} value={d.slug}>{d.city.name} — {d.description ?? d.name}</option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary sm" disabled title="Добавление панели будет в отдельной backend-задаче">
          <Plus size={12} />
          Панель
        </button>
      </div>

      {/* 6 columns */}
      <div
        className="grid flex-1 min-h-0"
        style={{ gridTemplateColumns: '1fr 1fr 1fr 1fr 180px 220px' }}
      >
        {DEPARTMENTS.map(dept => (
          <PanelColumn
            key={dept.key}
            dept={dept}
            displayId={selectedDisplayId}
            selectedPanelId={selectedPanel?.id ?? null}
            onPanelSelect={setSelectedPanel}
          />
        ))}
        <StorageSection displaySlug={selectedDisplay} />
        <HistoryRail displaySlug={selectedDisplay} selectedPanel={selectedPanel} />
      </div>
    </div>
  )
}
