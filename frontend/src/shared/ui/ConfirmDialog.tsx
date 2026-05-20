import { useState } from 'react'

import { Button } from './Button'
import { Modal } from './Modal'

type ConfirmVariant = 'danger' | 'primary' | 'ok'

export interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void | Promise<void>
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: ConfirmVariant
  loading?: boolean
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Точно?',
  description,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  variant = 'danger',
  loading: externalLoading = false,
}: ConfirmDialogProps) {
  const [internalLoading, setInternalLoading] = useState(false)
  const loading = externalLoading || internalLoading

  const handleConfirm = async () => {
    if (loading) return

    try {
      setInternalLoading(true)
      await onConfirm()
      onClose()
    } catch {
      // Keep the dialog open so the caller can render the backend error.
    } finally {
      setInternalLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={title} description={description} size="sm">
      <div className="mt-1 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={loading}>
          {cancelText}
        </Button>
        <Button
          variant={variant}
          onClick={handleConfirm}
          loading={loading}
          data-testid="confirm-dialog-confirm"
          autoFocus
        >
          {confirmText}
        </Button>
      </div>
    </Modal>
  )
}

export function useConfirmDialog() {
  const [open, setOpen] = useState(false)

  return {
    ask: () => setOpen(true),
    close: () => setOpen(false),
    props: {
      open,
      onClose: () => setOpen(false),
    },
  }
}
