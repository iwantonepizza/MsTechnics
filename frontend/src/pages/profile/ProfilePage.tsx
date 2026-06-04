import { useEffect, useState } from 'react'
import { Activity, MapPin, MessageCircle, Shield, Volume2, VolumeX } from 'lucide-react'

import { useInfiniteMyActivity, type ActivityLogEntry } from '@/entities/activity/hooks'
import { useMe } from '@/features/auth/hooks'
import {
  isNotificationSoundEnabled,
  playNotificationSound,
  setNotificationSoundEnabled,
} from '@/shared/lib/notificationSound'
import { useTheme, type ThemePreference } from '@/shared/lib/theme'
import { Button } from '@/shared/ui/Button'
import { InfiniteScrollSentinel } from '@/shared/ui/InfiniteScrollSentinel'
import { Spinner } from '@/shared/ui/Spinner'
import { Toggle } from '@/shared/ui/Toggle'
import { useCrumb } from '@/widgets/navigation/CrumbContext'

const THEME_OPTIONS: Array<{ value: ThemePreference; label: string; description: string }> = [
  { value: 'light', label: 'Светлая', description: 'Всегда использовать светлую тему.' },
  { value: 'dark', label: 'Тёмная', description: 'Всегда использовать тёмную тему.' },
  { value: 'system', label: 'Системная', description: 'Следовать настройке ОС и браузера.' },
]

export function ProfilePage() {
  const { data: me } = useMe()
  const { theme, resolvedTheme, setTheme } = useTheme()
  const { setCrumb } = useCrumb()
  const activityQuery = useInfiniteMyActivity(me?.username)
  const activity = activityQuery.entries
  const [soundEnabled, setSoundEnabledState] = useState<boolean>(() => isNotificationSoundEnabled())

  const handleSoundToggle = (next: boolean) => {
    setNotificationSoundEnabled(next)
    setSoundEnabledState(next)
  }

  useEffect(() => {
    setCrumb('Профиль')
    return () => setCrumb(null)
  }, [setCrumb])

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col gap-6 overflow-y-auto px-6 py-6">
      <section
        className="rounded-lg border p-5"
        style={{ background: 'var(--bg-1)', borderColor: 'var(--border-subtle)' }}
      >
        <div className="mb-4">
          <h1 className="text-lg font-semibold" style={{ color: 'var(--fg)' }}>
            Личный кабинет
          </h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--fg-dim)' }}>
            Настройки пользователя и темы интерфейса.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <InfoRow label="Пользователь" value={me?.username ?? '—'} />
          <InfoRow label="Email" value={me?.email ?? '—'} />
          <InfoRow label="Роль" value={me?.permission ?? '—'} icon={<Shield size={13} />} />
          <InfoRow
            label="Telegram / MAX"
            value={
              me?.telegram_id || me?.max_chat_id
                ? [me?.telegram_id, me?.max_chat_id].filter(Boolean).join(' / ')
                : 'Не подключено'
            }
            icon={<MessageCircle size={13} />}
          />
        </div>

        <div className="mt-5">
          <div
            className="mb-2 text-xs uppercase tracking-wider"
            style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}
          >
            Доступные города
          </div>
          <div className="flex flex-wrap gap-2">
            {(me?.allowed_cities ?? []).length > 0 ? (
              me?.allowed_cities.map(city => (
                <span
                  key={city.id}
                  className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs"
                  style={{
                    background: 'var(--bg-0)',
                    borderColor: 'var(--border-subtle)',
                    color: 'var(--fg-dim)',
                  }}
                >
                  <MapPin size={12} />
                  {city.name}
                </span>
              ))
            ) : (
              <span className="text-sm" style={{ color: 'var(--fg-faint)' }}>
                Нет доступных городов
              </span>
            )}
          </div>
        </div>
      </section>

      <section
        className="rounded-lg border p-5"
        style={{ background: 'var(--bg-1)', borderColor: 'var(--border-subtle)' }}
      >
        <div className="mb-4">
          <h2 className="text-base font-semibold" style={{ color: 'var(--fg)' }}>
            Тема интерфейса
          </h2>
          <p className="mt-1 text-sm" style={{ color: 'var(--fg-dim)' }}>
            Сейчас активна {resolvedTheme === 'dark' ? 'тёмная' : 'светлая'} тема.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {THEME_OPTIONS.map(option => {
            const selected = theme === option.value
            return (
              <label
                key={option.value}
                className="cursor-pointer rounded-lg border p-4 transition-colors"
                style={{
                  background: selected ? 'var(--accent-faint)' : 'var(--bg-0)',
                  borderColor: selected ? 'var(--accent)' : 'var(--border-subtle)',
                  color: 'var(--fg)',
                }}
              >
                <input
                  type="radio"
                  name="theme"
                  value={option.value}
                  checked={selected}
                  onChange={() => setTheme(option.value)}
                  className="sr-only"
                />
                <div className="text-sm font-semibold">{option.label}</div>
                <div className="mt-1 text-xs" style={{ color: 'var(--fg-dim)' }}>
                  {option.description}
                </div>
              </label>
            )
          })}
        </div>
      </section>

      <section
        className="rounded-lg border p-5"
        style={{ background: 'var(--bg-1)', borderColor: 'var(--border-subtle)' }}
        data-testid="profile-sound"
      >
        <div className="mb-4 flex items-center gap-2">
          {soundEnabled ? (
            <Volume2 size={15} style={{ color: 'var(--fg-dim)' }} />
          ) : (
            <VolumeX size={15} style={{ color: 'var(--fg-dim)' }} />
          )}
          <h2 className="text-base font-semibold" style={{ color: 'var(--fg)' }}>
            Звуковые уведомления
          </h2>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm" style={{ color: 'var(--fg-dim)' }}>
            Короткий сигнал в открытом приложении при появлении новой заявки.
          </p>
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => playNotificationSound(true)}
              data-testid="sound-preview"
            >
              Прослушать
            </Button>
            <Toggle
              checked={soundEnabled}
              onChange={handleSoundToggle}
              label={soundEnabled ? 'Включено' : 'Выключено'}
              ariaLabel="Звуковые уведомления"
              data-testid="sound-toggle"
            />
          </div>
        </div>
      </section>

      <section
        className="rounded-lg border p-5"
        style={{ background: 'var(--bg-1)', borderColor: 'var(--border-subtle)' }}
        data-testid="profile-activity"
      >
        <div className="mb-4 flex items-center gap-2">
          <Activity size={15} style={{ color: 'var(--fg-dim)' }} />
          <h2 className="text-base font-semibold" style={{ color: 'var(--fg)' }}>
            История действий
          </h2>
        </div>

        {activityQuery.isLoading ? (
          <div className="flex justify-center py-4">
            <Spinner className="h-5 w-5" />
          </div>
        ) : activity.length === 0 ? (
          <div className="text-sm" style={{ color: 'var(--fg-faint)' }}>
            История пуста: ваших действий пока не зафиксировано.
          </div>
        ) : (
          <ol className="flex flex-col gap-2" data-testid="activity-list">
            {activity.map(entry => (
              <ActivityRow key={entry.id} entry={entry} />
            ))}
            <InfiniteScrollSentinel
              hasMore={Boolean(activityQuery.hasNextPage)}
              loading={activityQuery.isFetchingNextPage}
              onLoadMore={() => void activityQuery.fetchNextPage()}
            />
          </ol>
        )}
      </section>
    </div>
  )
}

