import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  BatteryFull,
  Cable,
  Clock,
  Cpu,
  HandMetal,
  Layers,
  Monitor,
  Package,
  Plug,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { useChangeDepartment, usePanels } from '@/entities/panel/hooks'
import { useStorage } from '@/entities/storage/hooks'
import { useActivityLog } from '@/entities/activity/hooks'
import { useDisplays } from '@/entities/display/hooks'
import { PanelCreateButton } from '@/features/panels/PanelCreateButton'
import { PanelDeleteButton } from '@/features/panels/PanelDeleteButton'
import { Skeleton, SkeletonList } from '@/shared/ui/Skeleton'
import { EmptyState } from '@/shared/ui/EmptyState'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { cn, formatRelative } from '@/shared/lib/utils'
import type { Panel, StorageItem } from '@/shared/api/types'

// T-7-033: целевые отделы для DnD. 'monitor' исключён — установка в ячейку
// идёт через replace_panel_in_cell, не через смену department.
const DND_ALLOWED_TARGETS = new Set(['zip', 'hand', 'service'])
const DRAG_MIME = 'application/x-panel-id'

const DEPARTMENTS = [
  { key: 'zip',     label: 'ЗИП',         emoji: 'P' },
  { key: 'hand',    label: 'На руках',     emoji: 'H' },
  { key: 'service', label: 'Сервис',       emoji: 'W' },
  { key: 'monitor', label: 'На экранах',   emoji: 'M' },
]

const DEPARTMENTS_V2: Array<{
  key: string
  label: string
  Icon: LucideIcon
}> = [
  { key: 'zip', label: 'ЗИП', Icon: Package },
  { key: 'hand', label: 'На руках', Icon: HandMetal },
  { key: 'service', label: 'Сервис', Icon: Wrench },
  { key: 'monitor', label: 'На экранах', Icon: Monitor },
]

