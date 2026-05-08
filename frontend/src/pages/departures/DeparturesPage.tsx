import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, CheckCircle, Archive, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/Button'
import { Badge } from '@/shared/ui/Badge'
import { Spinner } from '@/shared/ui/Spinner'
import { EmptyState } from '@/shared/ui/EmptyState'
import { cn, formatDate, getErrorMessage } from '@/shared/lib/utils'
import { apiClient } from '@/shared/api/client'
import type { DepartureListItem, PaginatedResponse } from '@/shared/api/types'

const STATUS_COLORS: Record<string, string> = {
  created:   '#fbbf24',
  completed: '#22c55e',
  archived:  '#71717a',
  deleted:   '#ef4444',
}

export function DeparturesPage() {
  const qc = useQueryClient()
  const [status, setStatus] = useState<string>('')

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
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departures'] }); toast.success('Выезд завершён') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })

  const archive = useMutation({
    mutationFn: (id: number) => apiClient.post(`/departures/${id}/archive/`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['departures'] }); toast.success('Выезд архивирован') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })

  const departures = data?.results ?? []

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">Выезды</h1>
          <p className="text-sm text-text-muted mt-0.5">Управление выездными бригадами</p>
        </div>
      </div>

      {/* Фильтр */}
      <div className="flex gap-1.5 mb-4">
        {[
          { value: '', label: 'Все' },
          { value: 'created', label: 'Создан' },
          { value: 'completed', label: 'Выполнен' },
          { value: 'archived', label: 'Архив' },
        ].map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setStatus(value)}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-medium transition-colors',
              status === value
                ? 'bg-surface-3 text-text-primary'
                : 'text-text-muted hover:text-text-primary hover:bg-surface-2',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : departures.length === 0 ? (
        <EmptyState icon="🚗" title="Выездов нет" />
      ) : (
        <div className="space-y-2">
          {departures.map(dep => (
            <div
              key={dep.id}
              className="flex items-center gap-4 px-4 py-3 bg-surface-2 border border-surface-3 rounded-xl"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium truncate">
                    {dep.description ?? `Выезд #${dep.id}`}
                  </span>
                  {dep.status && (
                    <Badge
                      label={dep.status.description}
                      bgHex={STATUS_COLORS[dep.status.name] ?? '#888'}
                    />
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-text-muted">
                  {dep.executor && (
                    <span>{dep.executor.first_name} {dep.executor.last_name}</span>
                  )}
                  {dep.time_start && (
                    <span>Начало: {formatDate(dep.time_start)}</span>
                  )}
                  {dep.time_updated && (
                    <span>Обновлено: {formatDate(dep.time_updated)}</span>
                  )}
                </div>
              </div>

              {/* Действия */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {dep.status?.name === 'created' && (
                  <Button
                    size="sm"
                    variant="primary"
                    loading={complete.isPending}
                    onClick={() => complete.mutate(dep.id)}
                  >
                    <CheckCircle size={12} />
                    Завершить
                  </Button>
                )}
                {dep.status?.name === 'completed' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={archive.isPending}
                    onClick={() => archive.mutate(dep.id)}
                  >
                    <Archive size={12} />
                    Архив
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
