import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { GlobalSearch } from './GlobalSearch'
import { useAuthStore } from '@/features/auth/store'
import { apiClient } from '@/shared/api/client'

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

function renderSearch(initialEntry = '/menu') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <GlobalSearch />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('GlobalSearch', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'token',
      user: {
        id: 1,
        username: 'admin',
        first_name: 'Admin',
        last_name: 'User',
        permission: 'admin',
        allowed_city: [],
      } as never,
    })
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('opens with slash and closes with escape', async () => {
    renderSearch()

    fireEvent.keyDown(window, { key: '/' })
    expect(await screen.findByRole('textbox', { name: 'Глобальный поиск' })).toBeInTheDocument()

    fireEvent.keyDown(screen.getByRole('textbox', { name: 'Глобальный поиск' }), { key: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByRole('textbox', { name: 'Глобальный поиск' })).not.toBeInTheDocument()
    })
  })

  it('renders grouped results from all six categories', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        displays: [{ id: 1, name: 'RK-1', description: 'РК-1', slug: 'rk-1', city_name: 'Екатеринбург', city_slug: 'ekb', score: 0.9 }],
        panels: [{ id: 2, name: 'P-007', display_name: 'РК-1', display_slug: 'rk-1', city_slug: 'ekb', condition_name: 'work', department_name: 'monitor', active_application_id: null, score: 0.8 }],
        applications: [{ id: 3, display_name: 'РК-1', display_slug: 'rk-1', city_slug: 'ekb', panel_name: 'P-007', cell_position: 'A-01', status_name: 'sent_to_service', initial_comment: 'Сбой', score: 0.7 }],
        departures: [{ id: 4, description: 'Выезд на РК-1', executor_name: 'Иван Иванов', status_name: 'created', score: 0.6 }],
        users: [{ id: 5, username: 'ivanov', full_name: 'Иван Иванов', permission: 'service', score: 0.5 }],
        storage: [{ id: 6, kind: 'wires', name: 'Кабель 220V', description: 'Склад 1', count: 2, score: 0.4 }],
      },
    } as never)

    renderSearch('/control')

    fireEvent.keyDown(window, { key: '/' })
    const input = await screen.findByRole('textbox', { name: 'Глобальный поиск' })
    fireEvent.change(input, { target: { value: 'rk' } })

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/search/', { params: { q: 'rk', limit: 8 } })
    }, { timeout: 1500 })

    expect(await screen.findByText('Экраны')).toBeInTheDocument()
    expect(screen.getByText('Панели')).toBeInTheDocument()
    expect(screen.getByText('Заявки')).toBeInTheDocument()
    expect(screen.getByText('Выезды')).toBeInTheDocument()
    expect(screen.getByText('Пользователи')).toBeInTheDocument()
    expect(screen.getByText('ЗИП')).toBeInTheDocument()

    expect(screen.getAllByText('РК-1').length).toBeGreaterThan(0)
    expect(screen.getByText('P-007')).toBeInTheDocument()
    expect(screen.getByText('Заявка #3')).toBeInTheDocument()
    expect(screen.getByText('Выезд на РК-1')).toBeInTheDocument()
    expect(screen.getByText('ivanov')).toBeInTheDocument()
    expect(screen.getByText('Кабель 220V')).toBeInTheDocument()
  })
})
