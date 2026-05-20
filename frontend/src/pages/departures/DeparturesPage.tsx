import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, Car, CheckCircle } from 'lucide-react'
import { toast } from 'sonner'

import { apiClient } from '@/shared/api/client'
import type { DepartureListItem, PaginatedResponse } from '@/shared/api/types'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Spinner } from '@/shared/ui/Spinner'
import { formatDate, getErrorMessage } from '@/shared/lib/utils'

const STATUS_VARIANTS: Record<string, 'warn' | 'ok' | 'neutral' | 'err'> = {
  created: 'warn',
  completed: 'ok',
  archived: 'neutral',
  deleted: 'err',
}

const TABS = [
  { value: '', label: 'Все' },
  { value: 'created', label: 'Создан' },
  { value: 'completed', label: 'Выполнен' },
  { value: 'archived', label: 'Архив' },
]

export function DeparturesPage() {
  const qc = useQueryClient()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<string>('')
  const selectedDepartureId = Number(searchParams.get('departure_id') ?? '')

  const { data, isLoading } = useQuery({
    queryKey: ['departures', status],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<DepartureListItem>>('/departures/', {
        params: status ? { status } : undefined,
      })
      return res.data
    },
  })

  const complete = useMutation({
    mutationFn: (id: number) => apiClient.post(`/departures/${id}/complete/`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['departures'] })
      toast.success('Выезд завершён')
    },
    onError: error => toast.error(getErrorMessage(error)),
  })

  const archive = useMutation({
    mutationFn: (id: number) => apiClient.post(`/departures/${id}/archive/`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['departures'] })
      toast.success('Выезд архивирован')
    },
    onError: error => toast.error(getErrorMessage(error)),
  })

  const departures = data?.results ?? []

  useEffect(() => {
    if (!Number.isInteger(selectedDepartureId) || selectedDepartureId <= 0) return

    window.setTimeout(() => {
      document.getElementById(`departure-${selectedDepartureId}`)?.scrollIntoView({
        block: 'center',
        behavior: 'smooth',
      })
    }, 0)
  }, [selectedDepartureId, departures.length])

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold" style={{ color: 'var(--fg)' }}>
            Выезды
          </h1>
          <p className="mt-0.5 text-sm" style={{ color: 'var(--fg-mute)' }}>
            Управление выездными бригадами
          </p>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Фильтр выездов"
        className="mb-4 inline-flex rounded-md p-0.5"
        style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)' }}
      >
        {TABS.map(tab => {
          const active = status === tab.value
          return (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setStatus(tab.value)}
              className="h-7 rounded-sm px-3 text-xs font-medium transition-colors"
              style={{
                background: active ? 'var(--bg-0)' : 'transparent',
                color: active ? 'var(--fg)' : 'var(--fg-mute)',
                boxShadow: active ? '0 1px 2px rgba(0,0,0,0.06)' : undefined,
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : departures.length === 0 ? (
        <EmptyState icon={<Car size={24} />} title="Выездов нет" />
      ) : (
        <div className="space-y-2">
          {departures.map(dep => {
            const selected = dep.id === selectedDepartureId
            return (
              <div
                key={dep.id}
                id={`departure-${dep.id}`}
                className="flex items-center gap-4 rounded-xl border px-4 py-3 transition-colors"
                style={{
                  background: selected ? 'var(--accent-faint)' : 'var(--bg-1)',
                  borderColor: selected ? 'var(--accent-edge)' : 'var(--border-subtle)',
                }}
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span
                      className="truncate text-sm font-medium"
                      style={{ color: 'var(--fg)' }}
                    >
                      {dep.description ?? `Выезд #${dep.id}`}
                    </span>
                    {dep.status && (
                      <Badge
                        label={dep.status.description}
                        variant={STATUS_VARIANTS[dep.status.name] ?? 'neutral'}
                      />
                    )}
                  </div>
                  <div
                    className="flex flex-wrap items-center gap-3 text-xs"
                    style={{ color: 'var(--fg-mute)' }}
                  >
                    {dep.executor && (
                      <span>
                        {dep.executor.first_name} {dep.executor.last_name}
                      </span>
                    )}
                    {dep.time_start && <span>Начало: {formatDate(dep.time_start)}</span>}
                    {dep.time_updated && <span>Обновлено: {formatDate(dep.time_updated)}</span>}
                  </div>
                </div>

                <div className="flex flex-shrink-0 items-center gap-1.5">
                  {dep.status?.name === 'created' && (
                    <Button
                      size="sm"
                      variant="primary"
                      icon={<CheckCircle size={12} />}
                      loading={complete.isPending}
                      onClick={() => complete.mutate(dep.id)}
                    >
                      Завершить
                    </Button>
                  )}
                  {dep.status?.name === 'completed' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={<Archive size={12} />}
                      loading={archive.isPending}
                      onClick={() => archive.mutate(dep.id)}
                    >
                      Архив
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
