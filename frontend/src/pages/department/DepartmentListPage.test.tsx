import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DepartmentListPage } from './DepartmentListPage'

const mockDisplays = [
  {
    id: 1,
    slug: 'ekb-1',
    name: 'display-1',
    description: 'Альфа',
    rows: 4,
    cols: 4,
    city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
  },
  {
    id: 2,
    slug: 'ekb-2',
    name: 'display-2',
    description: 'Бета',
    rows: 10,
    cols: 10,
    city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
  },
  {
    id: 3,
    slug: 'msk-1',
    name: 'display-3',
    description: 'Альфа',
    rows: 6,
    cols: 6,
    city: { id: 2, name: 'Москва', slug: 'msk' },
  },
  {
    id: 4,
    slug: 'kzn-1',
    name: 'display-4',
    description: 'Гамма',
    rows: 8,
    cols: 8,
    city: { id: 3, name: 'Казань', slug: 'kzn' },
  },
]

const mockCities = [
  { id: 1, name: 'Екатеринбург', slug: 'ekb' },
  { id: 2, name: 'Москва', slug: 'msk' },
  { id: 3, name: 'Казань', slug: 'kzn' },
]

vi.mock('@/entities/display/hooks', () => ({
  useDisplays: vi.fn(() => ({ data: mockDisplays, isLoading: false, error: null, refetch: vi.fn() })),
  useCities: vi.fn(() => ({ data: mockCities, isLoading: false, error: null })),
}))

vi.mock('@/entities/application/hooks', () => ({
  useApplications: vi.fn(() => ({
    data: { results: [] },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

vi.mock('@/widgets/navigation/CrumbContext', () => ({
  useCrumb: () => ({ setCrumb: vi.fn() }),
}))

vi.mock('@/entities/application/ApplicationCard', () => ({
  ApplicationCard: ({ application }: { application: { id: number } }) => (
    <div data-testid={`application-card-${application.id}`}>app</div>
  ),
}))

function renderPage(initialPath = '/monitoring') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/monitoring" element={<DepartmentListPage department="monitoring" />} />
        <Route path="/monitoring/:citySlug" element={<DepartmentListPage department="monitoring" />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  sessionStorage.clear()
})

afterEach(() => {
  sessionStorage.clear()
})

describe('DepartmentListPage - merged sort/filter/quick-links', () => {
  it('renders 3 city groups with default name-asc sort inside each', () => {
    renderPage()

    expect(screen.getByText('Екатеринбург')).toBeInTheDocument()
    expect(screen.getByText('Москва')).toBeInTheDocument()
    expect(screen.getByText('Казань')).toBeInTheDocument()

    const ekbCards = [
      screen.getByTestId('display-card-ekb-1'),
      screen.getByTestId('display-card-ekb-2'),
    ]

    expect(within(ekbCards[0]).getByText('Альфа')).toBeInTheDocument()
    expect(within(ekbCards[1]).getByText('Бета')).toBeInTheDocument()
  })

  it('shows city filter when there are at least 3 cities and filters groups by substring', () => {
    renderPage()

    const filter = screen.getByTestId('city-filter').querySelector('input') as HTMLInputElement
    expect(filter).toBeInTheDocument()

    fireEvent.change(filter, { target: { value: 'каз' } })

    expect(screen.getByText('Казань')).toBeInTheDocument()
    expect(screen.queryByText('Москва')).not.toBeInTheDocument()
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
    expect(within(ekbCards[1]).getByText('Альфа')).toBeInTheDocument()
  })

  it('renders quick-links for each card', () => {
    renderPage()

    expect(screen.getByTestId('quicklink-zip-ekb-1')).toHaveAttribute('href', '/zip/ekb-1')
    expect(screen.getByTestId('quicklink-applications-ekb-1')).toHaveAttribute('href', '/control/ekb/ekb-1')
    expect(screen.getByTestId('quicklink-history-ekb-1')).toHaveAttribute(
      'href',
      '/monitoring/ekb/ekb-1?tab=history',
    )
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
    expect(screen.queryByText('Москва')).not.toBeInTheDocument()
    expect(screen.queryByText('Казань')).not.toBeInTheDocument()
  })
})
