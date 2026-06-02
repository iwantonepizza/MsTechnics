import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DailyTasksPanel } from './DailyTasksPanel'

const mockComplete = vi.fn()
const useDailyTasksMock = vi.fn()
let mockTasks: Array<Record<string, unknown>> = []

vi.mock('@/entities/daily-tasks/hooks', () => ({
  useDailyTasks: (cityId?: number) => useDailyTasksMock(cityId),
  useCompleteDailyTask: () => ({ mutateAsync: mockComplete, isPending: false }),
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

beforeEach(() => {
  mockComplete.mockReset()
  useDailyTasksMock.mockReset()
  mockTasks = [
    {
      id: 1,
      name: 'Open camera',
      status: 'ready',
      link: 'https://x.test',
      available: true,
      description: '',
      start_time: null,
      end_time: null,
      city_id: 1,
      city_name: 'c',
    },
    {
      id: 2,
      name: 'Closed task',
      status: 'not_ready',
      link: 'https://y.test',
      available: false,
      description: '',
      start_time: null,
      end_time: null,
      city_id: 1,
      city_name: 'c',
    },
  ]
  useDailyTasksMock.mockImplementation(() => ({ data: mockTasks, isLoading: false }))
  vi.spyOn(window, 'open').mockImplementation(() => null)
})

describe('DailyTasksPanel', () => {
  it('requests tasks immediately for the current city even when collapsed', () => {
    render(<DailyTasksPanel cityId={1} readOnly={false} />)

    expect(useDailyTasksMock).toHaveBeenCalledWith(1)
    expect(screen.queryByTestId('daily-task-1')).not.toBeInTheDocument()
  })

  it('monitoring opens link and completes available task', async () => {
    render(<DailyTasksPanel cityId={1} readOnly={false} />)
    fireEvent.click(screen.getByTestId('daily-tasks-toggle'))
    fireEvent.click(await screen.findByTestId('daily-task-1'))
    expect(window.open).toHaveBeenCalled()
    expect(mockComplete).toHaveBeenCalledWith(1)
  })

  it('control (read-only) does not complete on click', () => {
    render(<DailyTasksPanel cityId={1} readOnly />)
    fireEvent.click(screen.getByTestId('daily-tasks-toggle'))
    fireEvent.click(screen.getByTestId('daily-task-1'))
    expect(mockComplete).not.toHaveBeenCalled()
  })

  it('does not complete a not-available task', () => {
    render(<DailyTasksPanel cityId={1} readOnly={false} />)
    fireEvent.click(screen.getByTestId('daily-tasks-toggle'))
    fireEvent.click(screen.getByTestId('daily-task-2'))
    expect(mockComplete).not.toHaveBeenCalled()
  })
})
