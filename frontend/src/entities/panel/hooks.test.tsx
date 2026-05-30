import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/shared/api/client'
import type { Panel, PaginatedResponse } from '@/shared/api/types'

import { usePanels } from './hooks'

function makePanel(id: number): Panel {
  return {
    id,
    name: `P-${id.toString().padStart(3, '0')}`,
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
      icon: { id: 1, unicode_symbol: '+' },
    },
  }
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

function page(results: Panel[], nextCursor: string | null): PaginatedResponse<Panel> {
  return {
    results,
    next_cursor: nextCursor,
    prev_cursor: null,
    has_more: Boolean(nextCursor),
  }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('usePanels', () => {
  it('returns only the first page by default', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: page([makePanel(1)], 'cursor-2'),
    } as never)

    const { result } = renderHook(
      () => usePanels({ department: 'zip', display: '1' }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual([makePanel(1)])
    expect(getSpy).toHaveBeenCalledTimes(1)
  })

  it('concatenates cursor pages when fetchAll is enabled', async () => {
    const getSpy = vi
      .spyOn(apiClient, 'get')
      .mockResolvedValueOnce({
        data: page([makePanel(1)], 'cursor-2'),
      } as never)
      .mockResolvedValueOnce({
        data: page([makePanel(2), makePanel(3)], null),
      } as never)

    const { result } = renderHook(
      () => usePanels({ department: 'zip', display: '1', fetchAll: true }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual([makePanel(1), makePanel(2), makePanel(3)])
    expect(getSpy).toHaveBeenCalledTimes(2)
    expect(getSpy.mock.calls[1][1]).toMatchObject({
      params: expect.objectContaining({
        department: 'zip',
        display: '1',
        cursor: 'cursor-2',
      }),
    })
  })
})