function ActivityRow({ entry }: { entry: ActivityLogEntry }) {
  const dt = new Date(entry.occurred_at)
  const dateStr = dt.toLocaleString('ru', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  const targetLabel = entry.target_summary
    ? `${TARGET_KIND_LABELS[entry.target_summary.kind] ?? entry.target_summary.kind} #${entry.target_summary.id}`
    : null

  return (
    <li
      className="rounded-md border px-3 py-2 text-sm"
      style={{ background: 'var(--bg-0)', borderColor: 'var(--border-subtle)', color: 'var(--fg)' }}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium">
          {EVENT_LABELS[entry.event_type] ?? entry.event_type}
          {targetLabel && (
            <span className="ml-1" style={{ color: 'var(--fg-dim)' }}>
              {' · '}
              {targetLabel}
            </span>
          )}
        </span>
        <span
          className="whitespace-nowrap text-xs"
          style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}
        >
          {dateStr}
        </span>
      </div>
      {(entry.description || entry.comment) && (
        <div className="mt-1 text-xs" style={{ color: 'var(--fg-dim)' }}>
          {entry.description || entry.comment}
        </div>
      )}
    </li>
  )
}

const TARGET_KIND_LABELS: Record<string, string> = {
  application: 'Заявка',
  panel: 'Панель',
  display: 'Экран',
  departure: 'Выезд',
  cell: 'Ячейка',
}

const EVENT_LABELS: Record<string, string> = {
  'application.created': 'Создана заявка',
  'application.transition': 'Смена статуса заявки',
  'application.archived': 'Заявка в архиве',
  'application.deleted': 'Заявка удалена',
  'panel.condition_changed': 'Смена состояния панели',
  'panel.moved': 'Перемещение панели',
  'panel.removed': 'Снятие панели',
  'panel.installed': 'Установка панели',
  'departure.created': 'Создан выезд',
  'departure.completed': 'Выезд завершён',
}

function InfoRow({
  label,
  value,
  icon,
}: {
  label: string
  value: string
  icon?: React.ReactNode
}) {
  return (
    <div
      className="rounded-md border px-3 py-2"
      style={{ background: 'var(--bg-0)', borderColor: 'var(--border-subtle)' }}
    >
      <div
        className="mb-1 flex items-center gap-1 text-xs uppercase tracking-wider"
        style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}
      >
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-sm" style={{ color: 'var(--fg)' }}>
        {value}
      </div>
    </div>
  )
}
