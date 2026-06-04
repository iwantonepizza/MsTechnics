import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LoadingWave } from './LoadingWave'

afterEach(() => {
  vi.useRealTimers()
})

describe('LoadingWave', () => {
  it('cycles through reusable labels', () => {
    vi.useFakeTimers()
    render(<LoadingWave labels={['Загрузка', 'Суперсимметрия']} />)

    expect(screen.getByRole('status')).toHaveTextContent('Загрузка')
    act(() => vi.advanceTimersByTime(1800))
    expect(screen.getByRole('status')).toHaveTextContent('Суперсимметрия')
  })

  it('accepts a custom visual template', () => {
    render(<LoadingWave visual={<span data-testid="custom-loader-visual">MS</span>} />)

    expect(screen.getByTestId('custom-loader-visual')).toBeInTheDocument()
  })
})
