/**
 * T-4-020: Универсальная модалка для переходов заявки.
 * Работает для всех 8 типов TransitionKind.
 */
import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Modal } from '@/shared/ui/Modal'
import { Button } from '@/shared/ui/Button'
import { useTransitionApplication } from '@/entities/application/hooks'
import { useExecutors } from '@/entities/executor/hooks'
import { Badge } from '@/shared/ui/Badge'
import { TRANSITION_CONFIGS, type TransitionKind, buildTransitionSchema } from './transitionConfigs'
import type { ApplicationDetail } from '@/shared/api/types'

interface TransitionModalProps {
  open: boolean
  onClose: () => void
  application: ApplicationDetail
  targetState: TransitionKind
}

export function TransitionModal({ open, onClose, application, targetState }: TransitionModalProps) {
  const config = TRANSITION_CONFIGS[targetState]
  const transition = useTransitionApplication()
  const { data: executors = [], isLoading: executorsLoading } = useExecutors(!!config.needsExecutor)
  const fileRef = useRef<HTMLInputElement>(null)
  const schema = buildTransitionSchema(config)

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: any) => {
    try {
      await transition.mutateAsync({
        id: application.id,
        target_state: targetState,
        comment: data.comment || undefined,
        executor_id: data.executor_id,
        file: fileRef.current?.files?.[0] ?? null,
      })
      toast.success(`✅ ${config.buttonLabel}`)
      reset()
      onClose()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Ошибка перехода')
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'var(--bg-1)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-md)',
    color: 'var(--fg)',
    fontSize: '12.5px',
    padding: '7px 10px',
    resize: 'none',
    outline: 'none',
    fontFamily: 'var(--font-sans)',
  }

  return (
    <Modal open={open} onClose={onClose} title={config.title}>
      <Modal.Body>
        {/* Context */}
        <div
          className="flex items-center gap-3 p-3 rounded-md mb-4 text-xs"
          style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-md)' }}
        >
          <span style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}>
            #{application.id}
          </span>
          <Badge
            label={application.status.description ?? application.status.name}
            bgHex={application.status.color.hex}
            fgHex={application.status.color_text.hex}
            icon={application.status.icon?.unicode_symbol}
          />
          <span style={{ color: 'var(--fg-dim)' }}>
            {application.display.description ?? application.display.slug}
          </span>
          <span style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}>
            поз.{application.cell.position}
          </span>
        </div>

        {config.description && (
          <p className="text-xs mb-4" style={{ color: 'var(--warn)' }}>{config.description}</p>
        )}

        {/* Executor */}
        {config.needsExecutor && (
          <div className="mb-3">
            <label className="block text-2xs mb-1.5" style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Исполнитель <span style={{ color: 'var(--err)' }}>*</span>
            </label>
            <select
              {...register('executor_id', { valueAsNumber: true })}
              disabled={executorsLoading}
              defaultValue=""
              style={inputStyle}
            >
              <option value="" disabled>
                {executorsLoading ? 'Загрузка...' : 'Выберите исполнителя'}
              </option>
              {executors.map((executor) => (
                <option key={executor.id} value={executor.id}>
                  {[executor.last_name, executor.first_name].filter(Boolean).join(' ') || `#${executor.id}`}
                  {executor.executor_role ? ` · ${executor.executor_role}` : ''}
                </option>
              ))}
            </select>
            {errors.executor_id && (
              <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
                {errors.executor_id.message as string}
              </p>
            )}
          </div>
        )}

        {/* Comment */}
        <div className="mb-3">
          <label className="block text-2xs mb-1.5" style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Комментарий {config.commentRequired && <span style={{ color: 'var(--err)' }}>*</span>}
          </label>
          <textarea
            {...register('comment')}
            rows={3}
            placeholder={config.commentPlaceholder ?? 'Опционально...'}
            style={inputStyle}
          />
          {errors.comment && (
            <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
              {errors.comment.message as string}
            </p>
          )}
        </div>

        {/* File */}
        {config.filePresent && (
          <div className="mb-3">
            <label className="block text-2xs mb-1.5" style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Фото / файл
            </label>
            <input
              ref={fileRef}
              type="file"
              accept="image/*,application/pdf"
              className="text-xs"
              style={{ color: 'var(--fg-dim)' }}
            />
          </div>
        )}

        {/* Confirm checkbox */}
        {config.confirmRequired && (
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input
              type="checkbox"
              {...register('confirmed')}
              className="rounded"
            />
            <span style={{ color: 'var(--fg-dim)' }}>{config.confirmText}</span>
          </label>
        )}
        {errors.confirmed && (
          <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
            {errors.confirmed.message as string}
          </p>
        )}
      </Modal.Body>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>Отмена</Button>
        <Button
          variant={config.buttonVariant}
          size="sm"
          loading={transition.isPending}
          onClick={handleSubmit(onSubmit)}
        >
          {config.buttonLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
