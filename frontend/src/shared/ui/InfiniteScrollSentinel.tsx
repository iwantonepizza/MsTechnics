import { useEffect, useRef } from 'react'

import { Button } from '@/shared/ui/Button'

export function InfiniteScrollSentinel({
  hasMore,
  loading,
  onLoadMore,
}: {
  hasMore: boolean
  loading: boolean
  onLoadMore: () => void
}) {
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!hasMore || loading || !ref.current || typeof IntersectionObserver === 'undefined') {
      return
    }
    const observer = new IntersectionObserver(
      entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          onLoadMore()
        }
      },
      { rootMargin: '160px' },
    )
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [hasMore, loading, onLoadMore])

  if (!hasMore) {
    return null
  }

  return (
    <div ref={ref} className="flex justify-center py-2" data-testid="infinite-scroll-sentinel">
      <Button variant="ghost" size="sm" loading={loading} onClick={onLoadMore}>
        {loading ? 'Загрузка...' : 'Показать ещё'}
      </Button>
    </div>
  )
}
