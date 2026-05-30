import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'

export interface DisplayNote {
  id: number
  text: string
  author_name: string
  department: string
  created_at: string
}

export function useDisplayNotes(slug: string | undefined) {
  return useQuery({
    queryKey: ['display-notes', slug],
    queryFn: async () => {
      const res = await apiClient.get<DisplayNote[]>(`/displays/${slug}/notes/`)
      return res.data ?? []
    },
    enabled: !!slug,
    staleTime: 30_000,
  })
}

export function useAddDisplayNote(slug: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (text: string) => {
      const res = await apiClient.post<DisplayNote>(`/displays/${slug}/notes/`, { text })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['display-notes', slug] })
    },
  })
}
