import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { PaginatedResponse } from '@/shared/api/types'

export interface ActivityLogEntry {
  id: number
  event_type: string
  target_kind: string | null
  target_id: number | null
  target_summary: { kind: string; id: number } | null
  actor_name: string | null
  occurred_at: string
  description: string | null
  comment: string | null
  payload: Record<string, unknown> | null
}

export function useActivityLog(filter: { display?: string; kind?: string } = {}) {
  return useQuery({
    queryKey: ['activity-log', filter],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ActivityLogEntry>>('/activity-log/', {
        params: {
          display: filter.display,
          kind: filter.kind,
          limit: 30,
        },
      })
      return res.data.results ?? []
    },
    enabled: !!filter.display || !!filter.kind,
    staleTime: 30_000,
  })
}

/**
 * useMyActivity — личная история действий текущего пользователя (T-7-014, P2).
 *
 * Использует существующий endpoint `/api/v1/activity-log/?actor=<username>&limit=<n>`.
 * Backend (apps/interface/api/v1/activity/views.py) фильтрует по `actor_name`.
 */
export function useMyActivity(username: string | undefined, limit: number = 50) {
  return useQuery({
    queryKey: ['my-activity', username, limit],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ActivityLogEntry>>('/activity-log/', {
        params: { actor: username, limit },
      })
      return res.data.results ?? []
    },
    enabled: !!username,
    staleTime: 30_000,
  })
}
