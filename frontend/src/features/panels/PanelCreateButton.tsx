/**
 * PanelCreateButton — T-7-035 (Z7).
 *
 * Кнопка «+ Панель» в title bar ZipPage + модалка создания.
 * Видна service/admin/all. Если выбран конкретный экран (displaySlug в URL) —
 * заполняется как default; иначе показывается селект.
 */
import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'

import { useDisplays } from '@/entities/display/hooks'
import { useCreatePanel } from '@/entities/panel/hooks'
import { useMe } from '@/features/auth/hooks'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'

interface PanelCreateButtonProps {
  /** Если задан — display-id предзаполнен и поле скрыто. */
  presetDisplayId?: number | null
}

const ALLOWED_ROLES = new Set(['service', 'admin', 'all'])

export function PanelCreateButton({ presetDisplayId }: PanelCreateButtonProps) {
  const { data: me } = useMe()
  const canCreate = me ? ALLOWED_ROLES.has(me.permission) : false

  const [open, setOpen] = useState(false)
  if (!canCreate) return null

  return (
    <>
      <Button
        variant="primary"
        size="sm"
        icon={<Plus size={12} />}
        onClick={() => setOpen(true)}
        data-testid="create-panel-button"
      >
        Панель
      </Button>
      {open && (
        <CreatePanelModalInner
          presetDisplayId={presetDisplayId ?? null}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  )
}

function CreatePanelModalInner({
  presetDisplayId,
  onClose,
}: {
  presetDisplayId: number | null
  onClose: () => void
}) {
  const { data: displays = [] } = useDisplays()
  const mutation = useCreatePanel()

  const [name, setName] = useState('')
  const [displayId, setDisplayId] = useState<number | null>(presetDisplayId)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDisplayId(presetDisplayId)
  }, [presetDisplayId])

  const handleSubmit = async () => {
    setError(null)
    if (!name.trim()) {
      setError('Имя панели обязательно')
      return
    }
    if (!displayId) {
      setError('Выберите экран')
      return
    }
    try {
      await mutation.mutateAsync({
        name: name.trim(),
        display_id: displayId,
        comment: comment.trim() || undefined,
      })
      onClose()
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      const data = (err as { response?: { data?: { detail?: string; message?: string } } })?.response?.data
      setError(data?.detail || data?.message || (status === 409 ? 'Такое имя уже занято' : 'Не удалось создать панель'))
    }
  }

  return (
    <Modal open onClose={onClose} title="Новая панель" size="sm">
      <form
        className="flex flex-col gap-3"
        onSubmit={e => {
          e.preventDefault()
          handleSubmit()
        }}
      >
        <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--fg-dim)' }}>
          <span>Имя панели *</span>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="например: P-007"
            maxLength={15}
            autoFocus
            data-testid="create-panel-name"
            className="h-input px-2 text-sm"
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-sm)',
              color: 'var(--fg)',
            }}
          />
        </label>

        {presetDisplayId == null && (
          <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--fg-dim)' }}>
            <span>Экран *</span>
            <select
              value={displayId ?? ''}
              onChange={e => setDisplayId(e.target.value ? Number(e.target.value) : null)}
              data-testid="create-panel-display"
              className="h-input px-2 text-sm"
              style={{
                background: 'var(--bg-2)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-sm)',
                color: 'var(--fg)',
              }}
            >
              <option value="">— выберите —</option>
              {displays.map(d => (
                <option key={d.id} value={d.id}>
                  {d.city.name} — {d.description ?? d.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--fg-dim)' }}>
          <span>Комментарий</span>
          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            maxLength={500}
            rows={2}
            data-testid="create-panel-comment"
            className="px-2 py-1 text-sm"
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-sm)',
              color: 'var(--fg)',
            }}
          />
        </label>

        {error && (
          <div className="text-xs" style={{ color: 'var(--err)' }} data-testid="create-panel-error">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-1">
          <Button variant="ghost" type="button" onClick={onClose} disabled={mutation.isPending}>
            Отмена
          </Button>
          <Button
            variant="primary"
            type="submit"
            loading={mutation.isPending}
            data-testid="create-panel-submit"
          >
            Создать
          </Button>
        </div>
      </form>
    </Modal>
  )
}
