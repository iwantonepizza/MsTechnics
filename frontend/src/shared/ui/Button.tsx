import { cn } from '@/shared/lib/utils'
import { Loader2 } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'ok'
type Size = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: React.ReactNode
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary:   { background: 'var(--accent)',    color: 'var(--accent-ink)',  border: 'none' },
  secondary: { background: 'var(--bg-2)',      color: 'var(--fg)',          border: '1px solid var(--border)' },
  danger:    { background: 'var(--err-faint)', color: 'var(--err)',         border: 'none' },
  ghost:     { background: 'transparent',      color: 'var(--fg-dim)',      border: 'none' },
  ok:        { background: 'var(--ok-faint)',  color: 'var(--ok)',          border: 'none' },
}

const sizeStyles: Record<Size, { height: string; padding: string; fontSize: string }> = {
  sm: { height: 'var(--h-btn-sm)', padding: '0 8px',  fontSize: '12px' },
  md: { height: 'var(--h-btn-md)', padding: '0 10px', fontSize: '12.5px' },
  lg: { height: 'var(--h-btn-lg)', padding: '0 12px', fontSize: '13px' },
}

export function Button({
  variant = 'secondary', size = 'md', loading, children, className, disabled, icon, style, ...props
}: ButtonProps) {
  const vs = variantStyles[variant]
  const ss = sizeStyles[size]
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-1.5 font-medium rounded-md transition-colors cursor-pointer',
        'focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
        className,
      )}
      style={{ ...vs, ...ss, borderRadius: 'var(--r-md)', fontFamily: 'var(--font-sans)', ...style }}
    >
      {loading ? <Loader2 size={12} className="animate-spin" /> : icon}
      {children}
    </button>
  )
}
