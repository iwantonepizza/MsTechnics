import { Monitor, Moon, Sun } from 'lucide-react'

import { useTheme, type ThemePreference } from '@/shared/lib/theme'

const ICONS: Record<ThemePreference, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
}

const LABELS: Record<ThemePreference, string> = {
  light: 'Светлая тема',
  dark: 'Тёмная тема',
  system: 'Системная тема',
}

const NEXT: Record<ThemePreference, ThemePreference> = {
  light: 'dark',
  dark: 'system',
  system: 'light',
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const Icon = ICONS[theme]

  return (
    <button
      type="button"
      aria-label="Сменить тему"
      title={LABELS[theme]}
      onClick={() => setTheme(NEXT[theme])}
      className="icon-btn"
      data-testid="theme-toggle"
    >
      <Icon size={14} />
    </button>
  )
}
