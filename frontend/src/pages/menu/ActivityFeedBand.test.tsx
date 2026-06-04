import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActivityFeedBand } from './MainMenuPage'

const refetchMock = vi.fn()
const useActivityLogMock = vi.fn()

vi.mock('@/entities/activity/hooks', () => ({
  useActivityLog: (filter: unknown) => useActivityLogMock(filter),
}))

vi.mock('@/shared/lib/useDeferredLoading', () => ({
  useDeferredLoading: (isLoading: boolean) => isLoading,
}))

beforeEach(() => {
  refetchMock.mockReset()
  useActivityLogMock.mockReset()
  useActivityLogMock.mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
    refetch: refetchMock,
  })
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ActivityFeedBand', () => {
  it('keeps the since filter stable across unrelated renders', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-04T10:00:00Z'))
    const { rerender } = render(<ActivityFeedBand />)
    const firstSince =
      useActivityLogMock.mock.calls[useActivityLogMock.mock.calls.length - 1]?.[0].since

    vi.setSystemTime(new Date('2026-06-04T10:01:00Z'))
    rerender(<ActivityFeedBand />)

    const lastCall = useActivityLogMock.mock.calls[useActivityLogMock.mock.calls.length - 1]
    expect(lastCall?.[0].since).toBe(firstSince)
  })

  it('filters the feed by action entity kind', () => {
    render(<ActivityFeedBand />)

    fireEvent.click(screen.getByTestId('activity-kind-panel'))

    expect(useActivityLogMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        feed: true,
        kind: 'panel',
        limit: 60,
      }),
    )
  })

  it('shows a load error and supports an explicit retry', () => {
    useActivityLogMock.mockReturnValue({
      data: [],
      isLoading: false,
      isError: true,
      refetch: refetchMock,
    })

    render(<ActivityFeedBand />)
    fireEvent.click(screen.getByRole('button', { name: 'Повторить' }))

    expect(screen.getByText('Не удалось загрузить последние действия')).toBeInTheDocument()
    expect(screen.queryByText('Действий за период нет')).not.toBeInTheDocument()
    expect(refetchMock).toHaveBeenCalledTimes(1)
  })
})
