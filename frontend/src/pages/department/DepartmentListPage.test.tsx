import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DepartmentListPage } from './DepartmentListPage'

const mockDisplays = [
  {
    id: 1,
    slug: 'ekb-1',
    name: 'display-1',
    description: 'РђР»СЊС„Р°',
    rows: 4,
    cols: 4,
    aggregated_condition: {
      id: 10,
      name: 'error',
      description: 'Ошибка',
      color: { id: 100, name: 'yellow', hex: '#ffcc00' },
      icon: { id: 1, unicode_symbol: '!' },
    },
    city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
    application_count: 2,
  },
  {
    id: 2,
    slug: 'ekb-2',
    name: 'display-2',
    description: 'Бета',
    rows: 10,
    cols: 10,
    aggregated_condition: {
      id: 11,
      name: 'work',
      description: 'Работает',
      color: { id: 101, name: 'green', hex: '#00aa55' },
      icon: { id: 2, unicode_symbol: '+' },
    },
    city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
    application_count: 0,
  },
  {
    id: 3,
    slug: 'msk-1',
    name: 'display-3',
    description: 'РђР»СЊС„Р°',
    rows: 6,
    cols: 6,
    aggregated_condition: null,
    city: { id: 2, name: 'РњРѕСЃРєРІР°', slug: 'msk' },
    application_count: 0,
  },
  {
    id: 4,
    slug: 'kzn-1',
    name: 'display-4',
    description: 'Гамма',
    rows: 8,
    cols: 8,
    aggregated_condition: {
      id: 12,
      name: 'unrecoverable',
      description: 'Неремонтопригодна',
      color: { id: 102, name: 'red', hex: '#dd3344' },
      icon: { id: 3, unicode_symbol: 'x' },
    },
    city: { id: 3, name: 'Казань', slug: 'kzn' },
    application_count: 0,
  },
]

const mockCities = [
  { id: 1, name: 'Екатеринбург', slug: 'ekb' },
  { id: 2, name: 'РњРѕСЃРєРІР°', slug: 'msk' },
  { id: 3, name: 'Казань', slug: 'kzn' },
]

const mockDisplayDetail = {
  id: 1,
  slug: 'ekb-1',
  name: 'display-1',
  description: 'РђР»СЊС„Р°',
  rows: 4,
  cols: 4,
  city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
  file_url: '/media/schematics/ekb-1.pdf',
  project_photo_url: '/media/projects/ekb-1.jpg',
  contacts: [
    {
      id: 7,
      full_name: 'Иван Петров',
      description: 'Электрик',
      phone: '+79001234567',
      telegram_id: null,
    },
  ],
  photos: [
    {
      id: 77,
      url: '/media/photos/ekb-1.jpg',
      uploaded_at: '2026-05-30T10:00:00Z',
    },
  ],
  cells: [],
}

const mockApiPost = vi.fn()
const mockApiDelete = vi.fn()
const mockRefetchDetail = vi.fn()
const mockRefetchCities = vi.fn()
const mockRefetchDisplays = vi.fn()
const mockUseActivityLog = vi.fn()
let mockShowActivityFeed = true
let mockCitiesError: Error | null = null
let mockDisplaysError: Error | null = null
const mockActivityEntries = [
  {
    id: 501,
    description: 'Panel moved',
    actor_name: 'dispatcher',
    occurred_at: '2026-05-30T10:00:00Z',
  },
]

vi.mock('@/entities/display/hooks', () => ({
  useDisplays: vi.fn(() => ({
    data: mockDisplays,
    isLoading: false,
    error: mockDisplaysError,
    refetch: mockRefetchDisplays,
  })),
  useCities: vi.fn(() => ({
    data: mockCities,
    isLoading: false,
    error: mockCitiesError,
    refetch: mockRefetchCities,
  })),
  useDisplayDetail: vi.fn((slug: string | null) => ({
    data: slug ? mockDisplayDetail : undefined,
    isLoading: false,
    refetch: mockRefetchDetail,
  })),
}))

