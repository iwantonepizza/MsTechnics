import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
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

export interface ActivityLogFilter {
  display?: string
  panel?: number | null
  cell?: number | null
  kind?: string
  /** T-8-062: точный набор event_type через запятую */
  eventTypes?: string
  /** ISO-дата нижней границы (T-8-020) */
  since?: string
  /** T-8-020: общая лента (без таргета) — включается тумблером show_activity_feed */
  feed?: boolean
  limit?: number
  enabled?: boolean
}

function activityLogEnabled(filter: ActivityLogFilter) {
  return (
    filter.enabled ??
    (
      !!filter.display ||
      !!filter.kind ||
      !!filter.eventTypes ||
      filter.panel != null ||
      filter.cell != null ||
      !!filter.feed
    )
  )
}

async function fetchActivityLog(filter: ActivityLogFilter, cursor?: string) {
  const res = await apiClient.get<PaginatedResponse<ActivityLogEntry>>('/activity-log/', {
    params: {
      display: filter.display,
      panel: filter.panel ?? undefined,
      cell: filter.cell ?? undefined,
      kind: filter.kind,
      event_types: filter.eventTypes,
      since: filter.since,
      limit: filter.limit ?? 30,
      cursor,
    },
  })
  return res.data
}

export function useActivityLog(filter: ActivityLogFilter = {}) {
  return useQuery({
    queryKey: ['activity-log', filter],
    queryFn: async () => (await fetchActivityLog(filter)).results ?? [],
    enabled: activityLogEnabled(filter),
    staleTime: 30_000,
  })
}

export function useInfiniteActivityLog(filter: ActivityLogFilter = {}) {
  const query = useInfiniteQuery({
    queryKey: ['activity-log', 'infinite', filter],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => fetchActivityLog(filter, pageParam),
    getNextPageParam: lastPage => lastPage.next_cursor ?? undefined,
    enabled: activityLogEnabled(filter),
    staleTime: 30_000,
  })

  return {
    ...query,
    entries: query.data?.pages.flatMap(page => page.results ?? []) ?? [],
  }
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

export function useInfiniteMyActivity(username: string | undefined, limit: number = 50) {
  const query = useInfiniteQuery({
    queryKey: ['my-activity', 'infinite', username, limit],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const res = await apiClient.get<PaginatedResponse<ActivityLogEntry>>('/activity-log/', {
        params: { actor: username, limit, cursor: pageParam },
      })
      return res.data
    },
    getNextPageParam: lastPage => lastPage.next_cursor ?? undefined,
    enabled: !!username,
    staleTime: 30_000,
  })
  return {
    ...query,
    entries: query.data?.pages.flatMap(page => page.results ?? []) ?? [],
  }
}
