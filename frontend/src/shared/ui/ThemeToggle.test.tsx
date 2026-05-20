import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ThemeProvider, THEME_STORAGE_KEY, useTheme } from '@/shared/lib/theme'
import { ThemeToggle } from '@/shared/ui/ThemeToggle'

function ThemeProbe() {
  const { theme, resolvedTheme } = useTheme()
  return <output data-testid="theme-probe">{`${theme}:${resolvedTheme}`}</output>
}

function renderThemeToggle() {
  return render(
    <ThemeProvider>
      <ThemeProbe />
      <ThemeToggle />
    </ThemeProvider>,
  )
}

function mockMatchMedia(matches: boolean) {
  const listeners = new Set<NonNullable<MediaQueryList['onchange']>>()
  const matchMedia = vi.fn().mockImplementation(
    () =>
      ({
        matches,
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addEventListener: (
          _event: string,
          listener: EventListenerOrEventListenerObject,
        ) => {
          if (typeof listener === 'function') {
            listeners.add(listener as NonNullable<MediaQueryList['onchange']>)
          }
        },
        removeEventListener: (
          _event: string,
          listener: EventListenerOrEventListenerObject,
        ) => {
          if (typeof listener === 'function') {
            listeners.delete(listener as NonNullable<MediaQueryList['onchange']>)
          }
        },
        addListener: listener => {
          if (listener) {
            listeners.add(listener)
          }
        },
        removeListener: listener => {
          if (listener) {
            listeners.delete(listener)
          }
        },
        dispatchEvent: () => true,
      }) as MediaQueryList,
  )

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: matchMedia,
  })
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.colorScheme = ''
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses system preference by default and cycles system -> light -> dark', async () => {
    mockMatchMedia(true)

    renderThemeToggle()

    await waitFor(() => {
      expect(screen.getByTestId('theme-probe')).toHaveTextContent('system:dark')
      expect(document.documentElement).not.toHaveAttribute('data-theme')
      expect(document.documentElement.style.colorScheme).toBe('dark')
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сменить тему' }))

    await waitFor(() => {
      expect(screen.getByTestId('theme-probe')).toHaveTextContent('light:light')
      expect(document.documentElement).toHaveAttribute('data-theme', 'light')
      expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сменить тему' }))

    await waitFor(() => {
      expect(screen.getByTestId('theme-probe')).toHaveTextContent('dark:dark')
      expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
      expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    })
  })

  it('cycles dark -> system and clears explicit data-theme', async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    mockMatchMedia(false)

    renderThemeToggle()

    await waitFor(() => {
      expect(screen.getByTestId('theme-probe')).toHaveTextContent('dark:dark')
      expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сменить тему' }))

    await waitFor(() => {
      expect(screen.getByTestId('theme-probe')).toHaveTextContent('system:light')
      expect(document.documentElement).not.toHaveAttribute('data-theme')
      expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('system')
    })
  })
})
