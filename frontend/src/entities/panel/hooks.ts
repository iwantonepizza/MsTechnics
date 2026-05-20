import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { Panel, PaginatedResponse } from '@/shared/api/types'

export function usePanels(filter: { department?: string; display?: string | null } = {}) {
  return useQuery({
    queryKey: ['panels', filter],
    queryFn: async () => {
      const params: Record<string, string | undefined> = {}
      if (filter.department) params.department = filter.department
      if (filter.display) params.display = filter.display
      const res = await apiClient.get<PaginatedResponse<Panel>>('/panels/', { params })
      return res.data.results ?? []
    },
    staleTime: 30_000,
  })
}

export function usePanel(id: number | null) {
  return useQuery({
    queryKey: ['panel', id],
    queryFn: () => apiClient.get<Panel>(`/panels/${id}/`).then(r => r.data),
    enabled: !!id,
  })
}

export function useChangeDepartment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, department, comment }: { id: number; department: string; comment?: string }) =>
      apiClient.post(`/panels/${id}/change-department/`, { department, comment }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['panels'] })
      qc.invalidateQueries({ queryKey: ['display'] })
    },
  })
}

export function useChangeCondition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, condition_id, comment }: { id: number; condition_id: number; comment?: string }) =>
      apiClient.patch(`/panels/${id}/`, { condition_id, comment }).then(r => r.data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['panels'] })
      qc.invalidateQueries({ queryKey: ['panel', vars.id] })
      qc.invalidateQueries({ queryKey: ['display'] })
      qc.invalidateQueries({ queryKey: ['activity-log'] })
    },
  })
}

export function useMoveToCell() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ panelId, cell_id, comment }: { panelId: number; cell_id: number; comment?: string }) =>
      apiClient.post(`/panels/${panelId}/move-to-cell/`, { cell_id, comment }).then(r => r.data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['panels'] })
      qc.invalidateQueries({ queryKey: ['panel', vars.panelId] })
      qc.invalidateQueries({ queryKey: ['display'] })
      qc.invalidateQueries({ queryKey: ['activity-log'] })
    },
  })
}

export function useRemovePanel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      new_condition,
      comment,
      application_id,
    }: {
      id: number
      new_condition?: string
      comment?: string
      application_id?: number
    }) =>
      apiClient.post(`/panels/${id}/remove/`, { new_condition, comment, application_id }).then(r => r.data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['panels'] })
      qc.invalidateQueries({ queryKey: ['panel', vars.id] })
      qc.invalidateQueries({ queryKey: ['display'] })
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['activity-log'] })
    },
  })
}

/**
 * useCreatePanel — T-7-035, Z7.
 * POST /api/v1/panels/ — admin/service создаёт новую панель.
 */
export function useCreatePanel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      name,
      display_id,
      condition_name,
      comment,
    }: {
      name: string
      display_id: number
      condition_name?: string
      comment?: string
    }) =>
      apiClient
        .post<Panel>('/panels/', { name, display_id, condition_name, comment })
        .then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['panels'] })
      qc.invalidateQueries({ queryKey: ['display'] })
      qc.invalidateQueries({ queryKey: ['activity-log'] })
    },
  })
}

/**
 * useDeletePanel — T-7-036, Z8. Admin-only на бэкенде.
 * DELETE /api/v1/panels/{id}/ — 204 при успехе, 4xx с DomainError если установлена/есть заявка.
 */
export function useDeletePanel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiClient.delete(`/panels/${id}/`).then(() => id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['panels'] })
      qc.invalidateQueries({ queryKey: ['display'] })
      qc.invalidateQueries({ queryKey: ['activity-log'] })
    },
  })
}

export function usePanelHistory(id: number | null) {
  return useQuery({
    queryKey: ['panel-history', id],
    queryFn: () => apiClient.get<{ results: any[] }>(`/panels/${id}/history/`).then(r => r.data.results),
    enabled: !!id,
  })
}
