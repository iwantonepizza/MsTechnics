import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { z } from 'zod'

import { apiClient } from '@/shared/api/client'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'
import {
  useChangeCondition,
  useChangeDepartment,
  useMoveToCell,
  usePanels,
  useRemovePanel,
} from '@/entities/panel/hooks'
import type { Cell, Condition, Department, Panel } from '@/shared/api/types'

export type PanelLike = Pick<Panel, 'id' | 'name' | 'condition' | 'application_status_name'> & {
  comment?: string | null
  department_name?: string | null
  display_id?: number | null
  cell_id?: string | number | null
  active_application_id?: number | null
}

const FIELD_STYLE: React.CSSProperties = {
  width: '100%',
  background: 'var(--bg-1)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)',
  color: 'var(--fg)',
  fontSize: '12.5px',
  padding: '7px 10px',
  outline: 'none',
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--fg-mute)' }}>
      {children}
    </label>
  )
}

function useConditions() {
  return useQuery({
    queryKey: ['conditions'],
    queryFn: async () => {
      const res = await apiClient.get<{ results: Condition[] }>('/conditions/')
      return res.data.results ?? res.data
    },
    staleTime: 5 * 60_000,
  })
}

function useDepartments() {
  return useQuery({
    queryKey: ['departments'],
    queryFn: async () => {
      const res = await apiClient.get<{ results: Department[] }>('/departments/')
      return res.data.results ?? res.data
    },
    staleTime: 5 * 60_000,
  })
}

function ActionModal({
  open,
  onClose,
  title,
  description,
  children,
  submitLabel,
  loading,
  disabled,
  onSubmit,
}: {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
  submitLabel: string
  loading?: boolean
  disabled?: boolean
  onSubmit: () => void
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} description={description}>
      <Modal.Body>{children}</Modal.Body>
      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>Отмена</Button>
        <Button variant="primary" size="sm" loading={loading} disabled={disabled} onClick={onSubmit}>
          {submitLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

const conditionSchema = z.object({
  condition_id: z.coerce.number().min(1, 'Выберите состояние'),
  comment: z.string().optional(),
})

export function ChangeConditionModal({
  open,
  onClose,
  panel,
}: {
  open: boolean
  onClose: () => void
  panel: PanelLike
}) {
  const conditions = useConditions()
  const mutation = useChangeCondition()
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof conditionSchema>>({
    resolver: zodResolver(conditionSchema),
    defaultValues: { comment: '' },
  })
  const options = (conditions.data ?? []).filter(condition => condition.id !== panel.condition?.id)

  const submit = handleSubmit(async data => {
    try {
      await mutation.mutateAsync({ id: panel.id, condition_id: data.condition_id, comment: data.comment })
      toast.success('Состояние панели изменено')
      onClose()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail ?? 'Не удалось изменить состояние')
    }
  })

  return (
    <ActionModal open={open} onClose={onClose} title="Сменить состояние" submitLabel="Сменить" loading={mutation.isPending} onSubmit={submit}>
      <div className="space-y-3">
        <div>
          <Label>Новое состояние</Label>
          <select {...register('condition_id')} style={FIELD_STYLE}>
            <option value="">Выберите состояние</option>
            {options.map(condition => (
              <option key={condition.id} value={condition.id}>
                {condition.icon?.unicode_symbol ?? ''} {condition.description ?? condition.name}
              </option>
            ))}
          </select>
          {errors.condition_id && <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>{errors.condition_id.message}</p>}
        </div>
        <div>
          <Label>Комментарий</Label>
          <textarea {...register('comment')} rows={3} style={{ ...FIELD_STYLE, resize: 'none' }} />
        </div>
      </div>
    </ActionModal>
  )
}

const departmentSchema = z.object({
  department: z.string().min(1, 'Выберите отдел'),
  comment: z.string().optional(),
})

export function ChangeDepartmentModal({
  open,
  onClose,
  panel,
}: {
  open: boolean
  onClose: () => void
  panel: PanelLike
}) {
  const departments = useDepartments()
  const mutation = useChangeDepartment()
  const hasActiveApplication = panel.application_status_name && panel.application_status_name !== 'default'
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof departmentSchema>>({
    resolver: zodResolver(departmentSchema),
    defaultValues: { comment: '' },
  })

  const submit = handleSubmit(async data => {
    if (hasActiveApplication) {
      toast.error('Сначала закройте активную заявку')
      return
    }
    try {
      await mutation.mutateAsync({ id: panel.id, department: data.department, comment: data.comment })
      toast.success('Отдел панели изменён')
      onClose()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail ?? 'Не удалось изменить отдел')
    }
  })

  return (
    <ActionModal
      open={open}
      onClose={onClose}
      title="Сменить отдел"
      submitLabel="Сменить"
      loading={mutation.isPending}
      disabled={!!hasActiveApplication}
      onSubmit={submit}
    >
      <div className="space-y-3">
        {hasActiveApplication && (
          <div className="rounded-md border p-3 text-xs" style={{ borderColor: 'var(--warn)', background: 'var(--warn-faint)', color: 'var(--warn)' }}>
            У панели активная заявка: {panel.application_status_name}. Сначала закройте заявку.
          </div>
        )}
        <div>
          <Label>Новый отдел</Label>
          <select {...register('department')} style={FIELD_STYLE}>
            <option value="">Выберите отдел</option>
            {(departments.data ?? []).map(department => (
              <option key={department.id} value={department.name}>{department.description ?? department.name}</option>
            ))}
          </select>
          {errors.department && <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>{errors.department.message}</p>}
        </div>
        <div>
          <Label>Комментарий</Label>
          <textarea {...register('comment')} rows={3} style={{ ...FIELD_STYLE, resize: 'none' }} />
        </div>
      </div>
    </ActionModal>
  )
}

