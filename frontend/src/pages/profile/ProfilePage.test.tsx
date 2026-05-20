import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ProfilePage } from './ProfilePage'

vi.mock('@/widgets/navigation/CrumbContext', () => ({
  useCrumb: () => ({ setCrumb: vi.fn() }),
}))

vi.mock('@/shared/lib/theme', () => ({
  useTheme: () => ({ theme: 'system', resolvedTheme: 'light', setTheme: vi.fn() }),
}))

vi.mock('@/features/auth/hooks', () => ({
  useMe: () => ({
    data: {
      username: 'ivanov',
      email: 'i@example.com',
      permission: 'service',
      telegram_id: null,
      max_chat_id: null,
      allowed_cities: [],
    },
  }),
}))

const mockApiGet = vi.fn()
vi.mock('@/shared/api/client', () => ({
  apiClient: { get: (...args: unknown[]) => mockApiGet(...args) },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  mockApiGet.mockReset()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('ProfilePage - история действий (T-7-014)', () => {
  it('shows empty-state when user has no activity', async () => {
    mockApiGet.mockResolvedValue({ data: { results: [] } })
    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('profile-activity')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText(/история пуста/i)).toBeInTheDocument()
    })
  })

  it('renders activity entries with localized event label and target', async () => {
    mockApiGet.mockResolvedValue({
      data: {
        results: [
          {
            id: 1,
            event_type: 'application.created',
            target_kind: 'application',
            target_id: 42,
            target_summary: { kind: 'application', id: 42 },
            actor_name: 'ivanov',
            occurred_at: '2026-05-18T12:34:00Z',
            description: 'Создана заявка по панели P-007',
            comment: null,
            payload: null,
          },
          {
            id: 2,
            event_type: 'panel.condition_changed',
            target_kind: 'panel',
            target_id: 7,
            target_summary: { kind: 'panel', id: 7 },
            actor_name: 'ivanov',
            occurred_at: '2026-05-17T09:00:00Z',
            description: null,
            comment: 'Заменили блок питания',
            payload: null,
          },
        ],
      },
    })
    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('activity-list')).toBeInTheDocument()
    })
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)

    expect(screen.getAllByText(/Создана заявка/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Смена состояния панели/).length).toBeGreaterThanOrEqual(1)

    expect(screen.getByText(/· Заявка #42/)).toBeInTheDocument()
    expect(screen.getByText(/· Панель #7/)).toBeInTheDocument()

    expect(screen.getByText('Создана заявка по панели P-007')).toBeInTheDocument()
    expect(screen.getByText('Заменили блок питания')).toBeInTheDocument()
  })

  it('calls activity-log endpoint with actor=username param', async () => {
    mockApiGet.mockResolvedValue({ data: { results: [] } })
    renderPage()

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalled()
    })
    const calls = mockApiGet.mock.calls
    const activityCall = calls.find(call => call[0] === '/activity-log/')
    expect(activityCall).toBeDefined()
    expect(activityCall![1].params).toMatchObject({ actor: 'ivanov', limit: 50 })
  })
})

describe('ProfilePage - звуковые уведомления (T-7-012)', () => {
  beforeEach(() => {
    localStorage.clear()
    mockApiGet.mockResolvedValue({ data: { results: [] } })
  })

  it('renders sound section with default enabled state', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('profile-sound')).toBeInTheDocument()
    })
    const toggle = screen.getByTestId('sound-toggle') as HTMLInputElement
    expect(toggle.checked).toBe(true)
  })

  it('toggle updates localStorage', async () => {
    renderPage()
    const toggle = screen.getByTestId('sound-toggle') as HTMLInputElement

    fireEvent.click(toggle)
    expect(localStorage.getItem('notificationSound.enabled')).toBe('0')

    fireEvent.click(toggle)
    expect(localStorage.getItem('notificationSound.enabled')).toBe('1')
  })

  it('preview button stays enabled even when sound is disabled', async () => {
    localStorage.setItem('notificationSound.enabled', '0')
    renderPage()

    const preview = screen.getByTestId('sound-preview') as HTMLButtonElement
    expect(preview.disabled).toBe(false)
  })
})
