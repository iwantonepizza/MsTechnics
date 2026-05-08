import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const SIZE_W = { sm: '380px', md: '480px', lg: '600px' }

function Root({ open, onClose, title, children, size = 'md' }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={o => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full flex flex-col"
          style={{
            maxWidth: SIZE_W[size],
            background: 'var(--bg-2)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-lg)',
            boxShadow: 'var(--shadow-modal)',
            maxHeight: '85vh',
          }}
        >
          <div
            className="flex items-center justify-between px-4 py-3 shrink-0"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <Dialog.Title className="text-sm font-semibold" style={{ color: 'var(--fg)' }}>
              {title}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                className="flex items-center justify-center w-6 h-6 rounded transition-colors"
                style={{ color: 'var(--fg-mute)' }}
              >
                <X size={14} />
              </button>
            </Dialog.Close>
          </div>
          <div className="overflow-y-auto flex-1">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function Body({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('px-4 py-4', className)}>{children}</div>
}

function Footer({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="flex justify-end gap-2 px-4 py-3 shrink-0"
      style={{ borderTop: '1px solid var(--border-subtle)' }}
    >
      {children}
    </div>
  )
}

export const Modal = Object.assign(Root, { Body, Footer })
