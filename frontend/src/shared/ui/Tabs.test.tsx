import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Tabs } from './Tabs'

describe('Tabs', () => {
  it('renders readable inactive tabs and accented active tab', () => {
    const onChange = vi.fn()

    render(
      <Tabs value="received" onChange={onChange}>
        <Tabs.Item value="received">Запросы</Tabs.Item>
        <Tabs.Item value="all">Все</Tabs.Item>
      </Tabs>,
    )

    expect(screen.getByRole('tablist')).toBeInTheDocument()
    const activeTab = screen.getByTestId('tabs-item-received')
    const inactiveTab = screen.getByTestId('tabs-item-all')

    expect(activeTab).toHaveAttribute('aria-selected', 'true')
    expect(activeTab).toHaveStyle({
      color: 'var(--fg)',
      background: 'var(--bg-3)',
    })
    expect(activeTab.getAttribute('style')).toContain('border-color: var(--accent)')
    expect(inactiveTab).toHaveAttribute('aria-selected', 'false')
    expect(inactiveTab).toHaveStyle({
      color: 'var(--fg-dim)',
      background: 'transparent',
    })
    expect(inactiveTab.getAttribute('style')).toContain('border-color: transparent')
  })

  it('promotes inactive tab contrast on hover and emits changes on click', () => {
    const onChange = vi.fn()

    render(
      <Tabs value="received" onChange={onChange}>
        <Tabs.Item value="received">Запросы</Tabs.Item>
        <Tabs.Item value="all">Все</Tabs.Item>
      </Tabs>,
    )

    const inactiveTab = screen.getByTestId('tabs-item-all')
    fireEvent.mouseEnter(inactiveTab)

    expect(inactiveTab).toHaveStyle({
      color: 'var(--fg)',
      background: 'var(--bg-3)',
    })

    fireEvent.click(inactiveTab)
    expect(onChange).toHaveBeenCalledWith('all')
  })
})
