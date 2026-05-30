import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PanelCreateButton } from './PanelCreateButton'

const meMock = vi.fn()
const createMutation = { mutateAsync: vi.fn(), isPending: false }
const createPanelHook = vi.fn(() => createMutation)

vi.mock('@/features/auth/hooks', () => ({
  useMe: () => meMock(),
}))

vi.mock('@/entities/panel/hooks', () => ({
  useCreatePanel: () => createPanelHook(),
}))

vi.mock('@/entities/display/hooks', () => ({
  useDisplays: () => ({
    data: [
      { id: 1, slug: 'ekb', name: 'D1', description: 'Экран 1', city: { id: 1, name: 'Екб', slug: 'ekb' } },
      { id: 2, slug: 'msk', name: 'D2', description: 'Экран 2', city: { id: 2, name: 'Мск', slug: 'msk' } },
    ],
    isLoading: false,
  }),
}))

beforeEach(() => {
  createMutation.mutateAsync.mockReset()
  createMutation.mutateAsync.mockResolvedValue({})
  createMutation.isPending = false
  meMock.mockReturnValue({ data: { username: 'svc', permission: 'service' } })
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('PanelCreateButton (T-7-035)', () => {
  it('не рендерится для роли monitoring (нет прав)', () => {
    meMock.mockReturnValue({ data: { username: 'mon', permission: 'monitoring' } })
    const { container } = render(<PanelCreateButton />)
    expect(container).toBeEmptyDOMElement()
  })

  it('рендерит кнопку для роли admin', () => {
    meMock.mockReturnValue({ data: { username: 'a', permission: 'admin' } })
    render(<PanelCreateButton />)
    expect(screen.getByTestId('create-panel-button')).toBeInTheDocument()
  })

  it('открывает модалку и валидирует имя/экран', async () => {
    render(<PanelCreateButton />)
    fireEvent.click(screen.getByTestId('create-panel-button'))

    // модалка появилась
    expect(await screen.findByTestId('create-panel-submit')).toBeInTheDocument()

    // пустое имя → ошибка
    fireEvent.click(screen.getByTestId('create-panel-submit'))
    expect(await screen.findByTestId('create-panel-error')).toHaveTextContent(/имя/i)
    expect(createMutation.mutateAsync).not.toHaveBeenCalled()
  })

  it('uses readable contrast styles for modal form controls', async () => {
    render(<PanelCreateButton />)
    fireEvent.click(screen.getByTestId('create-panel-button'))

    const nameInput = await screen.findByTestId('create-panel-name')
    const displaySelect = screen.getByTestId('create-panel-display')
    const commentInput = screen.getByTestId('create-panel-comment')

    expect(nameInput).toHaveStyle('background: var(--bg-0)')
    expect(nameInput).toHaveStyle('color: var(--fg)')
    expect(displaySelect.getAttribute('style')).toContain('border: 1px solid var(--border-subtle)')
    expect(displaySelect).toHaveStyle('color: var(--fg)')
    expect(commentInput).toHaveStyle('background: var(--bg-0)')
    expect(commentInput.getAttribute('style')).toContain('border: 1px solid var(--border-subtle)')
  })

  it('подаёт запрос с display из select когда presetDisplayId не задан', async () => {
    render(<PanelCreateButton />)
    fireEvent.click(screen.getByTestId('create-panel-button'))

    const nameInput = await screen.findByTestId('create-panel-name')
    fireEvent.change(nameInput, { target: { value: 'P-099' } })

    const select = screen.getByTestId('create-panel-display') as HTMLSelectElement
    fireEvent.change(select, { target: { value: '2' } })

    fireEvent.click(screen.getByTestId('create-panel-submit'))

    await waitFor(() => {
      expect(createMutation.mutateAsync).toHaveBeenCalledWith({
        name: 'P-099',
        display_id: 2,
        comment: undefined,
      })
    })
  })

  it('скрывает select когда presetDisplayId задан, и подаёт его в запрос', async () => {
    render(<PanelCreateButton presetDisplayId={42} />)
    fireEvent.click(screen.getByTestId('create-panel-button'))

    expect(screen.queryByTestId('create-panel-display')).not.toBeInTheDocument()

    fireEvent.change(await screen.findByTestId('create-panel-name'), { target: { value: 'P-100' } })
    fireEvent.click(screen.getByTestId('create-panel-submit'))

    await waitFor(() => {
      expect(createMutation.mutateAsync).toHaveBeenCalledWith({
        name: 'P-100',
        display_id: 42,
        comment: undefined,
      })
    })
  })
})
