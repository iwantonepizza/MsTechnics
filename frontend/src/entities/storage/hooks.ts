import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { StorageItem } from '@/shared/api/types'

export type StorageKind = 'lamels' | 'hubs' | 'wires' | 'power-blocks' | 'connectors'

export function useStorage(kind: StorageKind, displaySlug?: string | null) {
  return useQuery<StorageItem[]>({
    queryKey: ['storage', kind, displaySlug],
    queryFn: async () => {
      const res = await apiClient.get<{ results: StorageItem[] }>(`/storage/${kind}/`)
      return res.data.results ?? res.data
    },
    staleTime: 60_000,
  })
}
