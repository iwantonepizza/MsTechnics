import * as Dialog from '@radix-ui/react-dialog'
import { Search, CornerDownLeft, ArrowUp, ArrowDown } from 'lucide-react'
import { Spinner } from '@/shared/ui/Spinner'
import { cn } from '@/shared/lib/utils'
import type { SearchResultItem, SearchSection } from '@/features/search/types'

interface CommandPaletteProps {
  open: boolean
  query: string
  isLoading: boolean
  sections: SearchSection[]
  activeIndex: number
  onClose: () => void
  onQueryChange: (value: string) => void
  onActiveIndexChange: (index: number) => void
  onSelect: (item: SearchResultItem) => void
  onInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  inputRef: React.RefObject<HTMLInputElement>
}

export function CommandPalette({
  open,
  query,
  isLoading,
  sections,
  activeIndex,
  onClose,
  onQueryChange,
  onActiveIndexChange,
  onSelect,
  onInputKeyDown,
  inputRef,
}: CommandPaletteProps) {
  const flatItems = sections.flatMap(section => section.items)
  const hasResults = flatItems.length > 0
  const showHelper = query.length < 2 && !hasResults
  const showEmpty = query.length >= 2 && !isLoading && !hasResults

  let offset = 0

  return (
    <Dialog.Root open={open} onOpenChange={nextOpen => !nextOpen && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(10px)' }}
        />
        <Dialog.Content
          className="fixed left-1/2 top-[12vh] z-50 w-[min(720px,calc(100vw-24px))] -translate-x-1/2 overflow-hidden rounded-xl border"
          style={{
            background: 'var(--bg-1)',
            borderColor: 'var(--border)',
            boxShadow: 'var(--shadow-modal)',
          }}
        >
          <Dialog.Title className="sr-only">Глобальный поиск</Dialog.Title>
          <Dialog.Description className="sr-only">
            Поиск по экранам, панелям, заявкам, выездам, пользователям и ЗИП.
          </Dialog.Description>

          <div
            className="flex items-center gap-3 px-4 py-3"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <Search size={16} style={{ color: 'var(--fg-mute)' }} />
            <input
              ref={inputRef}
              value={query}
              onChange={event => onQueryChange(event.target.value)}
              onKeyDown={onInputKeyDown}
              placeholder="Поиск по системе"
              aria-label="Глобальный поиск"
              className="w-full bg-transparent text-sm outline-none placeholder:text-[color:var(--fg-faint)]"
              style={{ color: 'var(--fg)' }}
            />
            {isLoading ? <Spinner size={14} /> : null}
          </div>

          <div className="max-h-[65vh] overflow-y-auto px-2 py-2">
            {showHelper ? (
              <HelperState text="Введите запрос минимум из 2 символов" />
            ) : null}

            {showEmpty ? (
              <HelperState text="Ничего не найдено" />
            ) : null}

            {sections.map(section => {
              const sectionStart = offset
              offset += section.items.length

              return (
                <section key={section.key} className="mb-3 last:mb-0">
                  <div
                    className="px-2 pb-1 text-[11px] uppercase tracking-[0.16em]"
                    style={{ color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}
                  >
                    {section.label}
                  </div>
                  <div className="space-y-1">
                    {section.items.map((item, index) => {
                      const itemIndex = sectionStart + index
                      return (
                        <button
                          key={item.key}
                          type="button"
                          onMouseEnter={() => onActiveIndexChange(itemIndex)}
                          onClick={() => onSelect(item)}
                          className={cn(
                            'flex w-full items-start justify-between gap-3 rounded-lg px-3 py-2 text-left transition-colors',
                            itemIndex === activeIndex && 'outline-none',
                          )}
                          style={{
                            background: itemIndex === activeIndex ? 'var(--bg-2)' : 'transparent',
                            color: 'var(--fg)',
                            border: `1px solid ${itemIndex === activeIndex ? 'var(--accent-edge)' : 'transparent'}`,
                          }}
                        >
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">
                              <HighlightedText text={item.title} query={query} />
                            </div>
                            {item.subtitle ? (
                              <div className="mt-0.5 truncate text-xs" style={{ color: 'var(--fg-mute)' }}>
                                <HighlightedText text={item.subtitle} query={query} />
                              </div>
                            ) : null}
                          </div>
                          <div className="shrink-0 text-right">
                            {item.badge ? (
                              <div
                                className="rounded px-2 py-0.5 text-[11px]"
                                style={{
                                  background: 'var(--accent-faint)',
                                  color: 'var(--accent-ink)',
                                  fontFamily: 'var(--font-mono)',
                                }}
                              >
                                {item.badge}
                              </div>
                            ) : null}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </section>
              )
            })}
          </div>

          <div
            className="flex items-center justify-between gap-3 px-4 py-2 text-[11px]"
            style={{ borderTop: '1px solid var(--border-subtle)', color: 'var(--fg-faint)' }}
          >
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1">
                <ArrowUp size={12} />
                <ArrowDown size={12} />
                Навигация
              </span>
              <span className="inline-flex items-center gap-1">
                <CornerDownLeft size={12} />
                Открыть
              </span>
            </div>
            <span>Esc закрыть</span>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function HelperState({ text }: { text: string }) {
  return (
    <div className="px-3 py-8 text-center text-sm" style={{ color: 'var(--fg-faint)' }}>
      {text}
    </div>
  )
}

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query || query.length < 2) return text

  const normalizedQuery = query.trim()
  if (!normalizedQuery) return text

  const parts = text.split(new RegExp(`(${escapeRegExp(normalizedQuery)})`, 'ig'))
  return (
    <>
      {parts.map((part, index) => {
        const isMatch = part.localeCompare(normalizedQuery, undefined, { sensitivity: 'accent' }) === 0
        if (!isMatch) return <span key={`${part}-${index}`}>{part}</span>

        return (
          <mark
            key={`${part}-${index}`}
            style={{
              background: 'var(--accent-faint)',
              color: 'var(--fg)',
              borderRadius: '4px',
              padding: '0 2px',
            }}
          >
            {part}
          </mark>
        )
      })}
    </>
  )
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
