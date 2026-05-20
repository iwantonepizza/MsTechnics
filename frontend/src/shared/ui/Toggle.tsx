import { cn } from '@/shared/lib/utils'

export interface ToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
  label?: React.ReactNode
  ariaLabel?: string
  disabled?: boolean
  size?: 'sm' | 'md'
  className?: string
  'data-testid'?: string
}

export function Toggle({
  checked,
  onChange,
  label,
  ariaLabel,
  disabled,
  size = 'md',
  className,
  ...rest
}: ToggleProps) {
  const width = size === 'sm' ? 32 : 36
  const height = size === 'sm' ? 18 : 20
  const knob = height - 4
  const knobX = checked ? width - knob - 2 : 2

  return (
    <label
      className={cn(
        'inline-flex cursor-pointer select-none items-center gap-2',
        disabled && 'cursor-not-allowed opacity-55',
        className,
      )}
      style={{ color: 'var(--fg)' }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={event => onChange(event.target.checked)}
        disabled={disabled}
        className="sr-only"
        aria-label={typeof label === 'string' ? label : ariaLabel}
        data-testid={rest['data-testid']}
      />
      <span
        className="relative inline-block transition-colors"
        style={{
          width,
          height,
          borderRadius: 999,
          background: checked ? 'var(--accent)' : 'var(--bg-3)',
        }}
      >
        <span
          className="absolute transition-transform"
          style={{
            top: 2,
            left: 0,
            width: knob,
            height: knob,
            borderRadius: '50%',
            background: 'var(--bg-0)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.25)',
            transform: `translateX(${knobX}px)`,
          }}
        />
      </span>
      {label !== undefined && (
        <span className="text-sm" style={{ color: 'var(--fg-dim)' }}>
          {label}
        </span>
      )}
    </label>
  )
}
