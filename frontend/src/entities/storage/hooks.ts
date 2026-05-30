import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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

/**
 * T-8-063: изменение расходника (количество и/или фото).
 * Бэкенд: PATCH /storage/<kind>/<id>/ (generic ModelViewSet).
 * При передаче `photo` уходит multipart, иначе — JSON.
 */
export function useUpdateStorageItem(kind: StorageKind) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, count, photo }: { id: number; count?: number; photo?: File }) => {
      let body: FormData | Record<string, unknown>
      let headers: Record<string, string> | undefined
      if (photo) {
        const form = new FormData()
        if (count != null) form.append('count', String(count))
        form.append('photo', photo)
        body = form
        headers = { 'Content-Type': 'multipart/form-data' }
      } else {
        body = { count }
      }
      const res = await apiClient.patch<StorageItem>(`/storage/${kind}/${id}/`, body, { headers })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['storage', kind] })
    },
  })
}
