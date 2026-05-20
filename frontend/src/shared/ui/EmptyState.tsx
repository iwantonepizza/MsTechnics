import { Inbox } from 'lucide-react'

import { cn } from '@/shared/lib/utils'

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const iconEl =
    icon === undefined ? (
      <Inbox size={24} />
    ) : typeof icon === 'string' ? (
      <span className="text-3xl leading-none">{icon}</span>
    ) : (
      icon
    )

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 py-12 text-center',
        className,
      )}
    >
      <span
        className="mb-1 inline-flex items-center justify-center"
        style={{ color: 'var(--fg-mute)' }}
      >
        {iconEl}
      </span>
      <p
        className="text-sm font-medium"
        style={{ color: 'var(--fg-dim)' }}
      >
        {title}
      </p>
      {description && (
        <p
          className="max-w-xs text-xs"
          style={{ color: 'var(--fg-mute)' }}
        >
          {description}
        </p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