function PanelChip({ panel, selected, onSelect }: { panel: Panel; selected: boolean; onSelect: (panel: Panel) => void }) {
  // T-7-033: HTML5 drag — без external deps.
  const handleDragStart = (e: React.DragEvent<HTMLButtonElement>) => {
    e.dataTransfer.setData(DRAG_MIME, String(panel.id))
    e.dataTransfer.setData('text/plain', panel.name)
    e.dataTransfer.effectAllowed = 'move'
    e.currentTarget.style.opacity = '0.48'
  }

  const handleDragEnd = (e: React.DragEvent<HTMLButtonElement>) => {
    e.currentTarget.style.opacity = '1'
  }

  return (
    <button
      type="button"
      id={`panel-${panel.id}`}
      data-testid={`panel-chip-${panel.id}`}
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-2xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 cursor-grab active:cursor-grabbing"
      title={panel.comment ?? undefined}
      onClick={() => onSelect(panel)}
      style={{
        background: selected ? 'var(--bg-3)' : 'var(--bg-1)',
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
  targetPanelId,
  onPanelSelect,
}: {
  dept: { key: string; label: string; Icon: LucideIcon }
  displayId: string | null
  selectedPanelId: number | null
  targetPanelId: number | null
  onPanelSelect: (panel: Panel) => void
}) {
  const { data = [], isLoading } = usePanels({
    department: dept.key,
    display: displayId,
    fetchAll: Boolean(displayId),
  })
  const show = useDeferredLoading(isLoading)
  const changeDept = useChangeDepartment()
  const [dragHover, setDragHover] = useState(false)

  const isDropTarget = DND_ALLOWED_TARGETS.has(dept.key)
  const lamels = { data: [] as StorageItem[], isLoading: false }
  const hubs = { data: [] as StorageItem[], isLoading: false }
  const wires = { data: [] as StorageItem[], isLoading: false }
  const powerBlocks = { data: [] as StorageItem[], isLoading: false }
  const connectors = { data: [] as StorageItem[], isLoading: false }

  const sectionsV2: Array<{
    key: string
    label: string
    Icon: LucideIcon
    data: StorageItem[]
    loading: boolean
  }> = [
    { key: 'lamels', label: 'Ламели', Icon: Layers, data: lamels.data ?? [], loading: lamels.isLoading },
    { key: 'hubs', label: 'Хабы', Icon: Cpu, data: hubs.data ?? [], loading: hubs.isLoading },
    { key: 'wires', label: 'Провода', Icon: Cable, data: wires.data ?? [], loading: wires.isLoading },
    { key: 'power-blocks', label: 'Блоки питания', Icon: BatteryFull, data: powerBlocks.data ?? [], loading: powerBlocks.isLoading },
    { key: 'connectors', label: 'Коннекторы', Icon: Plug, data: connectors.data ?? [], loading: connectors.isLoading },
  ]

  useEffect(() => {
    if (!targetPanelId || selectedPanelId === targetPanelId) return

    const panel = data.find(item => item.id === targetPanelId)
    if (!panel) return

    onPanelSelect(panel)
    window.setTimeout(() => {
      document.getElementById(`panel-${targetPanelId}`)?.scrollIntoView({
        block: 'center',
        behavior: 'smooth',
      })
    }, 0)
  }, [data, onPanelSelect, selectedPanelId, targetPanelId])

  // T-7-033: HTML5 DnD handlers
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.dataTransfer.dropEffect = isDropTarget ? 'move' : 'none'
    if (!isDropTarget) return
    // Принимаем только наш MIME (другие drag-операции системы пропускаем).
    if (!e.dataTransfer.types.includes(DRAG_MIME)) return
    e.preventDefault()
    setDragHover(true)
  }
  const handleDragLeave = () => setDragHover(false)
  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    if (!isDropTarget) return
    setDragHover(false)
    const idRaw = e.dataTransfer.getData(DRAG_MIME)
    const id = Number(idRaw)
    if (!Number.isFinite(id) || id <= 0) return
    // Если панель уже в этом отделе — игнор.
    if (data.some(p => p.id === id)) return
    e.preventDefault()
    try {
      await changeDept.mutateAsync({ id, department: dept.key })
      toast.success(`Панель перемещена в «${dept.label}»`)
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { detail?: string } } })?.response?.data
      toast.error(data?.detail ?? 'Не удалось переместить панель')
    }
  }

  return (
    <div
      className="flex flex-col min-h-0"
      data-testid={`panel-column-${dept.key}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        borderRight: '1px solid var(--border-subtle)',
        background: dragHover ? 'var(--accent-faint)' : undefined,
        outline: dragHover
          ? '2px dashed var(--accent)'
          : !isDropTarget
            ? '1px dashed var(--border-subtle)'
            : undefined,
        outlineOffset: '-2px',
        cursor: isDropTarget ? 'default' : 'not-allowed',
      }}
    >
      <div
        className="flex items-center justify-between px-3 py-2 shrink-0"
        style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-1)' }}
      >
        <div className="flex items-center gap-1.5 text-xs font-medium" style={{ color: 'var(--fg-dim)' }}>
          <dept.Icon size={12} />
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

function StorageSection({ highlightedStorageId }: { highlightedStorageId: string | null }) {
  const lamels = useStorage('lamels')
  const hubs = useStorage('hubs')
  const wires = useStorage('wires')
  const powerBlocks = useStorage('power-blocks')
  const connectors = useStorage('connectors')

  const sectionsV2: Array<{
    key: string
    label: string
    Icon: LucideIcon
    data: StorageItem[]
    loading: boolean
  }> = [
    { key: 'lamels', label: 'Ламели', Icon: Layers, data: lamels.data ?? [], loading: lamels.isLoading },
    { key: 'hubs', label: 'Хабы', Icon: Cpu, data: hubs.data ?? [], loading: hubs.isLoading },
    { key: 'wires', label: 'Провода', Icon: Cable, data: wires.data ?? [], loading: wires.isLoading },
    { key: 'power-blocks', label: 'Блоки питания', Icon: BatteryFull, data: powerBlocks.data ?? [], loading: powerBlocks.isLoading },
    { key: 'connectors', label: 'Коннекторы', Icon: Plug, data: connectors.data ?? [], loading: connectors.isLoading },
  ]

  const sections: Array<{
    key: string
    label: string
    data: StorageItem[]
    loading: boolean
  }> = [
    { key: 'lamels', label: 'Ламели', data: lamels.data ?? [], loading: lamels.isLoading },
    { key: 'hubs', label: 'Хабы', data: hubs.data ?? [], loading: hubs.isLoading },
    { key: 'wires', label: 'Провода', data: wires.data ?? [], loading: wires.isLoading },
    { key: 'power-blocks', label: 'Блоки питания', data: powerBlocks.data ?? [], loading: powerBlocks.isLoading },
    { key: 'connectors', label: 'Коннекторы', data: connectors.data ?? [], loading: connectors.isLoading },
  ]

  useEffect(() => {
    if (!highlightedStorageId) return

    window.setTimeout(() => {
      document.getElementById(highlightedStorageId)?.scrollIntoView({
        block: 'center',
        behavior: 'smooth',
      })
    }, 0)
  }, [highlightedStorageId, sectionsV2])

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
        {sectionsV2.map(sec => (
          <div key={sec.key}>
            <p className="mb-1 flex items-center gap-1.5 text-2xs font-medium" style={{ color: 'var(--fg-mute)' }}>
              <sec.Icon size={11} />
              <span>{sec.label}</span>
            </p>
            {sec.loading ? (
              <SkeletonList rows={2} height="20px" />
            ) : sec.data.length === 0 ? (
              <p className="text-2xs" style={{ color: 'var(--fg-faint)' }}>Пусто</p>
            ) : (
              <div className="space-y-0.5">
                {sec.data.map((item: StorageItem) => (
                  <div
                    key={item.id}
                    id={`storage-${sec.key}-${item.id}`}
                    data-testid={`storage-item-${item.name}`}
                    className={cn(
                      'storage-item-card rounded border px-2 py-2 text-xs',
                      item.is_low_stock && 'storage-item-card--low',
                      highlightedStorageId === `storage-${sec.key}-${item.id}` && 'storage-item-card--low',
                    )}
                    style={{
                      borderColor: highlightedStorageId === `storage-${sec.key}-${item.id}`
                        ? 'var(--accent-edge)'
                        : item.is_low_stock ? 'var(--err)' : 'var(--border-subtle)',
                      background: highlightedStorageId === `storage-${sec.key}-${item.id}`
                        ? 'var(--accent-faint)'
                        : item.is_low_stock ? 'var(--err-faint)' : 'var(--bg-1)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span style={{ color: item.is_low_stock ? 'var(--err)' : 'var(--fg-dim)' }}>{item.name}</span>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono)',
                          color: item.is_low_stock ? 'var(--err)' : item.count === 0 ? 'var(--err)' : 'var(--ok)',
                        }}
                      >
                        {item.count}
                      </span>
                    </div>
                    {item.is_low_stock && (
                      <div className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
                        Меньше {item.low_stock_threshold}
                      </div>
                    )}
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

function PanelDetails({ panel, onPanelDeleted }: { panel: Panel | null; onPanelDeleted: () => void }) {
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
      <div className="pt-1 flex justify-end">
        <PanelDeleteButton panel={panel} onDeleted={onPanelDeleted} />
      </div>
    </div>
  )
}

function HistoryRail({
  displaySlug,
  selectedPanel,
  onPanelDeleted,
}: {
  displaySlug: string | null
  selectedPanel: Panel | null
  onPanelDeleted: () => void
}) {
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
      <PanelDetails panel={selectedPanel} onPanelDeleted={onPanelDeleted} />
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
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const { data: displays = [] } = useDisplays()
  const [selectedDisplay, setSelectedDisplay] = useState<string | null>(displaySlug ?? null)
  const [selectedPanel, setSelectedPanel] = useState<Panel | null>(null)
  const targetPanelId = Number(searchParams.get('panel_id') ?? '')
  const highlightedStorageId = location.hash.startsWith('#storage-')
    ? location.hash.slice(1)
    : null

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
            data-testid="zip-display-filter"
            className="text-xs"
            style={{
              background: 'var(--bg-1)', border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--r-sm)', color: 'var(--fg)',
              padding: '3px 8px', height: 'var(--h-btn-sm)', cursor: 'pointer',
            }}
          >
            <option value="" style={{ background: 'var(--bg-0)', color: 'var(--fg)' }}>
              Все экраны
            </option>
            {displays.map(d => (
              <option key={d.id} value={d.slug} style={{ background: 'var(--bg-0)', color: 'var(--fg)' }}>
                {d.city.name} — {d.description ?? d.name}
              </option>
            ))}
          </select>
        </div>
        <PanelCreateButton presetDisplayId={selectedDisplayModel?.id ?? null} />
      </div>

      {/* 6 columns */}
      <div
        className="grid flex-1 min-h-0"
        style={{ gridTemplateColumns: '1fr 1fr 1fr 1fr 180px 220px' }}
      >
        {DEPARTMENTS_V2.map(dept => (
          <PanelColumn
            key={dept.key}
            dept={dept}
            displayId={selectedDisplayId}
            selectedPanelId={selectedPanel?.id ?? null}
            targetPanelId={Number.isInteger(targetPanelId) && targetPanelId > 0 ? targetPanelId : null}
            onPanelSelect={setSelectedPanel}
          />
        ))}
        <StorageSection highlightedStorageId={highlightedStorageId} />
        <HistoryRail
          displaySlug={selectedDisplay}
          selectedPanel={selectedPanel}
          onPanelDeleted={() => setSelectedPanel(null)}
        />
      </div>
    </div>
  )
}
