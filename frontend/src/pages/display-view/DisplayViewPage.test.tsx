import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DisplayViewPage } from './DisplayViewPage'

let mockPermission = 'monitoring'
let mockSelectedApp: any = null
let mockDeleteMutateAsync = vi.fn()

const mockDisplay = {
  id: 1,
  slug: 'test-display',
  name: 'display-1',
  description: 'Тестовый экран',
  rows: 2,
  cols: 2,
  camera_link: 'https://camera.example.test/embed',
  city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
  cells: [
    {
      id: 11,
      position: 'A1',
      row: 1,
      col: 1,
      panel: {
        id: 101,
        name: 'P-WORK',
        comment: '',
        condition: {
          id: 1,
          name: 'work',
          description: 'Работает',
          color: { id: 1, name: 'green', hex: '#00aa55' },
          icon: { id: 1, unicode_symbol: '+' },
        },
      },
    },
    {
      id: 12,
      position: 'A2',
      row: 1,
      col: 2,
      panel: {
        id: 102,
        name: 'P-ERROR',
        comment: 'fault',
        condition: {
          id: 2,
          name: 'error',
          description: 'Ошибка',
          color: { id: 2, name: 'yellow', hex: '#ffcc00' },
          icon: { id: 2, unicode_symbol: '!' },
        },
      },
    },
    {
      id: 13,
      position: 'B1',
      row: 2,
      col: 1,
      panel: null,
    },
  ],
}

vi.mock('@/features/auth/hooks', () => ({
  useMe: () => ({
    data: {
      permission: mockPermission,
    },
  }),
}))

vi.mock('@/entities/display/hooks', () => ({
  useDisplayDetail: () => ({
    data: mockDisplay,
    isLoading: false,
  }),
  useDisplayAlarms: () => ({
    data: [
      {
        id: 901,
        type: 'faulty',
        receiving_card_no: 4,
        raw_position: 'A2',
        raw_email_subject: 'fault',
        occurred_at: '2026-05-30T10:00:00Z',
        resolved_at: null,
        cell_id: 12,
        cell_position: 'A2',
        panel_id: 102,
        panel_name: 'P-ERROR',
      },
    ],
  }),
}))

vi.mock('@/entities/application/hooks', () => ({
  useApplicationDetail: () => ({
    data: mockSelectedApp,
  }),
  useApplicationEvents: () => ({
    data: [],
  }),
  useDeleteApplication: () => ({
    mutateAsync: mockDeleteMutateAsync,
  }),
}))

vi.mock('@/widgets/navigation/CrumbContext', () => ({
  useCrumb: () => ({ setCrumb: vi.fn() }),
}))

vi.mock('@/widgets/display-grid/DisplayGrid', () => ({
  DisplayGrid: ({ onCellSelect }: { onCellSelect: (cell: (typeof mockDisplay.cells)[number]) => void }) => (
    <div>
      {mockDisplay.cells.map(cell => (
        <button
          key={cell.id}
          data-testid={`grid-cell-${cell.id}`}
          onClick={() => onCellSelect(cell)}
        >
          {cell.position}
        </button>
      ))}
    </div>
  ),
}))

vi.mock('@/widgets/applications-panel/ApplicationsPanel', () => ({
  ApplicationsPanel: ({ onApplicationSelect }: { onApplicationSelect: (id: number) => void }) => (
    <button data-testid="select-application" onClick={() => onApplicationSelect(501)}>
      Выбрать заявку
    </button>
  ),
}))

vi.mock('@/entities/application/ApplicationDetailSheet', () => ({
  ApplicationDetailSheet: ({
    actions,
    canRemovePanel,
    onAction,
    onRemovePanel,
  }: {
    actions: Array<{ key: string; label: string }>
    canRemovePanel: boolean
    onAction: (key: string) => void
    onRemovePanel: () => void
  }) => (
    <div>
      {actions.map(action => (
        <button key={action.key} onClick={() => onAction(action.key)}>
          {action.label}
        </button>
      ))}
      {canRemovePanel ? <button onClick={onRemovePanel}>Снять панель</button> : null}
    </div>
  ),
}))

vi.mock('@/features/applications/CreateApplicationModal', () => ({
  CreateApplicationModal: ({ initialComment }: { initialComment: string }) => (
    <div data-testid="create-application-modal">{initialComment || 'create-open'}</div>
  ),
}))

vi.mock('@/features/applications/TransitionModal', () => ({
  TransitionModal: () => <div data-testid="transition-modal" />,
}))

vi.mock('@/features/panels/PanelActionModals', () => ({
  ChangeConditionModal: ({ allowedConditionNames }: { allowedConditionNames?: string[] }) => (
    <div data-testid="condition-modal">{allowedConditionNames?.join(',') ?? 'all'}</div>
  ),
  ChangeDepartmentModal: () => <div data-testid="department-modal" />,
  MoveToCellModal: () => <div data-testid="move-modal" />,
  PanelRemovalModal: () => <div data-testid="panel-removal-modal" />,
}))

