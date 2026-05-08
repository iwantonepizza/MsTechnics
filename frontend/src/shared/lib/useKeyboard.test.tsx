import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useKeyboard } from './useKeyboard'

describe('useKeyboard', () => {
  it('calls shortcut handler outside form fields', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboard({ A: handler }))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }))

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('ignores shortcuts inside inputs', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboard({ A: handler }))
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true }))

    expect(handler).not.toHaveBeenCalled()
    input.remove()
  })

  it('supports Mod+Enter combos', () => {
    const handler = vi.fn()
    renderHook(() => useKeyboard({ 'Mod+Enter': handler }))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))

    expect(handler).toHaveBeenCalledTimes(1)
  })
})
