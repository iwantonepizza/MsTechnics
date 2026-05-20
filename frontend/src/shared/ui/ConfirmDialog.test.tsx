import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { act, useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { ConfirmDialog, useConfirmDialog } from './ConfirmDialog'

describe('ConfirmDialog (T-7-008)', () => {
  it('renders title and description', () => {
    render(
      <ConfirmDialog
        open
        onClose={() => {}}
        onConfirm={() => {}}
        title="Удалить заявку?"
        description="Действие нельзя отменить."
      />,
    )

    expect(screen.getByText('Удалить заявку?')).toBeInTheDocument()
    expect(screen.getByText('Действие нельзя отменить.')).toBeInTheDocument()
  })

  it('uses the short default title', () => {
    render(<ConfirmDialog open onClose={() => {}} onConfirm={() => {}} />)
    expect(screen.getByText('Точно?')).toBeInTheDocument()
  })

  it('calls onConfirm and onClose on confirm', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    const onClose = vi.fn()

    render(<ConfirmDialog open onClose={onClose} onConfirm={onConfirm} confirmText="Удалить" />)

    fireEvent.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('keeps the dialog open when onConfirm rejects', async () => {
    const onConfirm = vi.fn().mockRejectedValue(new Error('boom'))
    const onClose = vi.fn()

    render(
      <ConfirmDialog
        open
        onClose={onClose}
        onConfirm={onConfirm}
        title="Удалить заявку?"
      />,
    )

    fireEvent.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1))
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByText('Удалить заявку?')).toBeInTheDocument()
  })

  it('calls onClose on cancel and does not fire onConfirm', () => {
    const onConfirm = vi.fn()
    const onClose = vi.fn()

    render(<ConfirmDialog open onClose={onClose} onConfirm={onConfirm} />)
    fireEvent.click(screen.getByRole('button', { name: 'Отмена' }))

    expect(onClose).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('disables buttons while loading (external flag)', () => {
    render(
      <ConfirmDialog open onClose={() => {}} onConfirm={() => {}} loading />,
    )

    const cancel = screen.getByRole('button', { name: 'Отмена' }) as HTMLButtonElement
    expect(cancel.disabled).toBe(true)
  })

  it('useConfirmDialog: ask() opens, close() closes', () => {
    function Demo() {
      const dlg = useConfirmDialog()
      return (
        <>
          <button onClick={dlg.ask}>open</button>
          <ConfirmDialog {...dlg.props} onConfirm={() => {}} title="Q?" />
        </>
      )
    }

    render(<Demo />)
    expect(screen.queryByText('Q?')).not.toBeInTheDocument()

    act(() => {
      screen.getByText('open').click()
    })

    expect(screen.getByText('Q?')).toBeInTheDocument()
  })
})

void useState
