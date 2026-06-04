import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/utils'

const DOT_SIZES = [4, 6, 5, 8, 4, 7, 4, 9, 5, 7, 5, 8, 4, 6, 4]
const DEFAULT_LABELS = ['Загрузка', 'Суперсимметрия']

export function LoadingWave({
  labels = DEFAULT_LABELS,
  visual,
  className,
}: {
  labels?: string[]
  visual?: ReactNode
  className?: string
}) {
  const [labelIndex, setLabelIndex] = useState(0)

  useEffect(() => {
    if (labels.length < 2) return
    const interval = window.setInterval(() => {
      setLabelIndex(index => (index + 1) % labels.length)
    }, 1800)
    return () => window.clearInterval(interval)
  }, [labels])

  return (
    <div className={cn('loading-wave', className)} role="status" aria-live="polite">
      {visual ? (
        <div className="loading-wave__visual" aria-hidden="true">{visual}</div>
      ) : (
        <div className="loading-wave__dots" aria-hidden="true">
          {DOT_SIZES.map((size, index) => (
            <span
              key={index}
              className="loading-wave__dot"
              style={
                {
                  '--loading-dot-index': index,
                  '--loading-dot-size': `${size}px`,
                } as React.CSSProperties
              }
            />
          ))}
        </div>
      )}
      <span className="loading-wave__label">{labels[labelIndex] ?? 'Загрузка'}</span>
    </div>
  )
}
