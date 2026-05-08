/**
 * T-4-013: DisplayViewPage v2 — по эталону screen-display-view.jsx
 * 3-колонночный layout: grid | panel info | timeline/applications rail
 */
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { X, Plus, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'

import { DisplayGrid } from '@/widgets/display-grid/DisplayGrid'
import { ApplicationsPanel } from '@/widgets/applications-panel/ApplicationsPanel'
import { TransitionModal } from '@/features/applications/TransitionModal'
import { CreateApplicationModal } from '@/features/applications/CreateApplicationModal'
import { ChangeConditionModal, ChangeDepartmentModal, MoveToCellModal } from '@/features/panels/PanelActionModals'
import { EventTimeline } from '@/entities/application/EventTimeline'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Skeleton } from '@/shared/ui/Skeleton'
import { useDisplayAlarms, useDisplayDetail } from '@/entities/display/hooks'
import { useApplicationDetail, useApplicationEvents } from '@/entities/application/hooks'
import { useMe } from '@/features/auth/hooks'
import { useCrumb } from '@/widgets/navigation/CrumbContext'
import { formatDate, formatRelative } from '@/shared/lib/utils'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { useKeyboard } from '@/shared/lib/useKeyboard'
import type { AlarmEvent, Cell } from '@/shared/api/types'
import type { TransitionKind } from '@/features/applications/transitionConfigs'

type Dept = 'monitoring' | 'control' | 'service'

// Transitions доступные по роли
const ROLE_TRANSITIONS: Record<string, TransitionKind[]> = {
  monitoring: [],
  control:    ['apply_in_control', 'sent_to_service', 'archive_done', 'archive_unable'],
  service:    ['work_in_service', 'done', 'unable'],
  admin:      ['apply_in_control', 'sent_to_service', 'work_in_service', 'done', 'unable', 'archive_done', 'archive_unable'],
  all:        ['apply_in_control', 'sent_to_service', 'work_in_service', 'done', 'unable', 'archive_done', 'archive_unable'],
}

const TRANSITION_LABELS: Record<TransitionKind, { emoji: string; label: string }> = {
  apply_in_control: { emoji: '✅', label: 'Принять' },
  sent_to_service:  { emoji: '📤', label: 'В сервис' },
  work_in_service:  { emoji: '🔧', label: 'В работу' },
  done:             { emoji: '✔️', label: 'Выполнено' },
  unable:           { emoji: '❌', label: 'Невозможно' },
  archive_done:     { emoji: '📦', label: 'Архив' },
  archive_unable:   { emoji: '📦', label: 'Архив' },
  delete_application:{ emoji: '🗑️', label: 'Удалить' },
}

const INPUT_STYLE: React.CSSProperties = {
  background: 'var(--bg-1)', border: '1px solid var(--border-subtle)',
  borderRadius: 'var(--r-sm)', color: 'var(--fg-mute)',
  fontSize: '11px', padding: '4px 8px', fontFamily: 'var(--font-mono)',
}

interface DisplayViewPageProps { department: Dept }

