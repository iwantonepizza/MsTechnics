import { Loader2 } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

export function Spinner({ className, size = 16 }: { className?: string; size?: number }) {
  return (
    <Loader2
      size={size}
      className={cn('animate-spin', className)}
      style={{ color: 'var(--fg-mute)' }}
    />
  )
}
