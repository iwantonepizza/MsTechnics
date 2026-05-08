import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'

export function useStorage(kind: 'lamels' | 'hubs' | 'wires', displaySlug?: string | null) {
  return useQuery({
    queryKey: ['storage', kind, displaySlug],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (displaySlug) params.display = displaySlug
      const res = await apiClient.get<{ results: any[] }>(`/storage/${kind}/`, { params })
      return res.data.results ?? res.data
    },
    staleTime: 60_000,
  })
}
