import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import type { Panel } from '@/shared/api/types'
import { ZipPage } from './ZipPage'

type UsePanelsFilter = { department?: string; display?: string | null; fetchAll?: boolean }
type UsePanelsResult = { data: Panel[]; isLoading: boolean }

const usePanelsMock = vi.fn<(filter?: UsePanelsFilter) => UsePanelsResult>(
  () => ({ data: [], isLoading: false }),
)
const changeDeptMutation = { mutateAsync: vi.fn(), isPending: false }

vi.mock('@/entities/panel/hooks', () => ({
  usePanels: (filter?: UsePanelsFilter) => usePanelsMock(filter),
  useCreatePanel: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeletePanel: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useChangeDepartment: vi.fn(() => changeDeptMutation),
}))

vi.mock('@/entities/storage/hooks', () => ({
  useStorage: vi.fn((kind: string) => {
    if (kind === 'wires') {
      return {
        data: [
          {
            id: 1,
            name: 'wire-low',
            count: 1,
            low_stock_threshold: 3,
            is_low_stock: true,
            description: '',
            photo: null,
          },
        ],
        isLoading: false,
      }
    }
    return { data: [], isLoading: false }
  }),
}))

vi.mock('@/entities/activity/hooks', () => ({
  useInfiniteActivityLog: vi.fn(() => ({
    entries: [],
    isLoading: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
  })),
}))

vi.mock('@/entities/display/hooks', () => ({
  useDisplays: vi.fn(() => ({
    data: [
      {
        id: 1,
        slug: 'ekb',
        name: 'display-1',
        description: 'Display 1',
        city: { id: 1, name: 'Ekaterinburg', slug: 'ekb' },
      },
    ],
  })),
}))

vi.mock('@/features/auth/hooks', () => ({
  useMe: vi.fn(() => ({ data: { username: 'guest', permission: 'monitoring' } })),
}))

function renderZipPage(initialEntry = '/zip/ekb') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/zip" element={<ZipPage />} />
        <Route path="/zip/:displaySlug" element={<ZipPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  usePanelsMock.mockReset()
  usePanelsMock.mockReturnValue({ data: [], isLoading: false })
  changeDeptMutation.mutateAsync.mockReset()
})

describe('ZipPage', () => {
  it('highlights low-stock storage items', () => {
    renderZipPage()

    const item = screen.getByTestId('storage-item-wire-low')
    expect(item).toHaveClass('storage-item-card--low')
    expect(screen.getByText(/3/)).toBeInTheDocument()
  })

  it('renders display filter with readable contrast styles', () => {
    renderZipPage()

    const select = screen.getByTestId('zip-display-filter')
    expect(select).toHaveStyle('background: var(--bg-1)')
    expect(select).toHaveStyle('color: var(--fg)')
    expect(select.getAttribute('style')).toContain('border: 1px solid var(--border-subtle)')
  })

  it('requests full panel lists when a concrete display is selected', () => {
    renderZipPage()

    expect(usePanelsMock).toHaveBeenCalledWith(
      expect.objectContaining({ department: 'zip', display: '1', fetchAll: true }),
    )
    expect(usePanelsMock).toHaveBeenCalledWith(
      expect.objectContaining({ department: 'monitor', display: '1', fetchAll: true }),
    )
  })

  it('requests full panel lists when all displays are selected', () => {
    renderZipPage('/zip')

    expect(usePanelsMock).toHaveBeenCalledWith(
      expect.objectContaining({ department: 'zip', display: null, fetchAll: true }),
    )
    expect(usePanelsMock).toHaveBeenCalledWith(
      expect.objectContaining({ department: 'monitor', display: null, fetchAll: true }),
    )
  })
})

describe('ZipPage DnD (T-7-033)', () => {
  const zipPanel: Panel = {
    id: 99,
    name: 'P-099',
    display_id: 1,
    cell_id: 0,
    application_status_name: 'default',
    active_application_id: 0,
    department_name: 'zip',
    comment: null,
    condition: {
      id: 1,
      name: 'work',
      description: 'Working',
      color: { id: 1, name: 'green', hex: '#00aa00' },
      icon: { id: 1, unicode_symbol: '+' },
    },
  }

  it('panel chip is draggable and dropping into service changes department', async () => {
    usePanelsMock.mockImplementation((filter?: { department?: string }) => {
      if (filter?.department === 'zip') {
        return { data: [zipPanel], isLoading: false }
      }
      return { data: [], isLoading: false }
    })
    changeDeptMutation.mutateAsync.mockResolvedValue({})

    renderZipPage()

    const chip = screen.getByTestId('panel-chip-99')
    expect(chip.getAttribute('draggable')).toBe('true')

    const data = new Map<string, string>()
    const dataTransfer = {
      data,
      types: [] as string[],
      effectAllowed: '',
      dropEffect: '',
      setData(type: string, value: string) {
        data.set(type, value)
        if (!this.types.includes(type)) {
          this.types.push(type)
        }
      },
      getData(type: string) {
        return data.get(type) ?? ''
      },
    }

    fireEvent.dragStart(chip, { dataTransfer })
    expect(data.get('application/x-panel-id')).toBe('99')

    const serviceColumn = screen.getByTestId('panel-column-service')
    fireEvent.dragOver(serviceColumn, { dataTransfer })
    fireEvent.drop(serviceColumn, { dataTransfer })

    await waitFor(() => {
      expect(changeDeptMutation.mutateAsync).toHaveBeenCalledWith({
        id: 99,
        department: 'service',
      })
    })
  })

  it('drop on monitor does not change department', () => {
    usePanelsMock.mockImplementation((filter?: { department?: string }) => {
      if (filter?.department === 'zip') {
        return { data: [zipPanel], isLoading: false }
      }
      return { data: [], isLoading: false }
    })

    renderZipPage()

    const monitorColumn = screen.getByTestId('panel-column-monitor')
    const data = new Map<string, string>([['application/x-panel-id', '99']])
    const dataTransfer = {
      data,
      types: ['application/x-panel-id'],
      effectAllowed: 'move',
      dropEffect: '',
      setData(type: string, value: string) {
        data.set(type, value)
      },
      getData(type: string) {
        return data.get(type) ?? ''
      },
    }

    fireEvent.drop(monitorColumn, { dataTransfer })

    expect(changeDeptMutation.mutateAsync).not.toHaveBeenCalled()
  })
})
