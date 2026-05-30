import { createContext, useContext, useState } from 'react'
import { cn } from '@/shared/lib/utils'

const Ctx = createContext<{ active: string; onChange: (v: string) => void }>({
  active: '', onChange: () => {},
})

interface TabsProps {
  value: string; onChange: (v: string) => void
  children: React.ReactNode; className?: string
}
function Root({ value, onChange, children, className }: TabsProps) {
  return (
    <Ctx.Provider value={{ active: value, onChange }}>
      <div
        role="tablist"
        className={cn('flex items-center gap-0.5 p-0.5 rounded-md', className)}
        style={{ background: 'var(--bg-2)', border: '1px solid var(--border-subtle)' }}
      >
        {children}
      </div>
    </Ctx.Provider>
  )
}
function Item({ value, children }: { value: string; children: React.ReactNode }) {
  const { active, onChange } = useContext(Ctx)
  const isActive = active === value
  const [hovered, setHovered] = useState(false)

  const color = isActive ? 'var(--fg)' : hovered ? 'var(--fg)' : 'var(--fg-dim)'
  const background = isActive ? 'var(--bg-3)' : hovered ? 'var(--bg-3)' : 'transparent'
  const borderColor = isActive ? 'var(--accent)' : 'transparent'

  return (
    <button
      onClick={() => onChange(value)}
      className="px-3 text-xs font-medium rounded transition-colors whitespace-nowrap"
      role="tab"
      aria-selected={isActive}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      data-testid={`tabs-item-${value}`}
      style={{
        height: 'var(--h-btn-sm)',
        background,
        color,
        borderWidth: '1px',
        borderStyle: 'solid',
        borderColor,
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}
export const Tabs = Object.assign(Root, { Item })
