import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import LotStatusDialog from './LotStatusDialog'
import { disableLot, getLotStatus, reactivateLot } from './lot-status.api'
vi.mock('./lot-status.api', () => ({ getLotStatus: vi.fn(), reactivateLot: vi.fn(), disableLot: vi.fn() }))
const lot = { lot_id: 'lot', number: '2', product_name: 'Producto QA', branch_name: 'Centro', expiration_date: '2027-10-16', quantity: 0, is_active: false, can_reactivate: true, can_disable: false }
const originalShow = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeEach(() => {
  vi.resetAllMocks(); vi.mocked(getLotStatus).mockResolvedValue(lot); vi.mocked(reactivateLot).mockResolvedValue({ lot_id: 'lot', changed: true })
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.open = false } })
})
afterEach(() => {
  cleanup()
  if (originalShow) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', originalShow); else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (originalClose) Object.defineProperty(HTMLDialogElement.prototype, 'close', originalClose); else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
describe('Reactivación desde Inventario', () => {
  it('usa una ventana compacta y requiere motivo y confirmación sin cambiar cantidades', async () => {
    const onChanged = vi.fn()
    render(<LotStatusDialog lotId="lot" onClose={vi.fn()} onChanged={onChanged} />)
    await screen.findByText('Producto QA')
    expect(screen.getByRole('dialog').classList.contains('app-modal')).toBe(false)
    expect(screen.getByText('0 unidades')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reactivar lote' }).hasAttribute('disabled')).toBe(true)
    fireEvent.change(screen.getByLabelText('Motivo de reactivación'), { target: { value: 'Revisión autorizada' } })
    expect(screen.getByRole('button', { name: 'Reactivar lote' }).hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Reactivar lote' }))
    await waitFor(() => expect(reactivateLot).toHaveBeenCalledWith(lot, 'Revisión autorizada'))
    expect(onChanged).toHaveBeenCalledWith({ ...lot, is_active: true, can_reactivate: false, can_disable: true })
  })
  it('no permite reactivar si el backend no lo autoriza', async () => {
    vi.mocked(getLotStatus).mockResolvedValue({ ...lot, can_reactivate: false })
    render(<LotStatusDialog lotId="lot" onClose={vi.fn()} onChanged={vi.fn()} />)
    await screen.findByText('Producto QA')
    expect(screen.queryByRole('button', { name: 'Reactivar lote' })).toBeNull()
    expect(reactivateLot).not.toHaveBeenCalled()
  })
})


describe('Deshabilitación desde Revisar lote', () => {
  it('exige motivo y confirmación y usa la acción contraria sin cambiar unidades', async () => {
    const active = { ...lot, quantity: 28, is_active: true, can_disable: true, can_reactivate: false }
    vi.mocked(getLotStatus).mockResolvedValue(active)
    vi.mocked(disableLot).mockResolvedValue({ lot_id: 'lot', changed: true })
    const onChanged = vi.fn()
    render(<LotStatusDialog lotId="lot" onClose={vi.fn()} onChanged={onChanged} />)
    const button = await screen.findByRole('button', { name: 'Deshabilitar lote' })
    expect(button.hasAttribute('disabled')).toBe(true)
    fireEvent.change(screen.getByLabelText('Motivo de deshabilitación'), { target: { value: 'Envases dañados' } })
    expect(button.hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(button)
    await waitFor(() => expect(disableLot).toHaveBeenCalledWith(active, 'Envases dañados'))
    expect(reactivateLot).not.toHaveBeenCalled()
    expect(onChanged).toHaveBeenCalledWith({ ...active, is_active: false, can_reactivate: true, can_disable: false })
  })
  it('no muestra la acción sin permiso del backend', async () => {
    vi.mocked(getLotStatus).mockResolvedValue({ ...lot, is_active: true, can_disable: false, can_reactivate: false })
    render(<LotStatusDialog lotId="lot" onClose={vi.fn()} onChanged={vi.fn()} />)
    await screen.findByText('Producto QA')
    expect(screen.queryByRole('button', { name: 'Deshabilitar lote' })).toBeNull()
    expect(disableLot).not.toHaveBeenCalled()
  })
})


describe('Lote vencido', () => {
  it.each([true, false])('no ofrece cambios de habilitación cuando is_active=%s', async (isActive) => {
    vi.mocked(getLotStatus).mockResolvedValue({ ...lot, quantity: 5, expiration_date: '2000-01-01',
      is_active: isActive, can_disable: isActive, can_reactivate: false })
    render(<LotStatusDialog lotId="lot" onClose={vi.fn()} onChanged={vi.fn()} />)
    await screen.findByText('Lote vencido. No puede venderse, transferirse ni reactivarse.')
    expect(screen.getByText(/Cuando retires físicamente/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Deshabilitar lote' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Reactivar lote' })).toBeNull()
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(screen.queryByText(/revisa el permiso/)).toBeNull()
    expect(disableLot).not.toHaveBeenCalled()
    expect(reactivateLot).not.toHaveBeenCalled()
  })
})
