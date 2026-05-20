import {
  Archive,
  Check,
  CheckCheck,
  FilePlus,
  Paperclip,
  Send,
  Wrench,
  X,
  type LucideIcon,
} from 'lucide-react'

import { formatDate } from '@/shared/lib/utils'
import type { ApplicationEvent } from '@/shared/api/types'

const STAGE_LABELS: Record<
  string,
  { label: string; Icon: LucideIcon }
> = {
  monitoring_create: { label: 'Создана мониторингом', Icon: FilePlus },
  control_apply: { label: 'Принята контролем', Icon: Check },
  control_send: { label: 'Отправлена в сервис', Icon: Send },
  service_apply: { label: 'Принята сервисом', Icon: Wrench },
  service_complete: { label: 'Ремонт выполнен', Icon: CheckCheck },
  service_unable: { label: 'Ремонт невозможен', Icon: X },
  archive_done: { label: 'Архивирована', Icon: Archive },
  archive_unable: { label: 'Архивирована (невозможно)', Icon: Archive },
}

export function EventTimeline({ events }: { events: ApplicationEvent[] }) {
  if (!events.length) {
    return (
      <p className="py-4 text-center text-xs" style={{ color: 'var(--fg-mute)' }}>
        История пуста
      </p>
    )
  }

  return (
    <div className="relative">
      <div
        className="absolute bottom-2 left-3 top-2 w-px"
        style={{ background: 'var(--border-subtle)' }}
      />

      <div className="space-y-4 pl-8">
        {events.map(event => {
          const meta = STAGE_LABELS[event.stage]

          return (
            <div key={event.id} className="relative">
              <div
                className="absolute -left-5 mt-0.5 h-2 w-2 rounded-full"
                style={{ background: 'var(--border)', boxShadow: '0 0 0 2px var(--bg-1)' }}
              />

              <div>
                <div className="mb-0.5 flex items-center gap-2">
                  {meta ? <meta.Icon size={12} /> : <span className="text-xs">•</span>}
                  <span className="text-xs font-medium" style={{ color: 'var(--fg)' }}>
                    {meta?.label ?? event.stage}
                  </span>
                  <span className="ml-auto text-2xs" style={{ color: 'var(--fg-mute)' }}>
                    {formatDate(event.timestamp)}
                  </span>
                </div>
                <p className="text-2xs" style={{ color: 'var(--fg-dim)' }}>
                  <span style={{ color: 'var(--fg-mute)' }}>{event.user}</span>
                  {event.comment && <> · {event.comment}</>}
                </p>
                {event.file_url && (
                  <a
                    href={event.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-2xs hover:underline"
                    style={{ color: 'var(--accent)' }}
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
