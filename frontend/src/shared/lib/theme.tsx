import { createContext, useContext, useEffect, useMemo, useState } from 'react'

export type ThemePreference = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'theme'

interface ThemeContextValue {
  theme: ThemePreference
  resolvedTheme: ResolvedTheme
  setTheme: (theme: ThemePreference) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<ThemePreference>(() => getStoredTheme())
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(getStoredTheme()))

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      document.documentElement.classList.remove('no-theme-transition')
      document.body.classList.remove('no-theme-transition')
    }, 50)

    return () => window.clearTimeout(timeoutId)
  }, [])

  useEffect(() => {
    const nextResolvedTheme = resolveTheme(theme)
    const root = document.documentElement

    setResolvedTheme(nextResolvedTheme)
    root.style.colorScheme = nextResolvedTheme
    if (theme === 'system') {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', theme)
    }
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      if (theme !== 'system') return

      const nextResolvedTheme = media.matches ? 'dark' : 'light'
      setResolvedTheme(nextResolvedTheme)
      document.documentElement.style.colorScheme = nextResolvedTheme
    }

    handleChange()
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [theme])

  const value = useMemo<ThemeContextValue>(() => ({
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme: () => {
      setTheme(currentTheme => resolveTheme(currentTheme) === 'dark' ? 'light' : 'dark')
    },
  }), [resolvedTheme, theme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}

function getStoredTheme(): ThemePreference {
  if (typeof window === 'undefined') return 'system'

  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY)
  if (storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system') {
    return storedTheme
  }
  return 'system'
}

function resolveTheme(theme: ThemePreference): ResolvedTheme {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}
