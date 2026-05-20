import type { ReactNode } from 'react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Paperclip, Printer, X } from 'lucide-react'

import { EventTimeline } from '@/entities/application/EventTimeline'
import { Badge } from '@/shared/ui/Badge'
import { Button, type ButtonProps } from '@/shared/ui/Button'
import { formatDate, formatRelative } from '@/shared/lib/utils'
import type { ApplicationDetail, ApplicationEvent } from '@/shared/api/types'

import './application-detail-sheet.css'

interface ApplicationAction {
  key: string
  label: string
  icon: ReactNode
  variant: ButtonProps['variant']
}

interface ApplicationDetailSheetProps {
  application: ApplicationDetail
  events: ApplicationEvent[]
  cityName: string
  actions: ApplicationAction[]
  canRemovePanel: boolean
  onAction: (key: string) => void
  onRemovePanel: () => void
  onClose: () => void
}

const STAGE_LABELS: Record<string, string> = {
  monitoring_create: 'Мониторинг',
  control_apply: 'Контроль: принято',
  control_send: 'Контроль: в сервис',
  service_apply: 'Сервис: принято',
  service_complete: 'Сервис: выполнено',
  service_unable: 'Сервис: невозможно',
  archive_done: 'Архив',
  archive_unable: 'Архив',
}

export function ApplicationDetailSheet({
  application,
  events,
  cityName,
  actions,
  canRemovePanel,
  onAction,
  onRemovePanel,
  onClose,
}: ApplicationDetailSheetProps) {
  const orderedEvents = [...events].sort(
    (left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp),
  )
  const createdAt = orderedEvents[0]?.timestamp ?? application.last_update_date_time ?? null
  const printedAt = format(new Date(), 'dd.MM.yyyy HH:mm', { locale: ru })
  const executorName = application.executor
    ? `${application.executor.first_name} ${application.executor.last_name}`
    : '—'
  const attachmentEvents = orderedEvents.filter(event => Boolean(event.file_url))

  return (
    <div className="application-detail-sheet flex h-full flex-col">
      <div
        className="application-detail-screen-header flex items-center justify-between px-4 py-3 shrink-0"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2">
          <span style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            #{application.id}
          </span>
          <Badge
            label={application.status.description ?? application.status.name}
            bgHex={application.status.color.hex}
            fgHex={application.status.color_text.hex}
            icon={application.status.icon?.unicode_symbol}
          />
        </div>
        <button
          onClick={onClose}
          className="application-detail-close flex items-center justify-center w-6 h-6 rounded transition-colors"
          style={{ color: 'var(--fg-mute)' }}
        >
          <X size={12} />
        </button>
      </div>

      <div className="application-detail-content flex-1 overflow-y-auto px-4 py-3 space-y-4">
        <header className="application-detail-print-header print-only">
          <img
            src="/logo-supersymmetria-black.svg"
            alt=""
            className="application-detail-print-logo"
          />
          <div>
            <div className="text-xs font-semibold" style={{ color: '#000' }}>
              Бюро визуальных коммуникаций
            </div>
            <div className="text-[11px]" style={{ color: '#444' }}>
              Система «Суперсимметрия»
            </div>
          </div>
          <div className="ml-auto text-right text-[11px]" style={{ color: '#000' }}>
            {printedAt}
          </div>
        </header>

        <div className="application-detail-print-title print-only">
          <h1 className="text-xl font-semibold" style={{ color: '#000' }}>
            Заявка №{application.id}
          </h1>
        </div>

        <div className="application-detail-print-meta space-y-1.5">
          {[
            ['Экран', application.display.description ?? application.display.slug ?? '—'],
            ['Город', cityName],
            ['Позиция', application.cell.position ?? '—'],
            ['Панель', application.panel.name],
            ['Создана', formatDate(createdAt)],
            ['Исполнитель', executorName],
            ['Обновлено', formatRelative(application.last_update_date_time)],
          ].map(([label, value]) => (
            <div key={label} className="application-detail-print-row text-xs">
              <span
                className="application-detail-print-row-label"
                style={{ color: 'var(--fg-mute)' }}
              >
                {label}
              </span>
              <span
                className="application-detail-print-row-value"
                style={{
                  color: 'var(--fg-dim)',
                  fontFamily: label === 'Позиция' || label === 'Панель' ? 'var(--font-mono)' : undefined,
                }}
              >
                {value}
              </span>
            </div>
          ))}
        </div>

        <div className="application-detail-print-status print-only">
          Статус: {application.status.description ?? application.status.name}
        </div>

        {application.initial_comment ? (
          <div
            className="application-detail-print-note rounded-md text-xs"
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--fg-dim)',
            }}
          >
            {application.initial_comment}
          </div>
        ) : null}

        <div className="application-detail-actions space-y-3 screen-only">
          <div className="flex flex-wrap gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              icon={<Printer size={12} />}
              onClick={() => window.print()}
            >
              Печать
            </Button>
            {actions.map(action => (
              <Button
                key={action.key}
                variant={action.variant}
                size="sm"
                icon={action.icon}
                onClick={() => onAction(action.key)}
              >
                {action.label}
              </Button>
            ))}
          </div>
          {canRemovePanel ? (
            <Button variant="danger" size="sm" onClick={onRemovePanel}>
              Снять панель
            </Button>
          ) : null}
        </div>

        {orderedEvents.length > 0 ? (
          <>
            <div className="application-detail-screen-timeline screen-only">
              <span
                className="mb-2 block text-2xs uppercase tracking-widest"
                style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}
              >
                История
              </span>
              <EventTimeline events={orderedEvents} />
            </div>

            <section className="application-detail-print-section print-only">
              <h2>Комментарии по этапам</h2>
              <div className="application-detail-print-events">
                {orderedEvents.map(event => (
                  <article key={event.id} className="application-detail-print-event">
                    <div className="application-detail-print-event-header">
                      <span>{STAGE_LABELS[event.stage] ?? event.stage}</span>
                      <span>{formatDate(event.timestamp)}</span>
                    </div>
                    <div className="application-detail-print-event-meta">
                      {event.user || 'Система'}
                    </div>
                    <div className="application-detail-print-event-comment">
                      {event.comment || '—'}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {attachmentEvents.length > 0 ? (
          <section className="application-detail-print-section print-only">
            <h2>Файлы и фото</h2>
            <div className="application-detail-print-attachments">
              {attachmentEvents.map(event => (
                <div key={event.id} className="application-detail-print-attachment">
                  <img
                    src={event.file_url}
                    alt=""
                    className="application-detail-print-thumb"
                    onError={handleImageError}
                  />
                  <div className="mb-1 text-[10pt]" style={{ color: '#000' }}>
                    {STAGE_LABELS[event.stage] ?? event.stage}
                  </div>
                  <a
                    href={event.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="application-detail-print-link inline-flex items-start gap-1"
                  >
                    <Paperclip size={12} />
                    <span>{event.file_url}</span>
                  </a>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <footer className="application-detail-print-footer print-only print-flex">
          <div>Исполнитель: ___________________________</div>
          <div>Дата: ___________________</div>
        </footer>

        <div className="print-only text-[10pt]" style={{ color: '#444' }}>
          Распечатано {printedAt} из системы Суперсимметрия
        </div>
      </div>
    </div>
  )
}

function handleImageError(event: React.SyntheticEvent<HTMLImageElement>) {
  event.currentTarget.style.display = 'none'
}
