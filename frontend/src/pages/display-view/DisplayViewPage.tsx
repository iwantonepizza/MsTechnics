/**
 * Display view: grid | detail | applications/alarms rail.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  Archive,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ExternalLink,
  Plus,
  Send,
  Trash2,
  Wrench,
  X,
  type LucideIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { ApplicationDetailSheet } from '@/entities/application/ApplicationDetailSheet'
import {
  useApplicationDetail,
  useApplicationEvents,
  useDeleteApplication,
} from '@/entities/application/hooks'
import { useDisplayAlarms, useDisplayDetail } from '@/entities/display/hooks'
import { CreateApplicationModal } from '@/features/applications/CreateApplicationModal'
import { TransitionModal } from '@/features/applications/TransitionModal'
import type { TransitionKind } from '@/features/applications/transitionConfigs'
import { useMe } from '@/features/auth/hooks'
import {
  ChangeConditionModal,
  ChangeDepartmentModal,
  MoveToCellModal,
  PanelRemovalModal,
  type PanelLike,
} from '@/features/panels/PanelActionModals'
import type { AlarmEvent, Cell } from '@/shared/api/types'
import { Badge } from '@/shared/ui/Badge'
import { Button, type ButtonProps } from '@/shared/ui/Button'
import { ConfirmDialog, useConfirmDialog } from '@/shared/ui/ConfirmDialog'
import { Skeleton } from '@/shared/ui/Skeleton'
import { ResizeHandle } from '@/shared/ui/ResizeHandle'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { formatDate, getErrorMessage } from '@/shared/lib/utils'
import { useKeyboard } from '@/shared/lib/useKeyboard'
import { useResizableValue, useResizeDrag } from '@/shared/lib/useResizableValue'
import { ApplicationsPanel } from '@/widgets/applications-panel/ApplicationsPanel'
import { useCrumb } from '@/widgets/navigation/CrumbContext'
import { DisplayGrid } from '@/widgets/display-grid/DisplayGrid'
import { DisplayNotes } from '@/widgets/display-notes/DisplayNotes'
import { DailyTasksPanel } from '@/widgets/daily-tasks/DailyTasksPanel'
import { CellHistory } from '@/widgets/cell-history/CellHistory'

type Dept = 'monitoring' | 'control' | 'service'

const ROLE_TRANSITIONS: Record<string, TransitionKind[]> = {
  monitoring: [],
  control: ['apply_in_control', 'sent_to_service', 'archive_done', 'archive_unable'],
  service: ['work_in_service', 'done', 'unable'],
  admin: [
    'apply_in_control',
    'sent_to_service',
    'work_in_service',
    'done',
    'unable',
    'archive_done',
    'archive_unable',
  ],
  all: [
    'apply_in_control',
    'sent_to_service',
    'work_in_service',
    'done',
    'unable',
    'archive_done',
    'archive_unable',
  ],
}

const ACTION_LABELS: Record<TransitionKind, { Icon: LucideIcon; label: string }> = {
  apply_in_control: { Icon: Check, label: 'Принять' },
  sent_to_service: { Icon: Send, label: 'В сервис' },
  work_in_service: { Icon: Wrench, label: 'В работу' },
  done: { Icon: CheckCheck, label: 'Выполнено' },
  unable: { Icon: X, label: 'Невозможно' },
  archive_done: { Icon: Archive, label: 'Архив' },
  archive_unable: { Icon: Archive, label: 'Архив' },
  delete_application: { Icon: Trash2, label: 'Удалить' },
}

const ADMIN_ROLES = new Set(['admin', 'all'])
const MONITORING_CREATEABLE_CONDITIONS = new Set(['problem', 'error', 'broken', 'unrecoverable'])

interface DisplayViewPageProps {
  department: Dept
}

interface ApplicationSheetAction {
  key: string
  label: string
  icon: ReactNode
  variant: ButtonProps['variant']
}

function isAdminRole(role: string) {
  return ADMIN_ROLES.has(role)
}

function canMonitoringCreateApplication(conditionName: string | null) {
  return Boolean(conditionName && MONITORING_CREATEABLE_CONDITIONS.has(conditionName))
}

function getTransitionVariant(transition: TransitionKind): ButtonProps['variant'] {
  if (transition === 'unable' || transition === 'delete_application') {
    return 'danger'
  }
  if (transition.includes('archive')) {
    return 'ghost'
  }
  return 'primary'
}

export function DisplayViewPage({ department }: DisplayViewPageProps) {
  const { displaySlug } = useParams<{ citySlug: string; displaySlug: string }>()
  const [searchParams] = useSearchParams()
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
  const [panelRemovalContext, setPanelRemovalContext] = useState<{
    panel: PanelLike
    applicationId?: number
  } | null>(null)
  const [railTab, setRailTab] = useState<'applications' | 'alarms'>('applications')
  const [deleteCandidate, setDeleteCandidate] = useState<number | null>(null)

  const deleteDialog = useConfirmDialog()
  const deleteApplication = useDeleteApplication()

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
        </span>,
      )
    }

    return () => setCrumb(null)
  }, [display, setCrumb])

  useEffect(() => {
    if (!display) {
      return
    }

    const applicationId = Number(searchParams.get('app_id') ?? '')
    if (Number.isInteger(applicationId) && applicationId > 0) {
      setSelectedAppId(applicationId)
      setSelectedCell(null)
      return
    }

    const panelId = Number(searchParams.get('panel_id') ?? '')
    if (!Number.isInteger(panelId) || panelId <= 0) {
      return
    }

    const cell = display.cells.find(item => item.panel?.id === panelId)
    if (!cell) {
      return
    }

    setSelectedCell(cell)
    setSelectedAppId(null)
  }, [display, searchParams])

  const handleCellClick = useCallback((cell: Cell) => {
    setSelectedCell(cell)
    setSelectedAppId(null)
  }, [])

  const handleAppSelect = useCallback((id: number) => {
    setSelectedAppId(id)
    setSelectedCell(null)
  }, [])

  const role = me?.permission ?? ''
  const isAdmin = isAdminRole(role)
  const isMonitoring = role === 'monitoring'
  const isService = role === 'service'

  const canCreateForCell = useCallback(
    (cell: Cell | null) => {
      const conditionName = cell?.panel?.condition.name ?? null
      if (isAdmin) {
        return Boolean(cell?.panel)
      }
      if (!isMonitoring) {
        return false
      }
      return canMonitoringCreateApplication(conditionName)
    },
    [isAdmin, isMonitoring],
  )

  const openCreateForCell = useCallback(
    (cell: Cell, comment = '') => {
      if (!canCreateForCell(cell)) {
        return
      }
      setSelectedCell(cell)
      setSelectedAppId(null)
      setCreateComment(comment)
      setCreateOpen(true)
    },
    [canCreateForCell],
  )

  const handlePanelRemoved = useCallback(() => {
    setSelectedCell(null)
    setPanelRemovalContext(null)
  }, [])

  const handleDeleteApplication = useCallback(async () => {
    if (deleteCandidate == null) {
      return
    }

    try {
      await deleteApplication.mutateAsync({ id: deleteCandidate })
      toast.success('Заявка удалена')
      setSelectedAppId(current => (current === deleteCandidate ? null : current))
      setDeleteCandidate(null)
    } catch (error) {
      toast.error(getErrorMessage(error))
      throw error
    }
  }, [deleteApplication, deleteCandidate])

  const handleAlarmCreate = useCallback(
    (alarm: AlarmEvent) => {
      const cell = display?.cells.find(item => item.id === alarm.cell_id)
      if (!cell?.panel) {
        toast.error('Для аларма не найдена установленная панель')
        return
      }

      openCreateForCell(
        cell,
        `VNNOX: receiving card ${alarm.receiving_card_no} abnormal. ${alarm.raw_position}`,
      )
    },
    [display?.cells, openCreateForCell],
  )

  const canCreateFromAlarm = useCallback(
    (alarm: AlarmEvent) => {
      const cell = display?.cells.find(item => item.id === alarm.cell_id) ?? null
      return canCreateForCell(cell)
    },
    [canCreateForCell, display?.cells],
  )

  const availableTransitions = useMemo(() => {
    if (!selectedApp) {
      return []
    }
    const roleTransitions = ROLE_TRANSITIONS[role] ?? []
    const nextPossible = (selectedApp.status.next_possible ?? []).map(item => item.target_state)
    return roleTransitions.filter(transition => nextPossible.includes(transition))
  }, [role, selectedApp])

  const selectedAppPanel = useMemo(
    () => display?.cells.find(item => item.panel?.id === selectedApp?.panel.id)?.panel ?? null,
    [display?.cells, selectedApp?.panel.id],
  )

  const canMutatePanelsInDepartment = department !== 'monitoring'
  const canChangeCondition = Boolean(
    selectedCell?.panel &&
      canMutatePanelsInDepartment &&
      (isAdmin || isService),
  )
  const canChangeDepartment = Boolean(
    selectedCell?.panel && canMutatePanelsInDepartment && (isAdmin || isService),
  )
  const canRemoveSelectedPanel = Boolean(
    selectedCell?.panel && canMutatePanelsInDepartment && (isAdmin || isService),
  )
  const canInstallPanel = Boolean(
    selectedCell && !selectedCell.panel && canMutatePanelsInDepartment && (isAdmin || isService),
  )
  const canCreateSelectedCellApplication = canCreateForCell(selectedCell)
  const canDeleteSelectedApplication =
    selectedApp?.status.name === 'sent_to_control' && (isAdmin || isMonitoring)
  const canRemovePanelFromApplication = Boolean(
    selectedAppPanel && canMutatePanelsInDepartment && (isAdmin || isService),
  )
  const showCameraCard = department === 'monitoring' && Boolean(display?.camera_link)
  const showDailyTasks = department === 'monitoring' || department === 'control'
  const [detailWidth, setDetailWidth] = useResizableValue({
    storageKey: `display-view:${department}:detail-width`,
    defaultValue: 360,
    min: 280,
    max: 560,
  })
  const [railWidth, setRailWidth] = useResizableValue({
    storageKey: `display-view:${department}:rail-width`,
    defaultValue: 320,
    min: 280,
    max: 560,
  })
  const [railMainHeight, setRailMainHeight] = useResizableValue({
    storageKey: `display-view:${department}:rail-main-height`,
    defaultValue: 360,
    min: 180,
    max: 720,
  })
  const onDetailResize = useResizeDrag({
    value: detailWidth,
    setValue: setDetailWidth,
    axis: 'x',
    direction: -1,
    min: 280,
    max: 560,
  })
  const onRailResize = useResizeDrag({
    value: railWidth,
    setValue: setRailWidth,
    axis: 'x',
    direction: -1,
    min: 280,
    max: 560,
  })
  const onRailMainResize = useResizeDrag({
    value: railMainHeight,
    setValue: setRailMainHeight,
    axis: 'y',
    direction: 1,
    min: 180,
    max: 720,
  })

  const selectedAppActions: ApplicationSheetAction[] = [
    ...(canDeleteSelectedApplication
      ? [
          {
            key: 'delete_application',
            label: ACTION_LABELS.delete_application.label,
            icon: <ACTION_LABELS.delete_application.Icon size={12} />,
            variant: 'danger' as const,
          },
        ]
      : []),
    ...availableTransitions.map(transition => {
      const meta = ACTION_LABELS[transition]
        return {
          key: transition,
          label: meta.label,
          icon: <meta.Icon size={12} />,
          variant: getTransitionVariant(transition),
        }
      }),
  ]

  const shortcutMap = useMemo(
    () => ({
      R: () => {
        if (department === 'service' && selectedApp?.status.name === 'sent_to_service') {
          setTransitionKind('work_in_service')
        }
      },
      D: () => {
        if (department === 'service' && selectedApp?.status.name === 'work_in_service') {
          setTransitionKind('done')
        }
      },
      U: () => {
        if (department === 'service' && selectedApp?.status.name === 'work_in_service') {
          setTransitionKind('unable')
        }
      },
      A: () => {
        if (department === 'control' && selectedApp?.status.name === 'sent_to_control') {
          setTransitionKind('apply_in_control')
        }
      },
      S: () => {
        if (department === 'control' && selectedApp?.status.name === 'apply_in_control') {
          setTransitionKind('sent_to_service')
        }
      },
      V: () => {
        if (department === 'control' && selectedApp?.status.name === 'done') {
          setTransitionKind('archive_done')
        }
        if (department === 'control' && selectedApp?.status.name === 'unable') {
          setTransitionKind('archive_unable')
        }
      },
      N: () => {
        if (canCreateSelectedCellApplication && selectedCell?.panel) {
          openCreateForCell(selectedCell)
        }
      },
    }),
    [canCreateSelectedCellApplication, department, openCreateForCell, selectedApp, selectedCell],
  )

  useKeyboard(shortcutMap, !transitionKind && !createOpen && !panelAction)

  if (showSkeleton) {
    return (
      <div className="flex h-full flex-col lg:flex-row" style={{ background: 'var(--bg-0)' }}>
        <div className="flex-1 p-4">
          <Skeleton style={{ height: '100%', borderRadius: 'var(--r-lg)' }} />
        </div>
        <div
          className="border-t lg:w-[360px] lg:border-l lg:border-t-0"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <Skeleton style={{ height: '100%' }} />
        </div>
        <div
          className="border-t lg:w-[320px] lg:border-l lg:border-t-0"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <Skeleton style={{ height: '100%' }} />
        </div>
      </div>
    )
  }

  if (!display) {
    return (
      <div className="flex h-full items-center justify-center text-xs" style={{ color: 'var(--fg-mute)' }}>
        Экран не найден
      </div>
    )
  }

  return (
    <div
      className="display-view-page display-view-resizable h-full overflow-y-auto lg:overflow-hidden"
      style={{
        '--display-detail-width': `${detailWidth}px`,
        '--display-rail-width': `${railWidth}px`,
        '--display-rail-main-height': `${railMainHeight}px`,
        background: 'var(--bg-0)',
      } as CSSProperties}
      data-testid="display-view-layout"
    >
      <div
        className="display-view-grid-column flex min-w-0 flex-col border-b lg:border-b-0 lg:border-r"
        style={{ borderColor: 'var(--border-subtle)' }}
        data-testid="display-view-grid-column"
      >
        <div
          className="flex shrink-0 items-center justify-between gap-3 px-4"
          style={{ height: 'var(--h-header)', borderBottom: '1px solid var(--border-subtle)' }}
        >
          <div className="min-w-0">
            <span
              className="block truncate text-md font-semibold"
              style={{ color: 'var(--fg)', letterSpacing: '-0.01em' }}
            >
              {display.description ?? display.name}
            </span>
            <span className="text-xs" style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}>
              {display.rows}Г—{display.cols}
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 max-h-[70vh] lg:max-h-none">
          <DisplayGrid
            displaySlug={display.slug ?? displaySlug ?? ''}
            selectedCellId={selectedCell?.id ?? null}
            onCellSelect={handleCellClick}
          />
        </div>

      </div>

      <ResizeHandle
        orientation="vertical"
        label="Изменить ширину деталей"
        className="hidden lg:flex"
        onPointerDown={onDetailResize}
        testId="display-detail-resize-handle"
      />

      <div
        className="display-view-detail-column flex w-full shrink-0 flex-col border-t lg:border-t-0 lg:border-r"
        style={{
          borderColor: 'var(--border-subtle)',
          background: 'var(--bg-1)',
        }}
        data-testid="display-view-detail-column"
      >
        {selectedApp ? (
          <ApplicationDetailSheet
            application={selectedApp}
            events={events}
            cityName={display.city.name}
            actions={selectedAppActions}
            canRemovePanel={canRemovePanelFromApplication}
            onAction={action => {
              if (action === 'delete_application') {
                setDeleteCandidate(selectedApp.id)
                deleteDialog.ask()
                return
              }
              setTransitionKind(action as TransitionKind)
            }}
            onRemovePanel={() =>
              selectedAppPanel &&
              setPanelRemovalContext({
                panel: selectedAppPanel,
                applicationId: selectedApp.id,
              })
            }
            onClose={() => setSelectedAppId(null)}
          />
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
                className="flex h-6 w-6 items-center justify-center rounded"
                style={{ color: 'var(--fg-mute)' }}
              >
                <X size={12} />
              </button>
            </div>

            <div className="flex-1 p-4">
              {selectedCell.panel ? (
                <div className="space-y-3">
                  {[
                    ['Панель', selectedCell.panel.name],
                    ['Состояние', selectedCell.panel.condition.description ?? selectedCell.panel.condition.name],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between text-xs">
                      <span style={{ color: 'var(--fg-mute)' }}>{label}</span>
                      <span
                        style={{
                          color: 'var(--fg-dim)',
                          fontFamily: label === 'Панель' ? 'var(--font-mono)' : undefined,
                        }}
                      >
                        {label === 'Состояние'
                          ? `${selectedCell.panel?.condition.icon?.unicode_symbol ?? ''} ${value}`
                          : value}
                      </span>
                    </div>
                  ))}
                  {selectedCell.panel.comment ? (
                    <div className="mt-2 text-xs" style={{ color: 'var(--fg-faint)' }}>
                      {selectedCell.panel.comment}
                    </div>
                  ) : null}

                  {canChangeCondition || canChangeDepartment ? (
                    <div className="grid grid-cols-2 gap-1.5 pt-1">
                      {canChangeCondition ? (
                        <Button variant="ghost" size="sm" onClick={() => setPanelAction('condition')}>
                          Состояние
                        </Button>
                      ) : null}
                      {canChangeDepartment ? (
                        <Button variant="ghost" size="sm" onClick={() => setPanelAction('department')}>
                          Отдел
                        </Button>
                      ) : null}
                    </div>
                  ) : null}

                  {canRemoveSelectedPanel ? (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setPanelRemovalContext({ panel: selectedCell.panel! })}
                      className="w-full justify-center"
                    >
                      Снять панель
                    </Button>
                  ) : null}

                  {canCreateSelectedCellApplication ? (
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<Plus size={11} />}
                      onClick={() => openCreateForCell(selectedCell)}
                      className="mt-2 w-full justify-center"
                    >
                      Создать заявку
                    </Button>
                  ) : null}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs" style={{ color: 'var(--fg-mute)' }}>
                    Ячейка пустая
                  </p>
                  {canInstallPanel ? (
                    <Button variant="primary" size="sm" onClick={() => setPanelAction('move')}>
                      Поставить панель
                    </Button>
                  ) : null}
                </div>
              )}

              {/* T-8-004: история панели / места */}
              <CellHistory
                cellId={selectedCell.id}
                panelId={selectedCell.panel?.id ?? null}
              />
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="px-4 text-center text-xs" style={{ color: 'var(--fg-faint)' }}>
              Выберите заявку или нажмите на ячейку
            </p>
          </div>
        )}
      </div>

      <ResizeHandle
        orientation="vertical"
        label="Изменить ширину правой панели"
        className="hidden lg:flex"
        onPointerDown={onRailResize}
        testId="display-rail-resize-handle"
      />

      <div
        className="display-view-rail-column flex w-full shrink-0 flex-col border-t lg:border-t-0"
        style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-0)' }}
        data-testid="display-view-rail-column"
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
              className="flex-1 h-7 rounded-sm text-xs transition-colors"
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
        <div className="display-view-rail-main">
          {railTab === 'applications' ? (
            <ApplicationsPanel
              displaySlug={display.slug ?? displaySlug ?? ''}
              department={department}
              onApplicationSelect={handleAppSelect}
              selectedId={selectedAppId}
            />
          ) : (
            <AlarmRail alarms={alarms} canCreate={canCreateFromAlarm} onCreate={handleAlarmCreate} />
          )}
        </div>
        <ResizeHandle
          orientation="horizontal"
          label="Изменить высоту заявок"
          className="hidden lg:flex"
          onPointerDown={onRailMainResize}
          testId="display-rail-main-resize-handle"
        />
        {showCameraCard ? <DisplayCameraCard cameraLink={display.camera_link!} /> : null}
        {showDailyTasks ? (
          <DailyTasksPanel
            cityId={display.city?.id}
            readOnly={department === 'control'}
            defaultOpen
          />
        ) : null}
        <DisplayNotes slug={display.slug ?? displaySlug ?? ''} />
      </div>

      {createOpen && selectedCell ? (
        <CreateApplicationModal
          open={createOpen}
          onClose={() => {
            setCreateOpen(false)
            setCreateComment('')
          }}
          cell={selectedCell}
          displayId={display.id}
          initialComment={createComment}
        />
      ) : null}

      {transitionKind && selectedApp ? (
        <TransitionModal
          open
          onClose={() => setTransitionKind(null)}
          application={selectedApp}
          targetState={transitionKind}
        />
      ) : null}

      {panelAction === 'condition' && selectedCell?.panel ? (
        <ChangeConditionModal
          open
          onClose={() => setPanelAction(null)}
          panel={selectedCell.panel}
        />
      ) : null}

      {panelAction === 'department' && selectedCell?.panel ? (
        <ChangeDepartmentModal
          open
          onClose={() => setPanelAction(null)}
          panel={selectedCell.panel}
        />
      ) : null}

      {panelAction === 'move' && selectedCell && !selectedCell.panel ? (
        <MoveToCellModal open onClose={() => setPanelAction(null)} cell={selectedCell} />
      ) : null}

      {panelRemovalContext ? (
        <PanelRemovalModal
          open
          onClose={() => setPanelRemovalContext(null)}
          panel={panelRemovalContext.panel}
          applicationId={panelRemovalContext.applicationId}
          onRemoved={handlePanelRemoved}
        />
      ) : null}

      <ConfirmDialog
        open={deleteDialog.props.open}
        onClose={() => {
          setDeleteCandidate(null)
          deleteDialog.close()
        }}
        onConfirm={handleDeleteApplication}
        title="Удалить заявку?"
        description={
          deleteCandidate != null
            ? `Заявка #${deleteCandidate} будет удалена без возможности восстановления.`
            : 'Заявка будет удалена без возможности восстановления.'
        }
        confirmText="Удалить"
        variant="danger"
      />
    </div>
  )
}

