import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { AlarmEvent, DisplayListItem, DisplayDetail } from '@/shared/api/types'

export function useDisplays(citySlug?: string) {
  return useQuery({
    queryKey: ['displays', citySlug],
    queryFn: async () => {
      const res = await apiClient.get<{ results: DisplayListItem[] }>('/displays/', {
        params: citySlug ? { city: citySlug } : undefined,
      })
      return res.data.results ?? res.data
    },
    staleTime: 60_000,
  })
}

export function useDisplayDetail(slug: string | null) {
  return useQuery({
    queryKey: ['display', slug],
    queryFn: async () => {
      const res = await apiClient.get<DisplayDetail>(`/displays/${slug}/`)
      return res.data
    },
    enabled: !!slug,
    staleTime: 15_000,
  })
}

export function useDisplayAlarms(slug: string | null, resolved = false) {
  return useQuery({
    queryKey: ['display-alarms', slug, resolved],
    queryFn: async () => {
      const res = await apiClient.get<AlarmEvent[]>(`/displays/${slug}/alarms/`, {
        params: { resolved: String(resolved), limit: 50 },
      })
      return Array.isArray(res.data) ? res.data : (res.data as { results?: AlarmEvent[] }).results ?? []
    },
    enabled: !!slug,
    staleTime: 30_000,
  })
}

export function useCities() {
  return useQuery({
    queryKey: ['cities'],
    queryFn: async () => {
      const res = await apiClient.get<{ results: any[] }>('/cities/')
      return res.data.results ?? res.data
    },
    staleTime: 5 * 60_000,
  })
}
