import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { ApplicationListItem, ApplicationDetail, ApplicationEvent, PaginatedResponse } from '@/shared/api/types'

export interface ApplicationsFilter {
  display?: string
  box?: string
  panel?: number
  cell?: number
  cursor?: string
  enabled?: boolean
}

export function useApplications(filter: ApplicationsFilter) {
  return useQuery({
    queryKey: ['applications', filter],
    queryFn: async () => {
      const params: Record<string, string | number | undefined> = {
        display: filter.display,
        box: filter.box ?? 'received',
        panel: filter.panel,
        cell: filter.cell,
        cursor: filter.cursor,
      }
      Object.keys(params).forEach(k => params[k] === undefined && delete params[k])
      const res = await apiClient.get<PaginatedResponse<ApplicationListItem>>('/applications/', { params })
      return res.data
    },
    enabled: filter.enabled ?? true,
  })
}

export function useInfiniteApplications(filter: ApplicationsFilter) {
  const query = useInfiniteQuery({
    queryKey: ['applications', 'infinite', filter],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const params: Record<string, string | number | undefined> = {
        display: filter.display,
        box: filter.box ?? 'received',
        panel: filter.panel,
        cell: filter.cell,
        cursor: pageParam,
      }
      Object.keys(params).forEach(k => params[k] === undefined && delete params[k])
      const res = await apiClient.get<PaginatedResponse<ApplicationListItem>>('/applications/', { params })
      return res.data
    },
    getNextPageParam: lastPage => lastPage.next_cursor ?? undefined,
    enabled: filter.enabled ?? true,
  })

  return {
    ...query,
    applications: query.data?.pages.flatMap(page => page.results ?? []) ?? [],
  }
}

export function useApplicationDetail(id: number | null) {
  return useQuery({
    queryKey: ['application', id],
    queryFn: async () => {
      const res = await apiClient.get<ApplicationDetail>(`/applications/${id}/`)
      return res.data
    },
    enabled: !!id,
  })
}

export function useApplicationEvents(id: number | null) {
  return useQuery({
    queryKey: ['application-events', id],
    queryFn: async () => {
      const res = await apiClient.get<{ results: ApplicationEvent[] }>(`/applications/${id}/events`)
      return res.data.results
    },
    enabled: !!id,
  })
}

export function useCreateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: {
      display_id: number; panel_id: number; cell_id: number
      comment: string; file?: File | null
    }) => {
      const form = new FormData()
      form.append('display_id', String(data.display_id))
      form.append('panel_id', String(data.panel_id))
      form.append('cell_id', String(data.cell_id))
      form.append('comment', data.comment)
      if (data.file) form.append('file', data.file)
      const res = await apiClient.post('/applications/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications'] }),
  })
}

export function useDeleteApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      await apiClient.delete(`/applications/${id}/`)
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['application', vars.id] })
      qc.invalidateQueries({ queryKey: ['application-events', vars.id] })
    },
  })
}

export function useTransitionApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id, target_state, comment, executor_id, file,
    }: {
      id: number; target_state: string; comment?: string; executor_id?: number; file?: File | null
    }) => {
      const form = new FormData()
      form.append('target_state', target_state)
      if (comment) form.append('comment', comment)
      if (executor_id) form.append('executor_id', String(executor_id))
      if (file) form.append('file', file)
      const res = await apiClient.post(`/applications/${id}/transition/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data
    },
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: ['applications'] })
      await qc.cancelQueries({ queryKey: ['application', vars.id] })

      const previousLists = qc.getQueriesData<PaginatedResponse<ApplicationListItem>>({ queryKey: ['applications'] })
      const previousDetail = qc.getQueryData<ApplicationDetail>(['application', vars.id])

      const patchStatus = <T extends ApplicationListItem | ApplicationDetail>(app: T): T => ({
        ...app,
        status: {
          ...app.status,
          name: vars.target_state,
          description: vars.target_state,
        },
      })

      previousLists.forEach(([key]) => {
        qc.setQueryData<PaginatedResponse<ApplicationListItem>>(key, old => {
          if (!old?.results) return old
          return {
            ...old,
            results: old.results.map(app => app.id === vars.id ? patchStatus(app) : app),
          }
        })
      })

      qc.setQueryData<ApplicationDetail>(['application', vars.id], old => old ? patchStatus(old) : old)

      return { previousLists, previousDetail }
    },
    onError: (_error, vars, context) => {
      context?.previousLists?.forEach(([key, value]) => qc.setQueryData(key, value))
      if (context?.previousDetail) qc.setQueryData(['application', vars.id], context.previousDetail)
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['application', vars.id] })
      qc.invalidateQueries({ queryKey: ['application-events', vars.id] })
    },
    onSettled: (_data, _error, vars) => {
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['application', vars.id] })
      qc.invalidateQueries({ queryKey: ['application-events', vars.id] })
    },
  })
}
