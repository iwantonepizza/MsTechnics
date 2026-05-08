import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'

export interface Executor {
  id: number
  first_name: string
  last_name: string
  executor_role: string
  phone_number: string | null
  telegram_id: string | null
}

export function useExecutors(enabled = true) {
  return useQuery({
    queryKey: ['executors'],
    queryFn: async () => {
      const res = await apiClient.get<{ results?: Executor[] } | Executor[]>('/executors/')
      return Array.isArray(res.data) ? res.data : (res.data.results ?? [])
    },
    enabled,
    staleTime: 5 * 60_000,
  })
}
