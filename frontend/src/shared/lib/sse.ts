/**
 * shared/lib/sse.ts — T-4-030
 * SSE подписка на /api/v1/events/stream?token=<jwt>
 * Статус хранится в Zustand. При SSE-событии — инвалидируем TanStack Query.
 */
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { create } from 'zustand'

type SSEStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

interface SSEStore {
  status: SSEStatus
  setStatus: (s: SSEStatus) => void
}

const useSSEStore = create<SSEStore>(set => ({
  status: 'disconnected',
  setStatus: (status) => set({ status }),
}))

export const useSSEStatus = () => useSSEStore(s => s.status)

// Маппинг event_type → query keys для инвалидации
const EVENT_QUERY_MAP: Record<string, string[][]> = {
  'application_transition':     [['applications'], ['application']],
  'application.create':         [['applications']],
  'application.deleted':        [['applications']],
  'panel.condition_changed':    [['panels'], ['display']],
  'panel.removed':              [['panels'], ['display']],
  'panel_move':                 [['panels'], ['display']],
  'departure.created':          [['departures']],
  'departure.completed':        [['departures']],
  'departure.archived':         [['departures']],
  'display_panel_replace':      [['display'], ['panels']],
}

let _es: EventSource | null = null
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null

function connectSSE(token: string, setStatus: (s: SSEStatus) => void, invalidate: (keys: string[][]) => void) {
  if (_es) {
    _es.close()
    _es = null
  }
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer)
    _reconnectTimer = null
  }

  const url = `/api/v1/events/stream?token=${encodeURIComponent(token)}`
  setStatus('connecting')

  const es = new EventSource(url)
  _es = es

  es.onopen = () => setStatus('connected')

  es.onmessage = (e) => {
    try {
      const payload = JSON.parse(e.data)
      const eventType = payload?.event_type ?? 'unknown'
      const keys = EVENT_QUERY_MAP[eventType]
      if (keys) invalidate(keys)
    } catch { /* ignore malformed */ }
  }

  // Named events from backend
  Object.keys(EVENT_QUERY_MAP).forEach(eventType => {
    es.addEventListener(eventType, (e) => {
      const keys = EVENT_QUERY_MAP[eventType]
      if (keys) invalidate(keys)
    })
  })

  es.onerror = () => {
    es.close()
    _es = null
    setStatus('reconnecting')
    _reconnectTimer = setTimeout(() => {
      connectSSE(token, setStatus, invalidate)
    }, 5_000)
  }
}

export function useSSESubscription() {
  const qc = useQueryClient()
  const setStatus = useSSEStore(s => s.setStatus)

  useEffect(() => {
    // Токен читаем из auth store (через window.__authStore)
    const getToken = (): string | null => {
      try {
        return (window as any).__authStore?.getState?.()?.accessToken ?? null
      } catch { return null }
    }

    const token = getToken()
    if (!token) {
      setStatus('disconnected')
      return
    }

    const invalidate = (keys: string[][]) => {
      keys.forEach(key => qc.invalidateQueries({ queryKey: key }))
    }

    connectSSE(token, setStatus, invalidate)

    return () => {
      if (_es) { _es.close(); _es = null }
      if (_reconnectTimer) { clearTimeout(_reconnectTimer) }
      setStatus('disconnected')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
}
