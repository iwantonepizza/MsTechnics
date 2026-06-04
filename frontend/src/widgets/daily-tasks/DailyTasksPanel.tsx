import { useState } from 'react'
import { AlertTriangle, CheckSquare, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import { toast } from 'sonner'
import {
  useCompleteDailyTask,
  useDailyTasks,
  type DailyTask,
  type DailyTaskStatus,
} from '@/entities/daily-tasks/hooks'
import { SkeletonList } from '@/shared/ui/Skeleton'

const STATUS_META: Record<DailyTaskStatus, { label: string; color: string }> = {
  not_ready: { label: 'Закрыто', color: 'var(--fg-faint)' },
  ready: { label: 'Открыто', color: 'var(--info)' },
  deadline: { label: 'Дедлайн', color: 'var(--warn)' },
  done: { label: 'Выполнено', color: 'var(--ok)' },
  undone: { label: 'Просрочено', color: 'var(--err)' },
}

/**
 * T-8-035: список ежедневных задач.
 * monitoring — интерактив (клик открывает ссылку и засчитывает);
 * control — read-only прогресс.
 */
export function DailyTasksPanel({
  cityId,
  readOnly = false,
  defaultOpen = false,
}: {
  cityId: number | undefined
  readOnly?: boolean
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const scopedTasks = useDailyTasks(cityId)
  const shouldLoadFallback = Boolean(
    cityId != null && !scopedTasks.isLoading && (scopedTasks.data?.length ?? 0) === 0,
  )
  const fallbackTasks = useDailyTasks(null, shouldLoadFallback)
  const complete = useCompleteDailyTask()
  const data = shouldLoadFallback ? (fallbackTasks.data ?? []) : (scopedTasks.data ?? [])
  const isLoading = scopedTasks.isLoading || (shouldLoadFallback && fallbackTasks.isLoading)
  const isError = Boolean(shouldLoadFallback ? fallbackTasks.isError : scopedTasks.isError)

  const doneCount = data.filter(t => t.status === 'done').length

  const onTaskClick = async (task: DailyTask) => {
    if (readOnly || !task.available) return
    // Решение владельца: открыл ссылку → авто-выполнено.
    window.open(task.link, '_blank', 'noopener')
    try {
      await complete.mutateAsync(task.id)
    } catch {
      toast.error('Не удалось отметить задачу')
    }
  }

  return (
    <div className="shrink-0" style={{ borderTop: '1px solid var(--border-subtle)' }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium"
        style={{ color: 'var(--fg-dim)' }}
        data-testid="daily-tasks-toggle"
      >
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <CheckSquare size={13} />
        Ежедневные задачи
        {data.length > 0 && (
          <span className="ml-auto text-2xs" style={{ color: 'var(--fg-faint)' }}>
            {doneCount}/{data.length}
          </span>
        )}
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-1 max-h-56 overflow-y-auto">
          {isLoading ? (
            <SkeletonList rows={3} height="30px" />
          ) : isError ? (
            <p
              className="flex items-center gap-1.5 text-2xs"
              style={{ color: 'var(--err)' }}
              data-testid="daily-tasks-error"
            >
              <AlertTriangle size={12} />
              Не удалось загрузить ежедневные задачи
            </p>
          ) : data.length === 0 ? (
            <p className="text-2xs" style={{ color: 'var(--fg-faint)' }}>Задач нет</p>
          ) : (
            data.map(task => {
              const meta = STATUS_META[task.status]
              const clickable = !readOnly && task.available
              return (
                <div
                  key={task.id}
                  role={clickable ? 'button' : undefined}
                  tabIndex={clickable ? 0 : undefined}
                  onClick={() => onTaskClick(task)}
                  onKeyDown={e => {
                    if (clickable && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      onTaskClick(task)
                    }
                  }}
                  data-testid={`daily-task-${task.id}`}
                  className="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-xs"
                  style={{
                    background: 'var(--bg-1)',
                    border: '1px solid var(--border-subtle)',
                    cursor: clickable ? 'pointer' : 'default',
                  }}
                >
                  <span className="flex items-center gap-1.5 truncate" style={{ color: 'var(--fg-dim)' }}>
                    {clickable && <ExternalLink size={11} style={{ color: 'var(--fg-faint)' }} />}
                    <span className="truncate">{task.name}</span>
                  </span>
                  <span
                    className="shrink-0 rounded px-1.5 py-0.5 text-2xs"
                    style={{ color: meta.color, border: `1px solid ${meta.color}` }}
                  >
                    {meta.label}
                  </span>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