const moveSchema = z.object({
  panel_id: z.coerce.number().min(1, 'Выберите панель'),
  comment: z.string().optional(),
})

export function MoveToCellModal({
  open,
  onClose,
  cell,
}: {
  open: boolean
  onClose: () => void
  cell: Cell
}) {
  const zipPanels = usePanels({ department: 'zip' })
  const handPanels = usePanels({ department: 'hand' })
  const mutation = useMoveToCell()
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof moveSchema>>({
    resolver: zodResolver(moveSchema),
    defaultValues: { comment: '' },
  })

  const options = useMemo(() => {
    const seen = new Set<number>()
    return [...(zipPanels.data ?? []), ...(handPanels.data ?? [])].filter(panel => {
      if (seen.has(panel.id)) return false
      seen.add(panel.id)
      return true
    })
  }, [handPanels.data, zipPanels.data])

  const submit = handleSubmit(async data => {
    try {
      await mutation.mutateAsync({ panelId: data.panel_id, cell_id: cell.id, comment: data.comment })
      toast.success('Панель поставлена в ячейку')
      onClose()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail ?? 'Не удалось поставить панель')
    }
  })

  return (
    <ActionModal open={open} onClose={onClose} title={`Поставить панель в ${cell.position}`} submitLabel="Поставить" loading={mutation.isPending} onSubmit={submit}>
      <div className="space-y-3">
        <div>
          <Label>Панель</Label>
          <select {...register('panel_id')} style={FIELD_STYLE}>
            <option value="">Выберите свободную панель</option>
            {options.map(panel => (
              <option key={panel.id} value={panel.id}>
                {panel.name} · {panel.condition?.description ?? panel.condition?.name ?? '—'} · {panel.department_name ?? '—'}
              </option>
            ))}
          </select>
          {errors.panel_id && <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>{errors.panel_id.message}</p>}
        </div>
        <div>
          <Label>Комментарий</Label>
          <textarea {...register('comment')} rows={3} style={{ ...FIELD_STYLE, resize: 'none' }} />
        </div>
      </div>
    </ActionModal>
  )
}

