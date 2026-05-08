import { Modal } from '@/shared/ui/Modal'

const SHORTCUTS = [
  ['/', 'Глобальный поиск'],
  ['?', 'Горячие клавиши'],
  ['Esc', 'Закрыть модалку'],
  ['Ctrl Enter', 'Отправить форму'],
  ['R', 'Взять заявку в работу'],
  ['D', 'Выполнено'],
  ['U', 'Невозможно'],
  ['A', 'Принять в контроле'],
  ['S', 'Отправить в сервис'],
  ['V', 'Архивировать'],
  ['N', 'Создать заявку'],
]

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded border px-1.5 font-mono text-2xs" style={{ borderColor: 'var(--border)', color: 'var(--fg-dim)' }}>
      {children}
    </span>
  )
}

export function ShortcutsHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal open={open} onClose={onClose} title="Горячие клавиши" size="sm">
      <Modal.Body>
        <dl className="grid grid-cols-[90px_1fr] gap-y-2 text-xs">
          {SHORTCUTS.map(([key, label]) => (
            <div key={key} className="contents">
              <dt><Kbd>{key}</Kbd></dt>
              <dd style={{ color: 'var(--fg-dim)' }}>{label}</dd>
            </div>
          ))}
        </dl>
      </Modal.Body>
    </Modal>
  )
}
