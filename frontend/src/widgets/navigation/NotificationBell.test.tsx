import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { NotificationBell } from './NotificationBell'

const mockApiGet = vi.fn()
vi.mock('@/shared/api/client', () => ({
  apiClient: { get: (...args: unknown[]) => mockApiGet(...args) },
}))

function renderBell() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const NOW = '2026-05-19T12:00:00Z'

beforeEach(() => {
  mockApiGet.mockReset()
  localStorage.clear()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('NotificationBell (T-7-011)', () => {
  it('renders bell button and hides badge when unread=0', async () => {
    mockApiGet.mockResolvedValue({ data: { results: [], count: 0 } })
    renderBell()

    await waitFor(() => {
      expect(screen.getByTestId('notification-bell-button')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('notification-bell-badge')).not.toBeInTheDocument()
  })

  it('shows unread badge when inbox has unseen items', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        count: 2,
        results: [
          { id: 10, rendered_text: 'Новая заявка #5', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: 'application', target_id: '5', deep_link_path: null },
          { id: 11, rendered_text: 'Назначен исполнитель', created_at: NOW, status: 'sent', delivered_via: 'max', target_kind: 'application', target_id: '5', deep_link_path: null },
        ],
      },
    })
    renderBell()

    await waitFor(() => {
      expect(screen.getByTestId('notification-bell-badge')).toHaveTextContent('2')
    })
  })

  it('opening popover marks all seen and writes to localStorage', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        count: 1,
        results: [
          { id: 42, rendered_text: 'Hello', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: null, target_id: null, deep_link_path: null },
        ],
      },
    })
    renderBell()

    await waitFor(() => expect(screen.getByTestId('notification-bell-badge')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('notification-bell-button'))

    expect(await screen.findByTestId('notification-bell-popover')).toBeInTheDocument()
    expect(screen.queryByTestId('notification-bell-badge')).not.toBeInTheDocument()
    expect(localStorage.getItem('notifications.lastSeenId')).toBe('42')
  })

  it('shows empty state when results are empty', async () => {
    mockApiGet.mockResolvedValue({ data: { results: [], count: 0 } })
    renderBell()

    await waitFor(() => expect(screen.getByTestId('notification-bell-button')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('notification-bell-button'))

    expect(await screen.findByText(/пока пусто/i)).toBeInTheDocument()
  })

  it('prefers backend deep_link_path when it is present', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        count: 1,
        results: [
          { id: 1, rendered_text: 'X', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: 'application', target_id: '7', deep_link_path: '/service/kazan/kzn-1?app_id=7' },
        ],
      },
    })
    renderBell()

    await waitFor(() => expect(screen.getByTestId('notification-bell-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('notification-bell-button'))

    const row = await screen.findByTestId('notification-row-1')
    expect(row.getAttribute('href')).toBe('/service/kazan/kzn-1?app_id=7')
  })

  it('deep-link falls back to legacy route when deep_link_path is null', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        count: 1,
        results: [
          { id: 1, rendered_text: 'X', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: 'application', target_id: '7', deep_link_path: null },
        ],
      },
    })
    renderBell()

    await waitFor(() => expect(screen.getByTestId('notification-bell-button')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('notification-bell-button'))

    const row = await screen.findByTestId('notification-row-1')
    expect(row.getAttribute('href')).toBe('/control?app_id=7')
  })

  it('badge stays hidden after mark-as-seen with new baseline in localStorage', async () => {
    mockApiGet.mockResolvedValueOnce({
      data: {
        count: 1,
        results: [
          { id: 1, rendered_text: 'A', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: null, target_id: null, deep_link_path: null },
        ],
      },
    })
    mockApiGet.mockResolvedValueOnce({
      data: {
        count: 2,
        results: [
          { id: 2, rendered_text: 'B', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: null, target_id: null, deep_link_path: null },
          { id: 1, rendered_text: 'A', created_at: NOW, status: 'sent', delivered_via: 'tg', target_kind: null, target_id: null, deep_link_path: null },
        ],
      },
    })

    localStorage.setItem('notifications.lastSeenId', '1')
    renderBell()

    await waitFor(() => expect(screen.getByTestId('notification-bell-button')).toBeInTheDocument())
    expect(screen.queryByTestId('notification-bell-badge')).not.toBeInTheDocument()
  })
})
