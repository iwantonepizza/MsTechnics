import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import type { Panel } from '@/shared/api/types'
import { ZipPage } from './ZipPage'

type UsePanelsFilter = { department?: string; display?: string | null; fetchAll?: boolean }
type UsePanelsResult = { data: Panel[]; isLoading: boolean }

const usePanelsMock = vi.fn<(filter?: UsePanelsFilter) => UsePanelsResult>(
  () => ({ data: [], isLoading: false }),
)
const changeDeptMutation = { mutateAsync: vi.fn(), isPending: false }

vi.mock('@/entities/panel/hooks', () => ({
  usePanels: (filter?: { department?: string; display?: string | null }) => usePanelsMock(filter),
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
  useActivityLog: vi.fn(() => ({ data: [], isLoading: false })),
}))

vi.mock('@/entities/display/hooks', () => ({
  useDisplays: vi.fn(() => ({
    data: [
      {
        id: 1,
        slug: 'ekb',
        name: 'display-1',
        description: 'Экран 1',
        city: { id: 1, name: 'Екатеринбург', slug: 'ekb' },
      },
    ],
  })),
}))

vi.mock('@/features/auth/hooks', () => ({
  useMe: vi.fn(() => ({ data: { username: 'guest', permission: 'monitoring' } })),
}))

function renderZipPage() {
  return render(
    <MemoryRouter initialEntries={['/zip/ekb']}>
      <Routes>
        <Route path="/zip/:displaySlug" element={<ZipPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ZipPage', () => {
  it('highlights low-stock storage items', () => {
    usePanelsMock.mockReturnValue({ data: [], isLoading: false })
    renderZipPage()

    const item = screen.getByTestId('storage-item-wire-low')
    expect(item).toHaveClass('storage-item-card--low')
    expect(screen.getByText('Меньше 3')).toBeInTheDocument()
  })
})

describe('ZipPage', () => {
  it('renders display filter with readable contrast styles', () => {
    usePanelsMock.mockReturnValue({ data: [], isLoading: false })
    renderZipPage()

    const select = screen.getByTestId('zip-display-filter')
    expect(select).toHaveStyle('background: var(--bg-1)')
    expect(select).toHaveStyle('color: var(--fg)')
    expect(select.getAttribute('style')).toContain('border: 1px solid var(--border-subtle)')
  })

  it('requests full panel lists when a concrete display is selected', () => {
    usePanelsMock.mockReturnValue({ data: [], isLoading: false })
    renderZipPage()

    expect(usePanelsMock).toHaveBeenCalledWith(
      expect.objectContaining({ department: 'zip', display: '1', fetchAll: true }),
    )
    expect(usePanelsMock).toHaveBeenCalledWith(
      expect.objectContaining({ department: 'monitor', display: '1', fetchAll: true }),
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
      description: 'Рабочая',
      color: { id: 1, name: 'green', hex: '#00aa00' },
      icon: { id: 1, unicode_symbol: '🟢' },
    },
  }

  it('panel chip — draggable, drop в service вызывает changeDept', async () => {
    usePanelsMock.mockImplementation((filter?: { department?: string }) => {
      if (filter?.department === 'zip') return { data: [zipPanel], isLoading: false }
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
        if (!this.types.includes(type)) this.types.push(type)
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

  it('drop на monitor не вызывает changeDept (не drop target)', async () => {
    usePanelsMock.mockImplementation((filter?: { department?: string }) => {
      if (filter?.department === 'zip') return { data: [zipPanel], isLoading: false }
      return { data: [], isLoading: false }
    })
    changeDeptMutation.mutateAsync.mockReset()

    renderZipPage()

    const monitorColumn = screen.getByTestId('panel-column-monitor')
    const data = new Map<string, string>([['application/x-panel-id', '99']])
    const dataTransfer = {
      data,
      types: ['application/x-panel-id'],
      effectAllowed: 'move',
      dropEffect: '',
      setData(type: string, value: string) { data.set(type, value) },
      getData(type: string) { return data.get(type) ?? '' },
    }

    fireEvent.drop(monitorColumn, { dataTransfer })

    expect(changeDeptMutation.mutateAsync).not.toHaveBeenCalled()
  })
})
