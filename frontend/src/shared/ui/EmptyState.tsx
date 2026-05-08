import { cn } from '@/shared/lib/utils'

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon = '📭', title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      <span className="text-4xl mb-3">{icon}</span>
      <p className="text-sm font-medium mb-1" style={{ color: 'var(--fg-dim)' }}>{title}</p>
      {description && <p className="text-xs mb-4" style={{ color: 'var(--fg-mute)' }}>{description}</p>}
      {action && action}
    </div>
  )
}
