import { cn } from '@/shared/lib/utils'

interface SkeletonProps {
  className?: string
  style?: React.CSSProperties
}

/** Использует .skeleton класс из tokens.css — автошиммер */
export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn('skeleton rounded-sm', className)}
      style={style}
      aria-hidden="true"
    />
  )
}

export function SkeletonList({ rows = 5, height = 'var(--h-row)' }: { rows?: number; height?: string }) {
  return (
    <div className="space-y-1.5 p-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} style={{ height, width: i % 3 === 0 ? '75%' : '100%' }} />
      ))}
    </div>
  )
}
