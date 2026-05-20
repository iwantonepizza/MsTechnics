import { useEffect, useRef, useState } from 'react'
import { Bell, BellRing } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useInbox, type InboxItem } from '@/entities/notification/hooks'
import { formatRelative } from '@/shared/lib/utils'

const MAX_ITEMS = 10

export function NotificationBell() {
  const { items, unreadCount, isLoading, markAllSeen } = useInbox(MAX_ITEMS)
  const [open, setOpen] = useState(false)
  const [pulse, setPulse] = useState(false)
  const prevUnreadRef = useRef(unreadCount)
  const popoverRef = useRef<HTMLDivElement>(null)

  const handleToggle = () => {
    if (!open) markAllSeen()
    setOpen(current => !current)
  }

  useEffect(() => {
    if (!open) return
    const handler = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  useEffect(() => {
    if (unreadCount > prevUnreadRef.current && unreadCount > 0) {
      setPulse(true)
      const timeoutId = window.setTimeout(() => setPulse(false), 800)
      prevUnreadRef.current = unreadCount
      return () => window.clearTimeout(timeoutId)
    }
    prevUnreadRef.current = unreadCount
  }, [unreadCount])

  const Icon = unreadCount > 0 ? BellRing : Bell

  return (
    <div ref={popoverRef} className="relative">
      <button
        type="button"
        onClick={handleToggle}
        aria-label={`Уведомления${unreadCount > 0 ? ` (${unreadCount} новых)` : ''}`}
        className="icon-btn relative"
        data-testid="notification-bell-button"
      >
        <Icon
          size={16}
          style={{ color: 'var(--fg-mute)' }}
          className={pulse ? 'bell-pulse' : undefined}
        />
        {unreadCount > 0 && (
          <span
            data-testid="notification-bell-badge"
            className="absolute -right-0.5 -top-0.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-2xs font-semibold"
            style={{
              background: 'var(--err)',
              color: 'var(--err-ink)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          data-testid="notification-bell-popover"
          className="absolute right-0 mt-1 w-80 rounded-md shadow-lg"
          style={{
            background: 'var(--bg-1)',
            border: '1px solid var(--border)',
            zIndex: 50,
          }}
        >
          <div
            className="flex items-center justify-between px-3 py-2 text-xs"
            style={{
              borderBottom: '1px solid var(--border-subtle)',
              color: 'var(--fg-mute)',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
            }}
          >
            <span>Уведомления</span>
            <span>{items.length}</span>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {isLoading ? (
              <div className="p-4 text-center text-xs" style={{ color: 'var(--fg-faint)' }}>
                Загрузка...
              </div>
            ) : items.length === 0 ? (
              <div className="p-4 text-center text-xs" style={{ color: 'var(--fg-faint)' }}>
                Пока пусто
              </div>
            ) : (
              <ul className="divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
                {items.map(item => (
                  <li key={item.id}>
                    <NotificationRow item={item} onAnyClick={() => setOpen(false)} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function NotificationRow({
  item,
  onAnyClick,
}: {
  item: InboxItem
  onAnyClick: () => void
}) {
  const href = buildDeepLink(item)
  const className = 'block px-3 py-2 text-sm transition-colors hover:bg-bg-2'
  const style: React.CSSProperties = { color: 'var(--fg)' }
  const content = (
    <>
      <div className="leading-snug">{item.rendered_text}</div>
      <div
        className="mt-1 flex items-center gap-2 text-2xs"
        style={{ color: 'var(--fg-mute)' }}
      >
        <span style={{ fontFamily: 'var(--font-mono)' }}>
          {formatRelative(item.created_at)}
        </span>
        {item.delivered_via && (
          <>
            <span>·</span>
            <span>{item.delivered_via}</span>
          </>
        )}
      </div>
    </>
  )

  if (href) {
    return (
      <Link
        to={href}
        onClick={onAnyClick}
        className={className}
        style={style}
        data-testid={`notification-row-${item.id}`}
      >
        {content}
      </Link>
    )
  }

  return (
    <div className={className} style={style} data-testid={`notification-row-${item.id}`}>
      {content}
    </div>
  )
}

function buildDeepLink(item: InboxItem): string | null {
  if (item.deep_link_path) return item.deep_link_path
  if (!item.target_kind || !item.target_id) return null

  switch (item.target_kind) {
    case 'application':
      return `/control?app_id=${item.target_id}`
    case 'departure':
      return `/departures?departure_id=${item.target_id}`
    case 'panel':
      return `/zip?panel_id=${item.target_id}`
    default:
      return null
  }
}
