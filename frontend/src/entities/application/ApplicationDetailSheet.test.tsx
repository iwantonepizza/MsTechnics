import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApplicationDetailSheet } from './ApplicationDetailSheet'

describe('ApplicationDetailSheet', () => {
  it('calls window.print from the print button and renders print sections', () => {
    const printSpy = vi.fn()
    Object.defineProperty(window, 'print', {
      value: printSpy,
      writable: true,
    })

    render(
      <ApplicationDetailSheet
        application={{
          id: 42,
          status: {
            id: 1,
            name: 'sent_to_service',
            description: 'Отправлена в сервис',
            color: { id: 1, name: 'amber', hex: '#ffaa00' },
            color_text: { id: 2, name: 'black', hex: '#000000' },
            icon: { id: 1, unicode_symbol: '!' },
            next_possible: [],
          },
          display: {
            id: 1,
            slug: 'rk-1',
            description: 'РК-1',
            city: { slug: 'ekaterinburg', name: 'Екатеринбург' },
          },
          panel: { id: 7, name: 'P-007' },
          cell: { id: 3, position: 'A-01' },
          executor: { id: 5, first_name: 'Иван', last_name: 'Иванов' },
          initial_comment: 'Нужно проверить соединение.',
          last_update_date_time: '2026-05-17T12:00:00+05:00',
        }}
        events={[
          {
            id: 1,
            stage: 'monitoring_create',
            user: 'katya',
            timestamp: '2026-05-17T10:00:00+05:00',
            comment: 'Первичная диагностика',
            file_url: 'https://example.com/photo.jpg',
            state_from: '',
            state_to: 'monitoring_create',
          },
        ]}
        cityName="Екатеринбург"
        actions={[
          { key: 'done', label: 'Выполнено', icon: '✓', variant: 'primary' },
        ]}
        canRemovePanel
        onAction={vi.fn()}
        onRemovePanel={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /печать/i }))

    expect(printSpy).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Бюро визуальных коммуникаций')).toBeInTheDocument()
    expect(screen.getByText('Заявка №42')).toBeInTheDocument()
    expect(screen.getByText('Файлы и фото')).toBeInTheDocument()
  })
})