// T-8-003/004/035: новые виджеты используют useQuery — мокаем их в этом тесте роль-матрицы.
vi.mock('@/widgets/display-notes/DisplayNotes', () => ({
  DisplayNotes: () => <div data-testid="display-notes" />,
}))
vi.mock('@/widgets/daily-tasks/DailyTasksPanel', () => ({
  DailyTasksPanel: () => <div data-testid="daily-tasks" />,
}))
vi.mock('@/widgets/cell-history/CellHistory', () => ({
  CellHistory: () => <div data-testid="cell-history" />,
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

function renderPage(department: 'monitoring' | 'control' | 'service') {
  return render(
    <MemoryRouter initialEntries={[`/${department}/ekb/test-display`]}>
      <Routes>
        <Route path="/:department/:citySlug/:displaySlug" element={<DisplayViewPage department={department} />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mockPermission = 'monitoring'
  mockSelectedApp = null
  mockDeleteMutateAsync = vi.fn().mockResolvedValue(undefined)
})

describe('DisplayViewPage role matrix', () => {
  it('monitoring does not see panel mutation actions on a healthy panel', () => {
    renderPage('monitoring')

    fireEvent.click(screen.getByTestId('grid-cell-11'))

    expect(screen.queryByRole('button', { name: 'Состояние' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Отдел' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Снять панель' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Поставить панель' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Создать заявку' })).not.toBeInTheDocument()
  })

  it('monitoring can create application for non-work panel without panel mutation actions', () => {
    renderPage('monitoring')

    fireEvent.click(screen.getByTestId('grid-cell-12'))

    expect(screen.getByRole('button', { name: 'Создать заявку' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Состояние' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Отдел' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Снять панель' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Поставить панель' })).not.toBeInTheDocument()
  })

  it('control does not see panel mutation or create actions', () => {
    mockPermission = 'control'
    renderPage('control')

    fireEvent.click(screen.getByTestId('grid-cell-12'))

    expect(screen.queryByRole('button', { name: 'Состояние' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Отдел' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Снять панель' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Создать заявку' })).not.toBeInTheDocument()
    expect(screen.queryByTestId('display-camera-card')).not.toBeInTheDocument()
  })

  it('renders resizable layout handles for desktop panes', () => {
    renderPage('monitoring')

    expect(screen.getByTestId('display-view-layout').className).toContain('display-view-resizable')
    expect(screen.getByTestId('display-view-grid-column').className).toContain('border-b')
    expect(screen.getByTestId('display-view-grid-column').className).toContain('lg:border-r')
    expect(screen.getByTestId('display-view-detail-column').className).toContain('w-full')
    expect(screen.getByTestId('display-view-rail-column').className).toContain('w-full')
    expect(screen.getByTestId('display-detail-resize-handle')).toBeInTheDocument()
    expect(screen.getByTestId('display-rail-resize-handle')).toBeInTheDocument()
    expect(screen.getByTestId('display-rail-main-resize-handle')).toBeInTheDocument()
  })

  it('renders camera, daily tasks, and notes inside the right rail', () => {
    renderPage('monitoring')

    const rail = screen.getByTestId('display-view-rail-column')
    const grid = screen.getByTestId('display-view-grid-column')

    expect(rail).toContainElement(screen.getByTestId('display-camera-card'))
    expect(rail).toContainElement(screen.getByTestId('daily-tasks'))
    expect(rail).toContainElement(screen.getByTestId('display-notes'))
    expect(grid).not.toContainElement(screen.getByTestId('daily-tasks'))
    expect(grid).not.toContainElement(screen.getByTestId('display-notes'))
  })

  it('service can install panel into empty cell', () => {
    mockPermission = 'service'
    renderPage('service')

    fireEvent.click(screen.getByTestId('grid-cell-13'))

    expect(screen.getByRole('button', { name: 'Поставить панель' })).toBeInTheDocument()
  })

  it('monitoring renders camera widget and falls back to external link after timeout', () => {
    vi.useFakeTimers()
    renderPage('monitoring')

    expect(screen.getByTestId('display-camera-card')).toBeInTheDocument()
    expect(screen.getByTitle('Камера экрана')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(screen.getByRole('button', { name: 'Открыть камеру' })).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('keeps embedded camera visible after a successful load event', () => {
    vi.useFakeTimers()
    renderPage('monitoring')

    const iframe = screen.getByTitle('Камера экрана')
    fireEvent.load(iframe)

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(screen.getByTitle('Камера экрана')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Открыть камеру' })).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('monitoring sees delete action for fresh application and confirms deletion', async () => {
    mockSelectedApp = {
      id: 501,
      status: {
        name: 'sent_to_control',
        description: 'Создана мониторингом',
        color: { hex: '#ffcc00' },
        color_text: { hex: '#111111' },
        icon: null,
        next_possible: [],
      },
      panel: {
        id: 102,
        name: 'P-ERROR',
      },
      cell: {
        id: 12,
        position: 'A2',
      },
      display: {
        id: 1,
        slug: 'test-display',
        description: 'Тестовый экран',
      },
      executor: null,
      initial_comment: 'fault',
      last_update_date_time: '2026-05-30T10:00:00Z',
    }

    renderPage('monitoring')

    fireEvent.click(screen.getByTestId('select-application'))

    expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Снять панель' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Принять' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Удалить' }))
    fireEvent.click(await screen.findByTestId('confirm-dialog-confirm'))

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith({ id: 501 })
    })
  })
})