vi.mock('@/entities/application/hooks', () => ({
  useApplications: vi.fn(() => ({
    data: { results: [] },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

vi.mock('@/entities/activity/hooks', () => ({
  useInfiniteActivityLog: (filter: unknown) => mockUseActivityLog(filter),
}))

mockUseActivityLog.mockImplementation(() => ({
  entries: mockActivityEntries,
  isLoading: false,
  isError: false,
  refetch: vi.fn(),
  hasNextPage: false,
  isFetchingNextPage: false,
  fetchNextPage: vi.fn(),
}))

vi.mock('@/features/auth/hooks', () => ({
  useMe: vi.fn(() => ({
    data: {
      permission: 'monitoring',
      show_activity_feed: mockShowActivityFeed,
    },
  })),
}))

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockApiPost(...args),
    delete: (...args: unknown[]) => mockApiDelete(...args),
  },
}))

vi.mock('@/widgets/navigation/CrumbContext', () => ({
  useCrumb: () => ({ setCrumb: vi.fn() }),
}))

vi.mock('@/entities/application/ApplicationCard', () => ({
  ApplicationCard: ({ application }: { application: { id: number } }) => (
    <div data-testid={`application-card-${application.id}`}>app</div>
  ),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
  },
}))

function renderPage(
  initialPath = '/monitoring',
  department: 'monitoring' | 'control' | 'service' = 'monitoring',
) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/monitoring" element={<DepartmentListPage department={department} />} />
        <Route path="/monitoring/:citySlug" element={<DepartmentListPage department={department} />} />
        <Route path="/service" element={<DepartmentListPage department={department} />} />
        <Route path="/service/:citySlug" element={<DepartmentListPage department={department} />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  sessionStorage.clear()
  mockShowActivityFeed = true
  mockCitiesError = null
  mockDisplaysError = null
  mockApiPost.mockReset()
  mockApiDelete.mockReset()
  mockRefetchCities.mockReset()
  mockRefetchDisplays.mockReset()
  mockUseActivityLog.mockClear()
  mockRefetchDetail.mockReset()
  mockRefetchDetail.mockResolvedValue(undefined)
  mockApiPost.mockResolvedValue({ data: { id: 99, url: '/media/photos/new.jpg', uploaded_at: null } })
  mockApiDelete.mockResolvedValue({ data: null })

  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined),
    },
  })
})

afterEach(() => {
  sessionStorage.clear()
  vi.clearAllMocks()
})

