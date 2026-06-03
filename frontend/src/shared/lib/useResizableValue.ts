import { useCallback, useEffect, useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function readStoredValue(storageKey: string, defaultValue: number, min: number, max: number) {
  try {
    const raw = window.localStorage.getItem(storageKey)
    const parsed = raw == null ? NaN : Number(raw)
    return Number.isFinite(parsed) ? clamp(parsed, min, max) : defaultValue
  } catch {
    return defaultValue
  }
}

export function useResizableValue({
  storageKey,
  defaultValue,
  min,
  max,
}: {
  storageKey: string
  defaultValue: number
  min: number
  max: number
}) {
  const [value, setValue] = useState(() => readStoredValue(storageKey, defaultValue, min, max))

  const setClampedValue = useCallback(
    (nextValue: number) => {
      setValue(clamp(nextValue, min, max))
    },
    [max, min],
  )

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, String(value))
    } catch {
      // Ignore private-mode/localStorage issues.
    }
  }, [storageKey, value])

  return [value, setClampedValue] as const
}

export function useResizeDrag({
  value,
  setValue,
  axis,
  direction = 1,
  min,
  max,
}: {
  value: number
  setValue: (value: number) => void
  axis: 'x' | 'y'
  direction?: 1 | -1
  min: number
  max: number
}) {
  const valueRef = useRef(value)

  useEffect(() => {
    valueRef.current = value
  }, [value])

  return useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      if (event.button !== 0) {
        return
      }

      const startPointer = axis === 'x' ? event.clientX : event.clientY
      const startValue = valueRef.current
      const cursor = axis === 'x' ? 'col-resize' : 'row-resize'
      const previousCursor = document.body.style.cursor
      const previousUserSelect = document.body.style.userSelect

      document.body.style.cursor = cursor
      document.body.style.userSelect = 'none'

      const handlePointerMove = (moveEvent: PointerEvent) => {
        const currentPointer = axis === 'x' ? moveEvent.clientX : moveEvent.clientY
        const delta = (currentPointer - startPointer) * direction
        setValue(clamp(startValue + delta, min, max))
      }

      const handlePointerUp = () => {
        document.body.style.cursor = previousCursor
        document.body.style.userSelect = previousUserSelect
        window.removeEventListener('pointermove', handlePointerMove)
        window.removeEventListener('pointerup', handlePointerUp)
      }

      window.addEventListener('pointermove', handlePointerMove)
      window.addEventListener('pointerup', handlePointerUp)
    },
    [axis, direction, max, min, setValue],
  )
}