function DisplayCameraCard({
  cameraLink,
}: {
  cameraLink: string
}) {
  const [expanded, setExpanded] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!expanded) {
      setLoadFailed(false)
      setIsLoading(false)
      return
    }

    setLoadFailed(false)
    setIsLoading(true)
  }, [expanded, cameraLink])

  useEffect(() => {
    if (!expanded || !isLoading || loadFailed) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setLoadFailed(true)
      setIsLoading(false)
    }, 5000)

    return () => window.clearTimeout(timeoutId)
  }, [cameraLink, expanded, isLoading, loadFailed])

  return (
    <section
      className="shrink-0 border-t px-4 py-3"
      style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)' }}
      data-testid="display-camera-card"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <div className="text-xs font-medium" style={{ color: 'var(--fg)' }}>
            Камера
          </div>
          <div className="text-2xs" style={{ color: 'var(--fg-faint)' }}>
            Поток с площадки для мониторинга
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon={expanded ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          onClick={() => setExpanded(value => !value)}
        >
          {expanded ? 'Свернуть' : 'Развернуть'}
        </Button>
      </div>

      {expanded ? (
        <div className="space-y-2">
          <div
            className="overflow-hidden rounded-md border"
            style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-0)' }}
          >
            <iframe
              key={cameraLink}
              src={cameraLink}
              title="Камера экрана"
              className="h-48 w-full border-0"
              loading="eager"
              allow="autoplay; fullscreen; picture-in-picture"
              allowFullScreen
              onLoad={() => {
                setLoadFailed(false)
                setIsLoading(false)
              }}
              onError={() => {
                setLoadFailed(true)
                setIsLoading(false)
              }}
            />
          </div>
          {loadFailed ? (
            <div
              className="rounded-md border px-3 py-2 text-xs"
              style={{
                borderColor: 'var(--border-subtle)',
                background: 'var(--bg-0)',
                color: 'var(--fg-dim)',
              }}
              data-testid="camera-fallback-message"
            >
              Поток загружается медленно или поставщик запрещает встраивание. Камеру можно открыть
              отдельно.
            </div>
          ) : null}
          <Button
            variant="primary"
            size="sm"
            icon={<ExternalLink size={12} />}
            onClick={() => window.open(cameraLink, '_blank', 'noopener,noreferrer')}
          >
            Открыть камеру
          </Button>
        </div>
      ) : null}
    </section>
  )
}