describe('DepartmentListPage - merged sort/filter/quick-links', () => {
  it('renders 3 city groups with default name-asc sort inside each', () => {
    renderPage()

    expect(screen.getByText('Екатеринбург')).toBeInTheDocument()
    expect(screen.getByText('РњРѕСЃРєРІР°')).toBeInTheDocument()
    expect(screen.getByText('Казань')).toBeInTheDocument()

    const ekbCards = [
      screen.getByTestId('display-card-ekb-1'),
      screen.getByTestId('display-card-ekb-2'),
    ]

    expect(within(ekbCards[0]).getByText('РђР»СЊС„Р°')).toBeInTheDocument()
    expect(within(ekbCards[1]).getByText('Бета')).toBeInTheDocument()
  })

  it('shows city filter when there are at least 3 cities and filters groups by substring', () => {
    renderPage()

    const filter = screen.getByTestId('city-filter').querySelector('input') as HTMLInputElement
    expect(filter).toBeInTheDocument()

    fireEvent.change(filter, { target: { value: 'Каз' } })

    expect(screen.getByText('Казань')).toBeInTheDocument()
    expect(screen.queryByText('РњРѕСЃРєРІР°')).not.toBeInTheDocument()
    expect(screen.queryByText('Екатеринбург')).not.toBeInTheDocument()
  })

  it('shows empty-state when city filter has no matches', () => {
    renderPage()

    const filter = screen.getByTestId('city-filter').querySelector('input') as HTMLInputElement
    fireEvent.change(filter, { target: { value: 'неттакого' } })

    expect(screen.getByText('Городов не найдено')).toBeInTheDocument()
  })

  it('size-desc sort puts larger displays first inside city', () => {
    renderPage()

    const select = screen.getByTestId('sort-select').querySelector('select') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'size-desc' } })

    const ekbCards = screen.getAllByTestId(/^display-card-ekb-/)
    expect(within(ekbCards[0]).getByText('Бета')).toBeInTheDocument()
    expect(within(ekbCards[1]).getByText('РђР»СЊС„Р°')).toBeInTheDocument()
  })

  it('renders zip quick-link and application count without broken history/application links', () => {
    renderPage()

    expect(screen.getByTestId('quicklink-zip-ekb-1')).toHaveAttribute('href', '/zip/ekb-1')
    expect(screen.getByTestId('quicklink-zip-ekb-1')).toHaveTextContent('ЗИП')
    expect(screen.getByTestId('display-application-count-ekb-1')).toHaveTextContent('Заявки: 2')
    expect(screen.queryByTestId('quicklink-applications-ekb-1')).not.toBeInTheDocument()
    expect(screen.queryByTestId('quicklink-history-ekb-1')).not.toBeInTheDocument()
  })

  it('shows the activity feed in the side rail when enabled for the user', () => {
    renderPage()

    expect(screen.getByTestId('department-list-layout').className).toContain('department-list-layout')
    expect(screen.getByTestId('department-rail-resize-handle')).toBeInTheDocument()
    expect(screen.getByTestId('department-activity-resize-handle')).toBeInTheDocument()
    expect(screen.getByTestId('department-activity-feed')).toBeInTheDocument()
    expect(screen.getByText('Panel moved')).toBeInTheDocument()
  })

  it('loads activity feed for all time without since filter', () => {
    renderPage()

    const select = screen.getByTestId('sort-select').querySelector('select') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'name-desc' } })

    const lastCall = mockUseActivityLog.mock.calls[mockUseActivityLog.mock.calls.length - 1]
    expect(lastCall?.[0]).toEqual(expect.objectContaining({ feed: true, limit: 60 }))
    expect(lastCall?.[0]).not.toHaveProperty('since')
    expect(screen.getByText('Всё время')).toBeInTheDocument()
  })

  it('retries both city and display queries after a list load error', () => {
    mockCitiesError = new Error('rate limited')
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: 'Повторить' }))

    expect(mockRefetchCities).toHaveBeenCalledTimes(1)
    expect(mockRefetchDisplays).toHaveBeenCalledTimes(1)
  })

  it('persists sort choice via sessionStorage across remounts', () => {
    const { unmount } = renderPage()
    const select = screen.getByTestId('sort-select').querySelector('select') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'name-desc' } })
    unmount()

    renderPage()
    const remountedSelect = screen.getByTestId('sort-select').querySelector('select') as HTMLSelectElement
    expect(remountedSelect.value).toBe('name-desc')
  })

  it('filters displays by route citySlug', () => {
    renderPage('/monitoring/ekb')

    expect(screen.getByText('Екатеринбург')).toBeInTheDocument()
    expect(screen.queryByText('РњРѕСЃРєРІР°')).not.toBeInTheDocument()
    expect(screen.queryByText('Казань')).not.toBeInTheDocument()
  })

  it('renders 4 action buttons for each display', () => {
    renderPage()

    expect(screen.getByTestId('display-action-schematic-ekb-1')).toBeInTheDocument()
    expect(screen.getByTestId('display-action-project-ekb-1')).toBeInTheDocument()
    expect(screen.getByTestId('display-action-contacts-ekb-1')).toBeInTheDocument()
    expect(screen.getByTestId('display-action-photos-ekb-1')).toBeInTheDocument()
  })

  it('renders aggregated condition indicator with accessible label', () => {
    renderPage()

    expect(screen.getByTestId('display-condition-ekb-1-error')).toHaveAttribute('aria-label', 'Ошибка')
    expect(screen.getByTestId('display-condition-msk-1-empty')).toHaveAttribute(
      'aria-label',
      'Состояние не определено',
    )
  })

  it('opens contacts modal with contact list and phone link', async () => {
    renderPage()

    fireEvent.click(screen.getByTestId('display-action-contacts-ekb-1'))

    expect(await screen.findByText(/Контакты/)).toBeInTheDocument()
    expect(screen.getByText('Иван Петров')).toBeInTheDocument()
    expect(screen.getByText('Электрик')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Позвонить' })).toHaveAttribute(
      'href',
      'tel:+79001234567',
    )
  })

  it('opens schematic modal with downloadable asset link', async () => {
    renderPage()

    fireEvent.click(screen.getByTestId('display-action-schematic-ekb-1'))

    expect(await screen.findByText(/Электросхема/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Скачать' })).toHaveAttribute(
      'href',
      '/media/schematics/ekb-1.pdf',
    )
  })

  it('service photo modal uploads and deletes photos through task routes', async () => {
    renderPage('/service', 'service')

    fireEvent.click(screen.getByTestId('display-action-photos-ekb-1'))

    const input = await screen.findByTestId('photo-upload-input')
    const file = new File(['gif-content'], 'screen.gif', { type: 'image/gif' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        '/displays/ekb-1/photos/',
        expect.any(FormData),
      )
    })

    fireEvent.click(screen.getByTestId('photo-delete-77'))
    fireEvent.click(await screen.findByTestId('confirm-dialog-confirm'))

    await waitFor(() => {
      expect(mockApiDelete).toHaveBeenCalledWith('/displays/ekb-1/photos/77/')
      expect(mockRefetchDetail).toHaveBeenCalled()
    })
  })
})
