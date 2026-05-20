import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Toggle } from '@/shared/ui/Toggle'

describe('Toggle', () => {
  it('calls onChange with next checked state', () => {
    const onChange = vi.fn()

    render(<Toggle checked={false} onChange={onChange} ariaLabel="Звуковые уведомления" />)

    fireEvent.click(screen.getByRole('checkbox', { name: 'Звуковые уведомления' }))

    expect(onChange).toHaveBeenCalledWith(true)
  })
})
