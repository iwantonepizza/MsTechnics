import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useInfiniteApplications } from './hooks'

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

describe('useInfiniteApplications', () => {
  it('loads applications page by page', async () => {
    apiGet
      .mockResolvedValueOnce({
        data: { results: [{ id: 20 }], next_cursor: 'cursor-2', prev_cursor: null, has_more: true },
      })
      .mockResolvedValueOnce({
        data: { results: [{ id: 10 }], next_cursor: null, prev_cursor: null, has_more: false },
      })

    const { result } = renderHook(
      () => useInfiniteApplications({ display: 'ekb-1', box: 'all' }),
      { wrapper },
    )

    await waitFor(() => expect(result.current.applications).toEqual([{ id: 20 }]))
    await act(async () => {
      await result.current.fetchNextPage()
    })

    await waitFor(() => expect(result.current.applications).toEqual([{ id: 20 }, { id: 10 }]))
    expect(apiGet).toHaveBeenNthCalledWith(
      2,
      '/applications/',
      expect.objectContaining({
        params: expect.objectContaining({ display: 'ekb-1', box: 'all', cursor: 'cursor-2' }),
      }),
    )
  })
})
