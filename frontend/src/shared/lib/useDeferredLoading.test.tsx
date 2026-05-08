import { renderHook, act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useDeferredLoading } from './useDeferredLoading'

describe('useDeferredLoading', () => {
  it('delays loading indicator until threshold', () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(({ loading }) => useDeferredLoading(loading, 300), {
      initialProps: { loading: false },
    })

    expect(result.current).toBe(false)

    rerender({ loading: true })
    expect(result.current).toBe(false)

    act(() => vi.advanceTimersByTime(299))
    expect(result.current).toBe(false)

    act(() => vi.advanceTimersByTime(1))
    expect(result.current).toBe(true)

    rerender({ loading: false })
    expect(result.current).toBe(false)
    vi.useRealTimers()
  })
})