function buildRemovalSchema(applicationContext: boolean) {
  return z.object({
    comment: z.string().optional(),
    new_condition: applicationContext
      ? z.string().min(1, 'Укажите состояние при снятии в рамках заявки')
      : z.string().optional(),
    keep_condition: z.boolean().optional(),
  })
}

export function PanelRemovalModal({
  open,
  onClose,
  panel,
  applicationId,
  onRemoved,
}: {
  open: boolean
  onClose: () => void
  panel: PanelLike
  applicationId?: number
  onRemoved?: () => void
}) {
  const applicationContext = applicationId != null
  const subtitle = applicationContext ? `Р—Р°РєСЂС‹С‚РёРµ Р·Р°СЏРІРєРё #${applicationId}` : `РЎРЅСЏС‚РёРµ РїР°РЅРµР»Рё ${panel.name}`
  const conditions = useConditions()
  const mutation = useRemovePanel()
  const schema = buildRemovalSchema(applicationContext)
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<
    z.infer<typeof schema>
  >({
    resolver: zodResolver(schema),
    defaultValues: {
      comment: '',
      new_condition: applicationContext ? '' : (panel.condition?.name ?? ''),
      keep_condition: !applicationContext,
    },
  })

  const keepCondition = watch('keep_condition') ?? false

  const submit = handleSubmit(async data => {
    try {
      const shouldKeepCondition = !applicationContext && keepCondition
      const nextCondition = shouldKeepCondition ? undefined : data.new_condition || undefined

      await mutation.mutateAsync({
        id: panel.id,
        new_condition: nextCondition,
        comment: data.comment,
        application_id: applicationId,
      })
      toast.success('Панель снята')
      onRemoved?.()
      onClose()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail ?? 'Не удалось снять панель')
    }
  })

  return (
    <ActionModal
      open={open}
      onClose={onClose}
      description={subtitle}
      title="Снять панель"
      submitLabel="Снять"
      loading={mutation.isPending}
      onSubmit={submit}
    >
      <div className="space-y-3">
        <div
          className="rounded-md border p-3 text-xs"
          style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)', color: 'var(--fg-dim)' }}
        >
          {applicationContext ? `Закрытие заявки #${applicationId}` : `Снятие панели ${panel.name}`}
        </div>

        {!applicationContext && panel.active_application_id && (
          <div
            className="rounded-md border p-3 text-xs"
            style={{ borderColor: 'var(--warn)', background: 'var(--warn-faint)', color: 'var(--warn)' }}
          >
            Снятие без закрытия активной заявки № {panel.active_application_id}
          </div>
        )}

        <div>
          <Label>Комментарий</Label>
          <textarea {...register('comment')} rows={3} style={{ ...FIELD_STYLE, resize: 'none' }} />
        </div>

        {!applicationContext && (
          <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--fg-dim)' }}>
            <input
              type="checkbox"
              {...register('keep_condition')}
              onChange={event => {
                const checked = event.target.checked
                setValue('keep_condition', checked, { shouldDirty: true })
                if (checked) {
                  setValue('new_condition', panel.condition?.name ?? '', { shouldDirty: true })
                }
              }}
            />
            <span>Оставить как есть</span>
          </label>
        )}

        <div>
          <Label>
            {applicationContext ? (
              <>Новое состояние панели <span style={{ color: 'var(--err)' }}>*</span></>
            ) : (
              'Изменить состояние (по желанию)'
            )}
          </Label>
          <select
            {...register('new_condition')}
            disabled={!applicationContext && keepCondition}
            style={{
              ...FIELD_STYLE,
              opacity: !applicationContext && keepCondition ? 0.6 : 1,
            }}
          >
            <option value="">
              {applicationContext ? 'Выберите состояние' : 'Не менять'}
            </option>
            {(conditions.data ?? []).map(condition => (
              <option key={condition.id} value={condition.name}>
                {condition.icon?.unicode_symbol ?? ''} {condition.description ?? condition.name}
              </option>
            ))}
          </select>
          {errors.new_condition && (
            <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
              {errors.new_condition.message}
            </p>
          )}
        </div>
      </div>
    </ActionModal>
  )
}
