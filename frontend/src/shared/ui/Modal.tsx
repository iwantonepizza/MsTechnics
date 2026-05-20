import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'

import { cn } from '@/shared/lib/utils'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const SIZE_W = { sm: '380px', md: '480px', lg: '600px' }

function Root({
  open,
  onClose,
  title,
  description,
  children,
  size = 'md',
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={nextOpen => !nextOpen && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 flex w-full -translate-x-1/2 -translate-y-1/2 flex-col"
          style={{
            maxWidth: SIZE_W[size],
            background: 'var(--bg-1)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--r-lg)',
            boxShadow: 'var(--shadow-modal)',
            maxHeight: '85vh',
          }}
        >
          <div
            className="shrink-0 flex items-center justify-between px-4 py-3"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <Dialog.Title
              className="text-sm font-semibold"
              style={{ color: 'var(--fg)' }}
            >
              {title}
            </Dialog.Title>
            {description ? (
              <Dialog.Description className="sr-only">{description}</Dialog.Description>
            ) : null}
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Закрыть"
                className="icon-btn"
                data-testid="modal-close"
              >
                <X size={14} />
              </button>
            </Dialog.Close>
          </div>
          <div className="flex-1 overflow-y-auto">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function Body({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return <div className={cn('px-4 py-4', className)}>{children}</div>
}

function Footer({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="shrink-0 flex justify-end gap-2 px-4 py-3"
      style={{ borderTop: '1px solid var(--border-subtle)' }}
    >
      {children}
    </div>
  )
}

export const Modal = Object.assign(Root, { Body, Footer })
