import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { GlobalSearchResponse } from '@/shared/api/types'

export function useGlobalSearch(query: string, limit = 8, enabled = true) {
  return useQuery({
    queryKey: ['global-search', query, limit],
    queryFn: async () => {
      const res = await apiClient.get<GlobalSearchResponse>('/search/', {
        params: { q: query, limit },
      })
      return res.data
    },
    enabled: enabled && query.length >= 2,
    staleTime: 30_000,
  })
}