function AlarmRail({
  alarms,
  canCreate,
  onCreate,
}: {
  alarms: AlarmEvent[]
  canCreate: (alarm: AlarmEvent) => boolean
  onCreate: (alarm: AlarmEvent) => void
}) {
  if (alarms.length === 0) {
    return (
      <div
        className="flex flex-1 items-center justify-center px-6 text-center text-xs"
        style={{ color: 'var(--fg-faint)' }}
      >
        Открытых VNNOX-алармов нет
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-2 overflow-y-auto p-3">
      {alarms.map(alarm => {
        const isFaulty = alarm.type === 'faulty'
        const canCreateForAlarm = isFaulty && canCreate(alarm)

        return (
          <div
            key={alarm.id}
            className="space-y-2 rounded-md p-3"
            style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)' }}
          >
            <div className="flex items-center justify-between gap-2">
              <Badge label={isFaulty ? 'Open' : 'Recovery'} variant={isFaulty ? 'err' : 'ok'} />
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

            <p className="line-clamp-2 text-2xs" style={{ color: 'var(--fg-faint)' }}>
              {alarm.raw_position}
            </p>

            {canCreateForAlarm ? (
              <Button
                variant="primary"
                size="sm"
                icon={<Plus size={11} />}
                onClick={() => onCreate(alarm)}
                className="w-full justify-center"
              >
                Создать заявку
              </Button>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
