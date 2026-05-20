import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { PanelRemovalModal } from './PanelActionModals'

const baseCondition = {
  id: 1,
  name: 'work',
  description: 'Рабочая',
  color: { id: 1, name: 'green', hex: '#00aa00' },
  icon: { id: 1, unicode_symbol: '🟢' },
}

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query')
  return {
    ...actual,
    useQuery: vi.fn(() => ({
      data: [
        baseCondition,
        {
          id: 2,
          name: 'error',
          description: 'Ошибка',
          color: { id: 2, name: 'yellow', hex: '#ffcc00' },
          icon: { id: 2, unicode_symbol: '⚠️' },
        },
      ],
      isLoading: false,
    })),
  }
})

vi.mock('@/entities/panel/hooks', () => ({
  useChangeCondition: vi.fn(),
  useChangeDepartment: vi.fn(),
  useMoveToCell: vi.fn(),
  usePanels: vi.fn(() => ({ data: [], isLoading: false })),
  useRemovePanel: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}))

describe('PanelRemovalModal', () => {
  it('renders application-context mode', () => {
    render(
      <PanelRemovalModal
        open
        onClose={() => {}}
        panel={{ id: 1, name: 'P-001', condition: baseCondition, application_status_name: 'work_in_service' }}
        applicationId={42}
      />,
    )

    expect(screen.getAllByText(/42/)).toHaveLength(2)
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(document.body).toMatchSnapshot()
  })

  it('renders manual mode with active-application warning', () => {
    render(
      <PanelRemovalModal
        open
        onClose={() => {}}
        panel={{
          id: 2,
          name: 'P-002',
          condition: baseCondition,
          application_status_name: 'sent_to_control',
          active_application_id: 77,
        }}
      />,
    )

    expect(screen.getAllByText(/P-002/)).toHaveLength(2)
    expect(screen.getByRole('checkbox')).toBeChecked()
    expect(screen.getByText(/77/)).toBeInTheDocument()
    expect(document.body).toMatchSnapshot()
  })
})
