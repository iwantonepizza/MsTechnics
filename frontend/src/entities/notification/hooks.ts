/**
 * useInbox — T-7-011. Inbox-уведомления для колокольчика в Header.
 *
 * Backend: GET /api/v1/notifications/inbox/?limit=20 → { results, count }.
 * Read-state — на клиенте: `last_seen_id` в localStorage. Это не требует
 * BC-breaking миграции Notification модели.
 */
import { useCallback, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'

export interface InboxItem {
  id: number
  rendered_text: string
  created_at: string
  status: 'sent' | 'pending' | 'failed' | 'skipped'
  delivered_via: string
  target_kind: string | null
  target_id: string | null
  deep_link_path: string | null
}

const LAST_SEEN_KEY = 'notifications.lastSeenId'

function readLastSeenId(): number {
  try {
    const raw = localStorage.getItem(LAST_SEEN_KEY)
    if (!raw) return 0
    const n = parseInt(raw, 10)
    return Number.isFinite(n) ? n : 0
  } catch {
    return 0
  }
}

function writeLastSeenId(id: number): void {
  try {
    localStorage.setItem(LAST_SEEN_KEY, String(id))
  } catch {
    /* private mode */
  }
}

export function useInbox(limit: number = 20) {
  const [lastSeenId, setLastSeenId] = useState<number>(() => readLastSeenId())

  const query = useQuery({
    queryKey: ['notifications-inbox', limit],
    queryFn: async () => {
      const res = await apiClient.get<{ results: InboxItem[]; count: number }>(
        '/notifications/inbox/',
        { params: { limit } },
      )
      return res.data.results ?? []
    },
    // Polling раз в 30s + SSE-инвалидация при application.create
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const items: InboxItem[] = query.data ?? []
  const maxId = useMemo(
    () => items.reduce((max, it) => (it.id > max ? it.id : max), 0),
    [items],
  )
  const unreadCount = useMemo(
    () => items.filter(it => it.id > lastSeenId).length,
    [items, lastSeenId],
  )

  const markAllSeen = useCallback(() => {
    if (maxId > lastSeenId) {
      writeLastSeenId(maxId)
      setLastSeenId(maxId)
    }
  }, [maxId, lastSeenId])

  return {
    items,
    unreadCount,
    isLoading: query.isLoading,
    refetch: query.refetch,
    markAllSeen,
  }
}
