import { formatDate } from '@/shared/lib/utils'
import { Paperclip } from 'lucide-react'
import type { ApplicationEvent } from '@/shared/api/types'

const STAGE_LABELS: Record<string, { label: string; emoji: string }> = {
  monitoring_create:  { label: 'Создана мониторингом', emoji: '📋' },
  control_apply:      { label: 'Принята контролем',    emoji: '✅' },
  control_send:       { label: 'Отправлена в сервис',  emoji: '📤' },
  service_apply:      { label: 'Принята сервисом',     emoji: '🔧' },
  service_complete:   { label: 'Ремонт выполнен',      emoji: '✔️' },
  service_unable:     { label: 'Ремонт невозможен',    emoji: '❌' },
  archive_done:       { label: 'Архивирована',         emoji: '📦' },
  archive_unable:     { label: 'Архивирована (невозможно)', emoji: '📦' },
}

export function EventTimeline({ events }: { events: ApplicationEvent[] }) {
  if (!events.length) return (
    <p className="text-xs text-text-muted py-4 text-center">История пуста</p>
  )

  return (
    <div className="relative">
      {/* Вертикальная линия */}
      <div className="absolute left-3 top-2 bottom-2 w-px bg-surface-3" />

      <div className="space-y-4 pl-8">
        {events.map((ev) => {
          const meta = STAGE_LABELS[ev.stage] ?? { label: ev.stage, emoji: '•' }
          return (
            <div key={ev.id} className="relative">
              {/* Dot */}
              <div className="absolute -left-5 mt-0.5 w-2 h-2 rounded-full bg-surface-3 ring-2 ring-surface-1" />

              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs">{meta.emoji}</span>
                  <span className="text-xs font-medium text-text-primary">{meta.label}</span>
                  <span className="ml-auto text-2xs text-text-muted">{formatDate(ev.timestamp)}</span>
                </div>
                <p className="text-2xs text-text-secondary">
                  <span className="text-text-muted">{ev.user}</span>
                  {ev.comment && <> · {ev.comment}</>}
                </p>
                {ev.file_url && (
                  <a
                    href={ev.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-2xs text-brand-400 hover:underline"
                  >
                    <Paperclip size={10} /> Прикреплённый файл
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
