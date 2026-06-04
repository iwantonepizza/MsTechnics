import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ActivityFeedBand } from './MainMenuPage'

const refetchMock = vi.fn()
const fetchNextPageMock = vi.fn()
const useInfiniteActivityLogMock = vi.fn()

vi.mock('@/entities/activity/hooks', () => ({
  useInfiniteActivityLog: (filter: unknown) => useInfiniteActivityLogMock(filter),
}))

vi.mock('@/shared/lib/useDeferredLoading', () => ({
  useDeferredLoading: (isLoading: boolean) => isLoading,
}))

beforeEach(() => {
  refetchMock.mockReset()
  fetchNextPageMock.mockReset()
  useInfiniteActivityLogMock.mockReset()
  useInfiniteActivityLogMock.mockReturnValue({
    entries: [],
    isLoading: false,
    isError: false,
    refetch: refetchMock,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: fetchNextPageMock,
  })
})

describe('ActivityFeedBand', () => {
  it('loads the all-time activity feed without a date limit', () => {
    render(<ActivityFeedBand />)

    expect(useInfiniteActivityLogMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        feed: true,
        limit: 60,
      }),
    )
    expect(useInfiniteActivityLogMock.mock.calls[0]?.[0]).not.toHaveProperty('since')
    expect(screen.getByText('Всё время')).toBeInTheDocument()
  })

  it('filters the feed by action entity kind', () => {
    render(<ActivityFeedBand />)

    fireEvent.click(screen.getByTestId('activity-kind-panel'))

    expect(useInfiniteActivityLogMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        feed: true,
        kind: 'panel',
        limit: 60,
      }),
    )
  })

  it('shows a load error and supports an explicit retry', () => {
    useInfiniteActivityLogMock.mockReturnValue({
      entries: [],
      isLoading: false,
      isError: true,
      refetch: refetchMock,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: fetchNextPageMock,
    })

    render(<ActivityFeedBand />)
    fireEvent.click(screen.getByRole('button', { name: 'Повторить' }))

    expect(screen.getByText('Не удалось загрузить последние действия')).toBeInTheDocument()
    expect(screen.queryByText('Действий за период нет')).not.toBeInTheDocument()
    expect(refetchMock).toHaveBeenCalledTimes(1)
  })
})
