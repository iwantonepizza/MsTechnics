import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DailyTasksPanel } from './DailyTasksPanel'

const mockComplete = vi.fn()
let mockTasks: Array<Record<string, unknown>> = []

vi.mock('@/entities/daily-tasks/hooks', () => ({
  useDailyTasks: () => ({ data: mockTasks, isLoading: false }),
  useCompleteDailyTask: () => ({ mutateAsync: mockComplete, isPending: false }),
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

beforeEach(() => {
  mockComplete.mockReset()
  mockTasks = [
    { id: 1, name: 'Открыть камеру', status: 'ready', link: 'https://x.test', available: true, description: '', start_time: null, end_time: null, city_id: 1, city_name: 'c' },
    { id: 2, name: 'Закрытая', status: 'not_ready', link: 'https://y.test', available: false, description: '', start_time: null, end_time: null, city_id: 1, city_name: 'c' },
  ]
  vi.spyOn(window, 'open').mockImplementation(() => null)
})

describe('DailyTasksPanel', () => {
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
