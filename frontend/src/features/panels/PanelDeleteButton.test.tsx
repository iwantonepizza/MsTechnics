import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PanelDeleteButton } from './PanelDeleteButton'

const meMock = vi.fn()
const deleteMutation = { mutateAsync: vi.fn(), isPending: false }
const deletePanelHook = vi.fn(() => deleteMutation)

vi.mock('@/features/auth/hooks', () => ({
  useMe: () => meMock(),
}))

vi.mock('@/entities/panel/hooks', () => ({
  useDeletePanel: () => deletePanelHook(),
}))

const mockPanel = {
  id: 7,
  name: 'P-007',
  comment: null,
  condition: null,
  department_name: 'zip',
  display_id: 1,
  cell_id: null,
  application_status_name: 'default',
  active_application_id: null,
}

beforeEach(() => {
  deleteMutation.mutateAsync.mockReset()
  deleteMutation.mutateAsync.mockResolvedValue(7)
  deleteMutation.isPending = false
  meMock.mockReturnValue({ data: { username: 'a', permission: 'admin', roles: ['admin'] } })
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('PanelDeleteButton (T-7-036)', () => {
  it('не рендерится для не-админа', () => {
    meMock.mockReturnValue({ data: { username: 's', permission: 'service', roles: ['service'] } })
    const { container } = render(<PanelDeleteButton panel={mockPanel as any} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('не рендерится для legacy-роли all', () => {
    meMock.mockReturnValue({
      data: { username: 'all', permission: 'all', roles: ['monitoring', 'control', 'service'] },
    })
    const { container } = render(<PanelDeleteButton panel={mockPanel as any} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('рендерится для multi-role admin', () => {
    meMock.mockReturnValue({ data: { username: 'a', permission: 'service', roles: ['service', 'admin'] } })
    render(<PanelDeleteButton panel={mockPanel as any} />)
    expect(screen.getByTestId('delete-panel-button')).toBeInTheDocument()
  })

  it('рендерит кнопку «Удалить» для admin', () => {
    render(<PanelDeleteButton panel={mockPanel as any} />)
    expect(screen.getByTestId('delete-panel-button')).toBeInTheDocument()
  })

  it('открывает ConfirmDialog с именем панели в title', async () => {
    render(<PanelDeleteButton panel={mockPanel as any} />)
    fireEvent.click(screen.getByTestId('delete-panel-button'))

    expect(await screen.findByText(/Удалить панель P-007\?/)).toBeInTheDocument()
  })

  it('confirm → mutateAsync(panel.id) + onDeleted callback', async () => {
    const onDeleted = vi.fn()
    render(<PanelDeleteButton panel={mockPanel as any} onDeleted={onDeleted} />)
    fireEvent.click(screen.getByTestId('delete-panel-button'))

    const confirmBtn = await screen.findByTestId('confirm-dialog-confirm')
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(deleteMutation.mutateAsync).toHaveBeenCalledWith(7)
      expect(onDeleted).toHaveBeenCalledTimes(1)
    })
  })

  it('показывает backend-ошибку (panel_has_active_application) в диалоге', async () => {
    deleteMutation.mutateAsync.mockRejectedValueOnce({
      response: { data: { detail: 'У панели P-007 есть активная заявка #5. Сначала закройте заявку.' } },
    })

    render(<PanelDeleteButton panel={mockPanel as any} />)
    fireEvent.click(screen.getByTestId('delete-panel-button'))

    const confirmBtn = await screen.findByTestId('confirm-dialog-confirm')
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(screen.getByText(/активная заявка #5/)).toBeInTheDocument()
    })
  })
})
