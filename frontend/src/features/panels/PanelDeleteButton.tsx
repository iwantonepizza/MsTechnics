import { useState } from 'react'
import { Trash2 } from 'lucide-react'

import { useDeletePanel } from '@/entities/panel/hooks'
import { useMe } from '@/features/auth/hooks'
import { Button } from '@/shared/ui/Button'
import { ConfirmDialog, useConfirmDialog } from '@/shared/ui/ConfirmDialog'
import type { Panel } from '@/shared/api/types'

const ADMIN_ROLES = new Set(['admin', 'all'])

interface PanelDeleteButtonProps {
  panel: Panel
  onDeleted?: () => void
}

export function PanelDeleteButton({ panel, onDeleted }: PanelDeleteButtonProps) {
  const { data: me } = useMe()
  const canDelete = me ? ADMIN_ROLES.has(me.permission) : false

  const dlg = useConfirmDialog()
  const mutation = useDeletePanel()
  const [error, setError] = useState<string | null>(null)

  if (!canDelete) return null

  const handleConfirm = async () => {
    setError(null)
    try {
      await mutation.mutateAsync(panel.id)
      onDeleted?.()
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { detail?: string; message?: string } } })
        ?.response?.data
      const msg = data?.detail || data?.message || 'Не удалось удалить'
      setError(msg)
      throw err
    }
  }

  return (
    <>
      <Button
        variant="danger"
        size="sm"
        icon={<Trash2 size={11} />}
        onClick={dlg.ask}
        data-testid="delete-panel-button"
      >
        Удалить
      </Button>
      <ConfirmDialog
        {...dlg.props}
        onConfirm={handleConfirm}
        title={`Удалить панель ${panel.name}?`}
        description={
          error
            ? error
            : 'Действие безвозвратное. История панели в журнале останется.'
        }
        confirmText="Удалить"
        variant="danger"
        loading={mutation.isPending}
      />
    </>
  )
}
