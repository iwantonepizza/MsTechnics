import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ActivityFeedBand } from './MainMenuPage'

const useActivityLogMock = vi.fn()

vi.mock('@/entities/activity/hooks', () => ({
  useActivityLog: (filter: unknown) => useActivityLogMock(filter),
}))

vi.mock('@/shared/lib/useDeferredLoading', () => ({
  useDeferredLoading: (isLoading: boolean) => isLoading,
}))

beforeEach(() => {
  useActivityLogMock.mockReset()
  useActivityLogMock.mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  })
})
describe('ActivityFeedBand', () => {
  it('requests the default one-month unfiltered feed', () => {
    render(<ActivityFeedBand />)

    expect(useActivityLogMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        feed: true,
        kind: undefined,
        limit: 60,
      }),
    )
    expect(screen.getByTestId('activity-months-1')).toBeInTheDocument()
  })

  it('filters the feed by action entity kind', () => {
    render(<ActivityFeedBand />)

    fireEvent.click(screen.getByTestId('activity-kind-panel'))

    expect(useActivityLogMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        feed: true,
        kind: 'panel',
      }),
    )
  })

  it('shows a load error instead of an empty feed', () => {
    useActivityLogMock.mockReturnValue({
      data: [],
      isLoading: false,
      isError: true,
    })

    render(<ActivityFeedBand />)

    expect(screen.getByText('Не удалось загрузить последние действия')).toBeInTheDocument()
    expect(screen.queryByText('Действий за период нет')).not.toBeInTheDocument()
  })
})
