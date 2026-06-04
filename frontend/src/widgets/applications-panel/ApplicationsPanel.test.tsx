import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApplicationsPanel } from './ApplicationsPanel'

const mockUseApplications = vi.fn()
const mockUseActivityLog = vi.fn()

vi.mock('@/entities/application/hooks', () => ({
  useApplications: (...args: unknown[]) => mockUseApplications(...args),
}))

vi.mock('@/entities/activity/hooks', () => ({
  useActivityLog: (...args: unknown[]) => mockUseActivityLog(...args),
}))

vi.mock('@/entities/application/ApplicationCard', () => ({
  ApplicationCard: ({ application }: { application: { id: number } }) => (
    <div data-testid={`application-card-${application.id}`}>app #{application.id}</div>
  ),
}))

describe('ApplicationsPanel', () => {
  it('renders monitoring tabs with history timeline', () => {
    mockUseApplications.mockReturnValue({
      data: { results: [{ id: 11 }] },
      isLoading: false,
    })
    mockUseActivityLog.mockReturnValue({
      data: [
        {
          id: 301,
          event_type: 'application.created',
          actor_name: 'ivanov',
          occurred_at: '2026-05-30T10:00:00Z',
          description: 'Создана заявка #11',
          comment: 'first issue',
          target_summary: { kind: 'application', id: 11 },
        },
      ],
      isLoading: false,
    })

    render(<ApplicationsPanel displaySlug="ekb-1" department="monitoring" />)

    expect(screen.getByText('Созданные')).toBeInTheDocument()
    expect(screen.getByText('Все')).toBeInTheDocument()
    expect(screen.getByText('История')).toBeInTheDocument()
    expect(screen.getByTestId('application-card-11')).toBeInTheDocument()

    fireEvent.click(screen.getByText('История'))

    expect(screen.getByTestId('applications-history-tab')).toBeInTheDocument()
    expect(screen.getByText('Создана заявка #11')).toBeInTheDocument()
    expect(screen.getByText('first issue')).toBeInTheDocument()
    expect(screen.getByText('application #11')).toBeInTheDocument()
    expect(mockUseActivityLog).toHaveBeenLastCalledWith({
      display: 'ekb-1',
      eventTypes: expect.stringContaining('application.created'),
    })
  })

  it('does not render history tab for control', () => {
    mockUseApplications.mockReturnValue({
      data: { results: [] },
      isLoading: false,
    })
    mockUseActivityLog.mockReturnValue({
      data: [],
      isLoading: false,
    })

    render(<ApplicationsPanel displaySlug="ekb-1" department="control" />)

    expect(screen.getByText('Запросы')).toBeInTheDocument()
    expect(screen.getByText('В работе')).toBeInTheDocument()
    expect(screen.queryByText('История')).not.toBeInTheDocument()
    expect(mockUseActivityLog).toHaveBeenLastCalledWith({})
  })
})
