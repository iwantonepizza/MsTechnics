/**
 * T-4-032: Двухпороговая загрузка — <300ms ничего, >300ms skeleton.
 * Устраняет "мигание" skeleton при быстрых ответах.
 */
import { useEffect, useState } from 'react'

export function useDeferredLoading(isLoading: boolean, threshold = 300): boolean {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!isLoading) {
      setShow(false)
      return
    }
    const t = window.setTimeout(() => setShow(true), threshold)
    return () => window.clearTimeout(t)
  }, [isLoading, threshold])

  return show
}
