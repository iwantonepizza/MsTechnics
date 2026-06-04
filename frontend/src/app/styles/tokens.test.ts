import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const css = readFileSync(resolve(process.cwd(), 'src/app/styles/tokens.css'), 'utf8')

function block(pattern: RegExp): string {
  const match = css.match(pattern)
  if (!match) throw new Error(`CSS token block not found: ${pattern}`)
  return match[1]
}

function hexToken(source: string, name: string): string {
  const match = source.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`))
  if (!match) throw new Error(`Hex token not found: --${name}`)
  return match[1]
}

function luminance(hex: string): number {
  const channels = [1, 3, 5]
    .map(index => Number.parseInt(hex.slice(index, index + 2), 16) / 255)
    .map(value => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4))
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrast(foreground: string, background: string): number {
  const foregroundLuminance = luminance(foreground)
  const backgroundLuminance = luminance(background)
  return (
    (Math.max(foregroundLuminance, backgroundLuminance) + 0.05) /
    (Math.min(foregroundLuminance, backgroundLuminance) + 0.05)
  )
}

function expectReadable(source: string, foreground: string, backgrounds: string[]) {
  for (const background of backgrounds) {
    expect(contrast(hexToken(source, foreground), hexToken(source, background))).toBeGreaterThanOrEqual(4.5)
  }
}

describe('design token contrast', () => {
  const light = block(/:root\s*\{([\s\S]*?)\}/)
  const dark = block(/\[data-theme="dark"\]\s*\{([\s\S]*?)\}/)

  it('keeps light controls and small muted text readable', () => {
    expectReadable(light, 'fg-0', ['bg-1', 'bg-2'])
    expectReadable(light, 'fg-mute', ['bg-0', 'bg-1', 'bg-2'])
    expectReadable(light, 'fg-faint', ['bg-0', 'bg-1', 'bg-2'])
    expectReadable(light, 'success', ['bg-0', 'bg-1'])
    expectReadable(light, 'warning', ['bg-0', 'bg-1'])
    expectReadable(light, 'danger', ['bg-0', 'bg-1'])
    expectReadable(light, 'info', ['bg-0', 'bg-1'])
    expect(contrast(hexToken(light, 'fg-0'), hexToken(light, 'accent-0'))).toBeGreaterThanOrEqual(4.5)
  })

  it('keeps dark controls and small muted text readable', () => {
    expectReadable(dark, 'fg-0', ['bg-1', 'bg-2'])
    expectReadable(dark, 'fg-mute', ['bg-0', 'bg-1', 'bg-2'])
    expectReadable(dark, 'fg-faint', ['bg-0', 'bg-1', 'bg-2'])
    expect(contrast(hexToken(dark, 'accent-ink'), hexToken(dark, 'accent-0'))).toBeGreaterThanOrEqual(4.5)
  })

  it('defines the compatibility alias used by active filter buttons', () => {
    expect(light).toContain('--accent-fg: var(--accent-ink);')
    expect(dark).toContain('--accent-fg: var(--accent-ink);')
  })
})
