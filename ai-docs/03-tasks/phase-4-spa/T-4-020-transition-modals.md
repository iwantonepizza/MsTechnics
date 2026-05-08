# T-4-020. TransitionModal — все 12 типов

> **Тип:** feature
> **Приоритет:** P0
> **Оценка:** 3 часа
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Универсальная модалка transition'а заявки. Конфиг по типу — какой comment обязателен, какой исполнитель нужен, и т.д. 12 типов из `ai-docs/07-frontend/design-brief-round-3.md`.

---

## Зависимости

- **Блокируется:** T-4-001..004, T-3-fix-001 (статусы без префикса)

---

## 12 типов transition (из дизайн-брифа)

```ts
type TransitionKind =
  | 'apply_in_control'      // принять в контроле
  | 'sent_to_service'       // в сервис (нужен executor)
  | 'work_in_service'       // взять в работу
  | 'done'                  // выполнено
  | 'unable'                // невозможно (comment обязателен)
  | 'archive_done'          // архив (после done)
  | 'archive_unable'        // архив (после unable)
  | 'create_application'    // создать заявку (это не transition, но та же модалка)
  | 'remove_panel'          // снять панель с ячейки
  | 'change_condition'      // сменить состояние панели
  | 'change_department'     // сменить отдел
  | 'delete_application'    // удалить заявку (5-min window)
```

---

## Что сделать

### Шаг 1. Конфиг

`frontend/src/features/applications/transitionConfigs.ts`:

```ts
import { z } from 'zod'

export interface TransitionConfig {
  title: string
  description?: string
  newStatusName: string
  commentRequired?: boolean
  filePresent?: boolean
  needsExecutor?: boolean   // dropdown executor
  needsCondition?: boolean
  warning?: string
  shortcut?: string
}

export const TRANSITION_CONFIGS: Record<string, TransitionConfig> = {
  apply_in_control: {
    title: 'Принять заявку в контроле',
    newStatusName: 'apply_in_control',
    shortcut: 'A',
  },
  sent_to_service: {
    title: 'Отправить в сервис',
    newStatusName: 'sent_to_service',
    needsExecutor: true,
    commentRequired: false,
    shortcut: 'S',
  },
  work_in_service: {
    title: 'Взять в работу',
    newStatusName: 'work_in_service',
    shortcut: 'R',
  },
  done: {
    title: 'Отметить выполненным',
    newStatusName: 'done',
    filePresent: true,
    shortcut: 'D',
  },
  unable: {
    title: 'Невозможно выполнить',
    newStatusName: 'unable',
    commentRequired: true,
    filePresent: true,
    shortcut: 'U',
  },
  archive_done: {
    title: 'Архивировать (выполнено)',
    newStatusName: 'archive_done',
    warning: 'Заявка уйдёт в архив, не вернётся',
    shortcut: 'V',
  },
  archive_unable: {
    title: 'Архивировать (невозможно)',
    newStatusName: 'archive_unable',
    warning: 'Заявка уйдёт в архив, не вернётся',
  },
}

export function buildSchema(cfg: TransitionConfig) {
  return z.object({
    comment: cfg.commentRequired
      ? z.string().min(1, 'Комментарий обязателен')
      : z.string().optional(),
    executor_id: cfg.needsExecutor
      ? z.number({ required_error: 'Выберите исполнителя' })
      : z.number().optional(),
    file: z.any().optional(),
  })
}
```

### Шаг 2. Универсальная TransitionModal

`frontend/src/features/applications/TransitionModal.tsx`:

```tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { X, AlertTriangle } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'

import { useTransitionApplication } from './hooks'
import { useExecutors } from '@/entities/executor/hooks'
import { TRANSITION_CONFIGS, buildSchema } from './transitionConfigs'
import type { ApplicationDetail } from '@/shared/api/types'

interface Props {
  application: ApplicationDetail
  kind: keyof typeof TRANSITION_CONFIGS
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function TransitionModal({ application, kind, open, onOpenChange, onSuccess }: Props) {
  const cfg = TRANSITION_CONFIGS[kind]
  const transition = useTransitionApplication()
  const { data: executors = [] } = useExecutors({ enabled: cfg.needsExecutor })
  
  const schema = buildSchema(cfg)
  const { register, handleSubmit, formState: { errors, isSubmitting }, reset } =
    useForm({ resolver: zodResolver(schema) })
  
  const onSubmit = async (data: any) => {
    try {
      await transition.mutateAsync({
        id: application.id,
        target_state: cfg.newStatusName,
        comment: data.comment ?? '',
        executor_id: data.executor_id,
        file: data.file?.[0],
      })
      toast.success(cfg.title + ' — выполнено')
      reset()
      onOpenChange(false)
      onSuccess?.()
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? 'Ошибка'
      toast.error(msg)
    }
  }
  
  // Ctrl+Enter / Cmd+Enter — submit
  // Esc — close (Radix делает это сам)
  
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-bg-0/80 backdrop-blur-sm" />
        <Dialog.Content
          onKeyDown={e => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleSubmit(onSubmit)()
          }}
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[480px] bg-bg-1 border border-border rounded-lg shadow-modal"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-border-subtle">
            <Dialog.Title className="text-[14px] font-semibold">{cfg.title}</Dialog.Title>
            <Dialog.Close className="text-fg-mute hover:text-fg"><X className="w-4 h-4" /></Dialog.Close>
          </div>
          
          <form onSubmit={handleSubmit(onSubmit)} className="px-5 py-4 space-y-4">
            {/* Контекст */}
            <div className="bg-bg-2 rounded-md p-3 space-y-1">
              <div className="flex items-center gap-2 text-[12px]">
                <span className="font-mono text-fg-mute">ID-{application.id}</span>
                <span className="text-fg-faint">·</span>
                <span className="text-fg-dim">{application.display.description}</span>
                <span className="text-fg-faint">·</span>
                <span className="font-mono text-fg-dim">{application.cell.position}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-fg-mute">Текущий:</span>
                <StatusPill status={application.status} />
                <span className="text-fg-faint">→</span>
                <StatusPill statusName={cfg.newStatusName} />
              </div>
            </div>
            
            {/* Warning */}
            {cfg.warning && (
              <div className="flex items-start gap-2 p-3 bg-warn-faint rounded-md">
                <AlertTriangle className="w-4 h-4 text-warn flex-shrink-0 mt-0.5" />
                <span className="text-[12px] text-warn-ink">{cfg.warning}</span>
              </div>
            )}
            
            {/* Executor dropdown */}
            {cfg.needsExecutor && (
              <Field label="Исполнитель" error={errors.executor_id?.message}>
                <select {...register('executor_id', { valueAsNumber: true })} className="...">
                  <option value="">— выберите —</option>
                  {executors.map(e => <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>)}
                </select>
              </Field>
            )}
            
            {/* Comment */}
            <Field
              label={cfg.commentRequired ? 'Комментарий *' : 'Комментарий'}
              error={errors.comment?.message}
            >
              <textarea {...register('comment')} rows={3} className="..." />
            </Field>
            
            {/* File */}
            {cfg.filePresent && (
              <Field label="Фото (опционально)">
                <input type="file" accept="image/*" {...register('file')} />
              </Field>
            )}
            
            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => onOpenChange(false)} type="button">Отмена</Button>
              <Button variant="primary" type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Выполняем...' : cfg.title}
                {cfg.shortcut && <Kbd>{cfg.shortcut}</Kbd>}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
```

### Шаг 3. Hook с optimistic update + rollback

`frontend/src/features/applications/hooks.ts`:

```ts
export function useTransitionApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: { id: number; target_state: string; comment: string; executor_id?: number; file?: File }) => {
      const formData = new FormData()
      formData.append('target_state', data.target_state)
      if (data.comment) formData.append('comment', data.comment)
      if (data.executor_id) formData.append('executor_id', String(data.executor_id))
      if (data.file) formData.append('file', data.file)
      
      const r = await apiClient.post(`/applications/${data.id}/transition/`, formData)
      return r.data
    },
    onMutate: async ({ id, target_state }) => {
      // Optimistic: меняем статус сразу
      await qc.cancelQueries({ queryKey: ['application', id] })
      const previous = qc.getQueryData(['application', id])
      qc.setQueryData(['application', id], (old: any) =>
        old ? { ...old, status: { ...old.status, name: target_state } } : old
      )
      return { previous }
    },
    onError: (err, vars, ctx: any) => {
      // Rollback
      if (ctx?.previous) qc.setQueryData(['application', vars.id], ctx.previous)
    },
    onSettled: (_, __, vars) => {
      qc.invalidateQueries({ queryKey: ['application', vars.id] })
      qc.invalidateQueries({ queryKey: ['applications'] })
    },
  })
}
```

---

## Критерии приёмки

- [ ] 7 transition'ов работают (apply, send, work, done, unable, archive_*)
- [ ] 5 panel/app actions (create, remove_panel, change_condition, change_dept, delete_app) — отдельная модалка но та же структура (T-4-021..023)
- [ ] Universal modal — конфиг определяет поведение
- [ ] Esc закрывает, Cmd+Enter сабмитит
- [ ] Optimistic update + rollback при ошибке
- [ ] Ошибки сервера (409 panel_has_active_application и пр.) — показываются toast'ом
- [ ] Validation через zod (commentRequired когда нужно)
- [ ] При success → close + invalidate queries

---

## Что НЕ делать

- НЕ дублировать код для каждого типа — один компонент + конфиг
- НЕ делать optimistic update без rollback — лучше pessimistic если не уверен
- НЕ блокировать UI при error — toast и оставить открытой
