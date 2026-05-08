import { createContext, useContext } from 'react'
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
  return (
    <button
      onClick={() => onChange(value)}
      className="px-3 text-xs font-medium rounded transition-colors whitespace-nowrap"
      style={{
        height: 'var(--h-btn-sm)',
        background: isActive ? 'var(--bg-3)' : 'transparent',
        color: isActive ? 'var(--fg)' : 'var(--fg-mute)',
        border: 'none', cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}
export const Tabs = Object.assign(Root, { Item })
