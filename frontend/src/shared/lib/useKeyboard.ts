import { useEffect } from 'react'

export type ShortcutMap = Record<string, () => void>

function eventKey(event: KeyboardEvent) {
  const key = event.key.length === 1 ? event.key.toUpperCase() : event.key
  return `${event.ctrlKey || event.metaKey ? 'Mod+' : ''}${event.shiftKey ? 'Shift+' : ''}${key}`
}

export function useKeyboard(shortcuts: ShortcutMap, enabled = true) {
  useEffect(() => {
    if (!enabled) return

    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable
      ) {
        return
      }

      const callback = shortcuts[eventKey(event)] ?? shortcuts[event.key] ?? shortcuts[event.key.toUpperCase()]
      if (!callback) return

      event.preventDefault()
      callback()
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [enabled, shortcuts])
}