export function DisplayViewPage({ department }: DisplayViewPageProps) {
  const { displaySlug } = useParams<{ citySlug: string; displaySlug: string }>()
  const { data: me } = useMe()
  const { setCrumb } = useCrumb()

  const { data: display, isLoading: displayLoading } = useDisplayDetail(displaySlug ?? null)
  const showSkeleton = useDeferredLoading(displayLoading)

  const [selectedCell, setSelectedCell] = useState<Cell | null>(null)
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null)
  const [transitionKind, setTransitionKind] = useState<TransitionKind | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [createComment, setCreateComment] = useState('')
  const [panelAction, setPanelAction] = useState<'condition' | 'department' | 'move' | null>(null)
  const [railTab, setRailTab] = useState<'applications' | 'alarms'>('applications')

  const { data: selectedApp } = useApplicationDetail(selectedAppId)
  const { data: events = [] } = useApplicationEvents(selectedAppId)
  const { data: alarms = [] } = useDisplayAlarms(displaySlug ?? null, false)

  useEffect(() => {
    if (display) {
      setCrumb(
        <span className="flex items-center gap-2 text-xs" style={{ color: 'var(--fg-mute)' }}>
          <span>{display.city.name}</span>
          <ChevronRight size={10} style={{ color: 'var(--fg-faint)' }} />
          <span style={{ color: 'var(--fg-dim)' }}>{display.description ?? display.name}</span>
        </span>
      )
    }
    return () => setCrumb(null)
  }, [display, setCrumb])

  const handleCellClick = useCallback((cell: Cell) => {
    setSelectedCell(cell)
    setSelectedAppId(null)
  }, [])

  const handleAppSelect = useCallback((id: number) => {
    setSelectedAppId(id)
    setSelectedCell(null)
  }, [])

  const role = me?.permission ?? ''
  const canCreate = role === 'monitoring' || role === 'admin' || role === 'all'

  const openCreateForCell = useCallback((cell: Cell, comment = '') => {
    setSelectedCell(cell)
    setSelectedAppId(null)
    setCreateComment(comment)
    setCreateOpen(true)
  }, [])

  const handleAlarmCreate = useCallback((alarm: AlarmEvent) => {
    const cell = display?.cells.find(item => item.id === alarm.cell_id)
    if (!cell?.panel) {
      toast.error('Для аларма не найдена установленная панель')
      return
    }
    openCreateForCell(
      cell,
      `VNNOX: receiving card ${alarm.receiving_card_no} abnormal. ${alarm.raw_position}`,
    )
  }, [display?.cells, openCreateForCell])

  // Доступные переходы = пересечение доступных для роли + next_possible от бэка
  const availableTransitions: TransitionKind[] = (() => {
    if (!selectedApp) return []
    const roleTransitions = ROLE_TRANSITIONS[role] ?? []
    const nextPossible = (selectedApp.status.next_possible ?? []).map(n => n.target_state)
    return roleTransitions.filter(t => nextPossible.includes(t))
  })()

  const shortcutMap = useMemo(() => ({
    R: () => {
      if (department === 'service' && selectedApp?.status.name === 'sent_to_service') setTransitionKind('work_in_service')
    },
    D: () => {
      if (department === 'service' && selectedApp?.status.name === 'work_in_service') setTransitionKind('done')
    },
    U: () => {
      if (department === 'service' && selectedApp?.status.name === 'work_in_service') setTransitionKind('unable')
    },
    A: () => {
      if (department === 'control' && selectedApp?.status.name === 'sent_to_control') setTransitionKind('apply_in_control')
    },
    S: () => {
      if (department === 'control' && selectedApp?.status.name === 'apply_in_control') setTransitionKind('sent_to_service')
    },
    V: () => {
      if (department === 'control' && selectedApp?.status.name === 'done') setTransitionKind('archive_done')
      if (department === 'control' && selectedApp?.status.name === 'unable') setTransitionKind('archive_unable')
    },
    N: () => {
      if ((department === 'monitoring' || department === 'control') && selectedCell?.panel) openCreateForCell(selectedCell)
    },
  }), [department, selectedApp, selectedCell, openCreateForCell])
  useKeyboard(shortcutMap, !transitionKind && !createOpen && !panelAction)

  if (showSkeleton) {
    return (
      <div className="flex h-full" style={{ background: 'var(--bg-0)' }}>
        <div className="flex-1 p-4"><Skeleton style={{ height: '100%', borderRadius: 'var(--r-lg)' }} /></div>
        <div style={{ width: '360px', borderLeft: '1px solid var(--border-subtle)' }}><Skeleton style={{ height: '100%' }} /></div>
        <div style={{ width: '320px', borderLeft: '1px solid var(--border-subtle)' }}><Skeleton style={{ height: '100%' }} /></div>
      </div>
    )
  }

  if (!display) {
    return (
      <div className="flex items-center justify-center h-full text-xs" style={{ color: 'var(--fg-mute)' }}>
        Экран не найден
      </div>
    )
  }

  return (
    <div className="flex h-full" style={{ background: 'var(--bg-0)' }}>

      {/* ── Col 1: Grid ───────────────────────────────────────────────── */}
      <div
        className="flex flex-col flex-1 min-w-0"
        style={{ borderRight: '1px solid var(--border-subtle)' }}
      >
        {/* Title bar */}
        <div
          className="flex items-center justify-between px-4 shrink-0"
          style={{ height: 'var(--h-header)', borderBottom: '1px solid var(--border-subtle)' }}
        >
          <div>
            <span className="text-md font-semibold" style={{ color: 'var(--fg)', letterSpacing: '-0.01em' }}>
              {display.description ?? display.name}
            </span>
            <span className="ml-3 text-xs" style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}>
              {display.rows}×{display.cols}
            </span>
          </div>
          {canCreate && selectedCell?.panel && (
            <Button variant="primary" size="sm" icon={<Plus size={11} />} onClick={() => openCreateForCell(selectedCell)}>
              Заявка
            </Button>
          )}
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-auto p-4">
          <DisplayGrid
            displaySlug={display.slug ?? displaySlug ?? ''}
            selectedCellId={selectedCell?.id ?? null}
            onCellSelect={handleCellClick}
          />
        </div>
      </div>

      {/* ── Col 2: Panel info + Application detail ────────────────────── */}
      <div
        className="flex flex-col"
        style={{ width: '360px', flexShrink: 0, borderRight: '1px solid var(--border-subtle)', background: 'var(--bg-1)' }}
      >
        {selectedApp ? (
          <>
            {/* App header */}
            <div
              className="flex items-center justify-between px-4 py-3 shrink-0"
              style={{ borderBottom: '1px solid var(--border-subtle)' }}
            >
              <div className="flex items-center gap-2">
                <span style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  #{selectedApp.id}
                </span>
                <Badge
                  label={selectedApp.status.description ?? selectedApp.status.name}
                  bgHex={selectedApp.status.color.hex}
                  fgHex={selectedApp.status.color_text.hex}
                  icon={selectedApp.status.icon?.unicode_symbol}
                />
              </div>
              <button
                onClick={() => setSelectedAppId(null)}
                className="flex items-center justify-center w-6 h-6 rounded transition-colors"
                style={{ color: 'var(--fg-mute)' }}
              >
                <X size={12} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
              {/* KV Info */}
              <div className="space-y-1.5">
                {[
                  ['Экран',       selectedApp.display.description ?? selectedApp.display.slug ?? '—'],
                  ['Позиция',     selectedApp.cell.position ?? '—'],
                  ['Панель',      selectedApp.panel.name],
                  ['Исполнитель', selectedApp.executor ? `${selectedApp.executor.first_name} ${selectedApp.executor.last_name}` : '—'],
                  ['Обновлено',   formatRelative(selectedApp.last_update_date_time)],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span style={{ color: 'var(--fg-mute)' }}>{k}</span>
                    <span style={{ color: 'var(--fg-dim)', fontFamily: k === 'Позиция' || k === 'Панель' ? 'var(--font-mono)' : undefined }}>
                      {v}
                    </span>
                  </div>
                ))}
              </div>

              {/* Initial comment */}
              {selectedApp.initial_comment && (
                <div
                  className="p-3 rounded-md text-xs"
                  style={{ background: 'var(--bg-2)', border: '1px solid var(--border-subtle)', color: 'var(--fg-dim)' }}
                >
                  {selectedApp.initial_comment}
                </div>
              )}

              {/* Action buttons */}
              {availableTransitions.length > 0 && (
                <div className="space-y-1">
                  <span className="text-2xs uppercase tracking-widest" style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}>
                    Действия
                  </span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {availableTransitions.map(t => {
                      const meta = TRANSITION_LABELS[t]
                      const isDanger = t === 'unable' || t === 'delete_application'
                      return (
                        <Button
                          key={t}
                          variant={isDanger ? 'danger' : t.includes('archive') ? 'ghost' : 'primary'}
                          size="sm"
                          onClick={() => setTransitionKind(t)}
                        >
                          {meta.emoji} {meta.label}
                        </Button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Timeline */}
              {events.length > 0 && (
                <div>
                  <span className="text-2xs uppercase tracking-widest mb-2 block" style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}>
                    История
                  </span>
                  <EventTimeline events={events} />
                </div>
              )}
            </div>
          </>
        ) : selectedCell ? (
          <>
            <div
              className="flex items-center justify-between px-4 py-3 shrink-0"
              style={{ borderBottom: '1px solid var(--border-subtle)' }}
            >
              <span className="text-sm font-medium" style={{ color: 'var(--fg)' }}>
                Позиция {selectedCell.position}
              </span>
              <button
                onClick={() => setSelectedCell(null)}
                className="flex items-center justify-center w-6 h-6 rounded"
                style={{ color: 'var(--fg-mute)' }}
              >
                <X size={12} />
              </button>
            </div>

            <div className="p-4 flex-1">
              {selectedCell.panel ? (
                <div className="space-y-3">
                  {[
                    ['Панель',     selectedCell.panel.name],
                    ['Состояние',  selectedCell.panel.condition.description ?? selectedCell.panel.condition.name],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span style={{ color: 'var(--fg-mute)' }}>{k}</span>
                      <span style={{ color: 'var(--fg-dim)', fontFamily: k === 'Панель' ? 'var(--font-mono)' : undefined }}>
                        {k === 'Состояние'
                          ? `${selectedCell.panel!.condition.icon?.unicode_symbol ?? ''} ${v}`
                          : v
                        }
                      </span>
                    </div>
                  ))}
                  {selectedCell.panel.comment && (
                    <div className="text-xs mt-2" style={{ color: 'var(--fg-faint)' }}>
                      {selectedCell.panel.comment}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-1.5 pt-1">
                    <Button variant="ghost" size="sm" onClick={() => setPanelAction('condition')}>
                      Состояние
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setPanelAction('department')}>
                      Отдел
                    </Button>
                  </div>
                  {canCreate && (
                    <Button
                      variant="primary" size="sm"
                      icon={<Plus size={11} />}
                      onClick={() => openCreateForCell(selectedCell)}
                      className="w-full justify-center mt-2"
                    >
                      Создать заявку
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs" style={{ color: 'var(--fg-mute)' }}>Ячейка пустая</p>
                  <Button variant="primary" size="sm" onClick={() => setPanelAction('move')}>
                    Поставить панель
                  </Button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-xs text-center px-4" style={{ color: 'var(--fg-faint)' }}>
              Выберите заявку или нажмите на ячейку
            </p>
          </div>
        )}
      </div>

      {/* ── Col 3: Applications panel ─────────────────────────────────── */}
      <div
        className="flex flex-col"
        style={{ width: '320px', flexShrink: 0, background: 'var(--bg-0)' }}
      >
        <div
          className="flex items-center gap-1 p-2 shrink-0"
          style={{ borderBottom: '1px solid var(--border-subtle)' }}
        >
          {([
            ['applications', 'Заявки'],
            ['alarms', `VNNOX ${alarms.length ? alarms.length : ''}`],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setRailTab(key)}
              className="flex-1 h-7 text-xs rounded-sm transition-colors"
              style={{
                color: railTab === key ? 'var(--fg)' : 'var(--fg-mute)',
                background: railTab === key ? 'var(--bg-2)' : 'transparent',
                border: railTab === key ? '1px solid var(--border-subtle)' : '1px solid transparent',
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {railTab === 'applications' ? (
          <ApplicationsPanel
            displaySlug={display.slug ?? displaySlug ?? ''}
            department={department}
            onApplicationSelect={handleAppSelect}
            selectedId={selectedAppId}
          />
        ) : (
          <AlarmRail alarms={alarms} canCreate={canCreate} onCreate={handleAlarmCreate} />
        )}
      </div>

      {/* Modals */}
      {createOpen && selectedCell && display && (
        <CreateApplicationModal
          open={createOpen}
          onClose={() => { setCreateOpen(false); setCreateComment('') }}
          cell={selectedCell}
          displayId={display.id}
          initialComment={createComment}
        />
      )}
      {transitionKind && selectedApp && (
        <TransitionModal
          open
          onClose={() => setTransitionKind(null)}
          application={selectedApp}
          targetState={transitionKind}
        />
      )}
      {panelAction === 'condition' && selectedCell?.panel && (
        <ChangeConditionModal
          open
          onClose={() => setPanelAction(null)}
          panel={selectedCell.panel}
        />
      )}
      {panelAction === 'department' && selectedCell?.panel && (
        <ChangeDepartmentModal
          open
          onClose={() => setPanelAction(null)}
          panel={selectedCell.panel}
        />
      )}
      {panelAction === 'move' && selectedCell && !selectedCell.panel && (
        <MoveToCellModal
          open
          onClose={() => setPanelAction(null)}
          cell={selectedCell}
        />
      )}
    </div>
  )
}

function AlarmRail({ alarms, canCreate, onCreate }: {
  alarms: AlarmEvent[]
  canCreate: boolean
  onCreate: (alarm: AlarmEvent) => void
}) {
  if (alarms.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-6 text-center text-xs" style={{ color: 'var(--fg-faint)' }}>
        Открытых VNNOX-алармов нет
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-2">
      {alarms.map(alarm => {
        const isFaulty = alarm.type === 'faulty'
        return (
          <div
            key={alarm.id}
            className="rounded-md p-3 space-y-2"
            style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)' }}
          >
            <div className="flex items-center justify-between gap-2">
              <Badge
                label={isFaulty ? 'Open' : 'Recovery'}
                bgHex={isFaulty ? '#7f1d1d' : '#14532d'}
                fgHex="#ffffff"
              />
              <span className="text-2xs" style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}>
                {formatDate(alarm.occurred_at)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-y-1 text-xs">
              <span style={{ color: 'var(--fg-mute)' }}>Ячейка</span>
              <span style={{ color: 'var(--fg-dim)', fontFamily: 'var(--font-mono)' }}>
                {alarm.cell_position ?? String(alarm.receiving_card_no).padStart(2, '0')}
              </span>
              <span style={{ color: 'var(--fg-mute)' }}>Панель</span>
              <span style={{ color: 'var(--fg-dim)', fontFamily: 'var(--font-mono)' }}>
                {alarm.panel_name ?? '—'}
              </span>
            </div>
            <p className="text-2xs line-clamp-2" style={{ color: 'var(--fg-faint)' }}>
              {alarm.raw_position}
            </p>
            {isFaulty && canCreate && (
              <Button
                variant="primary"
                size="sm"
                icon={<Plus size={11} />}
                onClick={() => onCreate(alarm)}
                className="w-full justify-center"
              >
                Создать заявку
              </Button>
            )}
          </div>
        )
      })}
    </div>
  )
}
