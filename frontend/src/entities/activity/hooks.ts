import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { PaginatedResponse } from '@/shared/api/types'

export function useActivityLog(filter: { display?: string; kind?: string } = {}) {
  return useQuery({
    queryKey: ['activity-log', filter],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<any>>('/activity-log/', {
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
