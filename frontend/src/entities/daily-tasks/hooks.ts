import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { PaginatedResponse } from '@/shared/api/types'

export type DailyTaskStatus = 'not_ready' | 'ready' | 'deadline' | 'done' | 'undone'

export interface DailyTask {
  id: number
  name: string
  description: string
  status: DailyTaskStatus
  start_time: string | null
  end_time: string | null
  link: string
  city_id: number
  city_name: string
  available: boolean
}

export function useDailyTasks(cityId?: number | null, enabled = true) {
  return useQuery({
    queryKey: ['daily-tasks', cityId ?? null],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<DailyTask>>('/daily-tasks/', {
        params: { city: cityId ?? undefined },
      })
      return res.data.results ?? []
    },
    enabled,
    staleTime: 30_000,
  })
}

export function useCompleteDailyTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await apiClient.post<DailyTask>(`/daily-tasks/${id}/complete/`)
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['daily-tasks'] })
    },
  })
}
