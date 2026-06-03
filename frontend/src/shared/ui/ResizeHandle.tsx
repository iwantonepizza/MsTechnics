import { GripHorizontal, GripVertical } from 'lucide-react'
import type { PointerEventHandler } from 'react'

import { cn } from '@/shared/lib/utils'

export function ResizeHandle({
  orientation,
  label,
  className,
  onPointerDown,
  testId,
}: {
  orientation: 'vertical' | 'horizontal'
  label: string
  className?: string
  onPointerDown: PointerEventHandler<HTMLButtonElement>
  testId?: string
}) {
  const Icon = orientation === 'vertical' ? GripVertical : GripHorizontal

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn('resize-handle', `resize-handle-${orientation}`, className)}
      onPointerDown={onPointerDown}
      data-testid={testId}
    >
      <Icon size={14} />
    </button>
  )
}
