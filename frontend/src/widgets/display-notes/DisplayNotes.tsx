import { useState } from 'react'
import { ChevronDown, ChevronRight, StickyNote } from 'lucide-react'
import { toast } from 'sonner'
import { useAddDisplayNote, useDisplayNotes } from '@/entities/display-notes/hooks'
import { SkeletonList } from '@/shared/ui/Skeleton'
import { formatRelative } from '@/shared/lib/utils'

const DEPT_LABEL: Record<string, string> = {
  monitoring: 'Мониторинг',
  control: 'Контроль',
  service: 'Сервис',
  all: 'Все отделы',
  admin: 'Админ',
}

/** T-8-003: блок заметок об экране (общий для всех отделов). */
export function DisplayNotes({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const { data = [], isLoading } = useDisplayNotes(open ? slug : undefined)
  const addNote = useAddDisplayNote(slug)

  const submit = async () => {
    const value = text.trim()
    if (!value) return
    try {
      await addNote.mutateAsync(value)
      setText('')
    } catch {
      toast.error('Не удалось добавить заметку')
    }
  }

  return (
    <div className="shrink-0" style={{ borderTop: '1px solid var(--border-subtle)' }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium"
        style={{ color: 'var(--fg-dim)' }}
        data-testid="display-notes-toggle"
      >
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <StickyNote size={13} />
        Заметки об экране
        {data.length > 0 && (
          <span className="ml-auto text-2xs" style={{ color: 'var(--fg-faint)' }}>{data.length}</span>
        )}
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-2">
          <div className="flex gap-1.5">
            <input
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
              placeholder="Оставить заметку…"
              data-testid="display-note-input"
              className="flex-1 text-xs"
              style={{
                background: 'var(--bg-1)', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--r-sm)', color: 'var(--fg)', padding: '4px 8px',
              }}
            />
            <button
              type="button"
              onClick={submit}
              disabled={addNote.isPending || !text.trim()}
              className="text-xs px-2 rounded disabled:opacity-50"
              style={{ background: 'var(--accent)', color: 'var(--accent-ink)' }}
            >
              +
            </button>
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1.5">
            {isLoading ? (
              <SkeletonList rows={3} height="28px" />
            ) : data.length === 0 ? (
              <p className="text-2xs" style={{ color: 'var(--fg-faint)' }}>Заметок нет</p>
            ) : (
              data.map(note => (
                <div
                  key={note.id}
                  className="rounded px-2 py-1.5 text-xs"
                  style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)' }}
                >
                  <div style={{ color: 'var(--fg-dim)' }}>{note.text}</div>
                  <div className="mt-0.5 flex justify-between text-2xs" style={{ color: 'var(--fg-faint)' }}>
                    <span>{note.author_name} · {DEPT_LABEL[note.department] ?? note.department}</span>
                    <span>{formatRelative(note.created_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
