import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useInfiniteActivityLog } from './hooks'

const apiGet = vi.fn()

vi.mock('@/shared/api/client', () => ({
  apiClient: { get: (...args: unknown[]) => apiGet(...args) },
}))

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

beforeEach(() => {
  apiGet.mockReset()
})

describe('useInfiniteActivityLog', () => {
  it('loads the next cursor and keeps all-time entries', async () => {
    apiGet
      .mockResolvedValueOnce({
        data: { results: [{ id: 2 }], next_cursor: 'cursor-2', prev_cursor: null, has_more: true },
      })
      .mockResolvedValueOnce({
        data: { results: [{ id: 1 }], next_cursor: null, prev_cursor: null, has_more: false },
      })

    const { result } = renderHook(() => useInfiniteActivityLog({ feed: true, limit: 1 }), { wrapper })

    await waitFor(() => expect(result.current.entries).toEqual([{ id: 2 }]))
    await act(async () => {
      await result.current.fetchNextPage()
    })

    await waitFor(() => expect(result.current.entries).toEqual([{ id: 2 }, { id: 1 }]))
    expect(apiGet).toHaveBeenNthCalledWith(
      2,
      '/activity-log/',
      expect.objectContaining({ params: expect.objectContaining({ cursor: 'cursor-2' }) }),
    )
    expect(apiGet.mock.calls[0][1].params.since).toBeUndefined()
  })
})
