import { useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Modal } from '@/shared/ui/Modal'
import { Button } from '@/shared/ui/Button'
import { useCreateApplication } from '@/entities/application/hooks'
import type { Cell } from '@/shared/api/types'

const schema = z.object({ comment: z.string().min(1, 'Опишите проблему') })
type FormData = z.infer<typeof schema>

const INPUT_STYLE: React.CSSProperties = {
  width: '100%', background: 'var(--bg-1)', border: '1px solid var(--border)',
  borderRadius: 'var(--r-md)', color: 'var(--fg)', fontSize: '12.5px',
  padding: '7px 10px', resize: 'none', outline: 'none', fontFamily: 'var(--font-sans)',
}
const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: '11px', color: 'var(--fg-mute)',
  fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
  letterSpacing: '0.06em', marginBottom: '6px',
}

export function CreateApplicationModal({ open, onClose, cell, displayId, initialComment }: {
  open: boolean; onClose: () => void; cell: Cell; displayId: number; initialComment?: string
}) {
  const create = useCreateApplication()
  const fileRef = useRef<HTMLInputElement>(null)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    values: { comment: initialComment ?? '' },
  })

  const onSubmit = async (data: FormData) => {
    if (!cell.panel) return
    try {
      await create.mutateAsync({
        display_id: displayId, panel_id: cell.panel.id,
        cell_id: cell.id, comment: data.comment,
        file: fileRef.current?.files?.[0] ?? null,
      })
      toast.success(`✅ Заявка создана — ${cell.panel.name}`)
      reset(); onClose()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Ошибка создания заявки')
    }
  }

  const panel = cell.panel
  return (
    <Modal open={open} onClose={onClose} title="Создать заявку">
      <Modal.Body>
        {/* Panel info */}
        <div
          className="p-3 rounded-md mb-4 space-y-1.5"
          style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)' }}
        >
          {[
            ['Позиция', cell.position, true],
            ['Панель', panel?.name, true],
            ['Состояние', panel ? `${panel.condition.icon?.unicode_symbol ?? ''} ${panel.condition.description ?? panel.condition.name}` : '—', false],
          ].map(([k, v, mono]) => (
            <div key={String(k)} className="flex justify-between text-xs">
              <span style={{ color: 'var(--fg-mute)' }}>{k}</span>
              <span style={{ color: 'var(--fg-dim)', fontFamily: mono ? 'var(--font-mono)' : undefined }}>{String(v ?? '—')}</span>
            </div>
          ))}
        </div>

        {/* Comment */}
        <div className="mb-3">
          <label style={LABEL_STYLE}>Описание проблемы <span style={{ color: 'var(--err)' }}>*</span></label>
          <textarea {...register('comment')} rows={3} placeholder="Моргает, не работает, разбита..." style={INPUT_STYLE} />
          {errors.comment && <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>{errors.comment.message}</p>}
        </div>

        {/* File */}
        <div>
          <label style={LABEL_STYLE}>Фото / файл (опционально)</label>
          <input ref={fileRef} type="file" accept="image/*,application/pdf"
            className="text-xs" style={{ color: 'var(--fg-dim)' }} />
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose}>Отмена</Button>
        <Button variant="primary" size="sm" loading={create.isPending}
          onClick={handleSubmit(onSubmit)} disabled={!panel}
        >
          Создать заявку
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
