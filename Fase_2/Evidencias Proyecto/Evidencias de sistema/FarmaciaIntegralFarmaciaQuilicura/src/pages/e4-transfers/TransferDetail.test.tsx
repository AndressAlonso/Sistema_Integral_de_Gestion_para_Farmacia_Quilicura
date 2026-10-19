import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TransferDetail from './TransferDetail'
import { changeTransfer, getTransfer } from './transfers.api'
import type { Transfer } from './transfers.api'
import { reviewReceipt } from './receipt-review.api'

vi.mock('./transfers.api', async () => {
  const actual = await vi.importActual<typeof import('./transfers.api')>('./transfers.api')
  return { ...actual, getTransfer: vi.fn(), changeTransfer: vi.fn() }
})
vi.mock('./receipt-review.api', () => ({ reviewReceipt: vi.fn(), reactivateDestinationLot: vi.fn() }))
const transfer: Transfer = { id: 'qa-transfer', origin_id: 'origin', origin_name: 'Sucursal Centro', destination_id: 'destination', destination_name: 'Sucursal de prueba', state: 'SOLICITADA', created_at: '2026-10-12T12:00:00Z', requested_by: 'Usuario QA', rejection_reason: null, actions: ['approve', 'reject'], items: [{ product_id: 'product', product_name: 'Producto QA', sku: 'QA', quantity: 18, lots: [] }], timeline: [] }
const originalShowModal = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getTransfer).mockResolvedValue(transfer)
  vi.mocked(changeTransfer).mockResolvedValue({ ...transfer, state: 'AUTORIZADA' })
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: vi.fn(function (this: HTMLDialogElement) { this.setAttribute('open', '') }) })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: vi.fn(function (this: HTMLDialogElement) { this.removeAttribute('open') }) })
})
afterEach(() => {
  cleanup(); vi.restoreAllMocks()
  if (originalShowModal) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', originalShowModal)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (originalClose) Object.defineProperty(HTMLDialogElement.prototype, 'close', originalClose)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
describe('Selección y confirmación de transferencias', () => {
  it('elegir autorizar no ejecuta la operación hasta confirmar explícitamente', async () => {
    const onChanged = vi.fn()
    render(<MemoryRouter><TransferDetail transfer={transfer} onClose={vi.fn()} onChanged={onChanged} /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('radio', { name: 'Autorizar transferencia' }))
    expect(changeTransfer).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Confirmar autorización' }).hasAttribute('disabled')).toBe(true)
    fireEvent.submit(screen.getByRole('dialog').querySelector('form')!)
    expect(changeTransfer).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar autorización' }))
    await waitFor(() => expect(changeTransfer).toHaveBeenCalledWith('qa-transfer', 'approve', {}))
    expect(onChanged).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: 'Aprobar' })).toBeNull()
  })
  it('cambiar a rechazo exige confirmar de nuevo y conserva el contrato con motivo', async () => {
    render(<MemoryRouter><TransferDetail transfer={transfer} onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('radio', { name: 'Autorizar transferencia' }))
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('radio', { name: 'Rechazar transferencia' }))
    expect((screen.getByRole('checkbox') as HTMLInputElement).checked).toBe(false)
    expect(screen.getByRole('button', { name: 'Confirmar rechazo' }).hasAttribute('disabled')).toBe(true)
    fireEvent.change(screen.getByLabelText('Motivo *'), { target: { value: 'Prueba de rechazo' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar rechazo' }))
    await waitFor(() => expect(changeTransfer).toHaveBeenCalledWith('qa-transfer', 'reject', { reason: 'Prueba de rechazo' }))
  })
  it('mantiene la salida separada de la selección y explica origen, destino y unidades', async () => {
    const authorized: Transfer = { ...transfer, state: 'AUTORIZADA', actions: ['reject', 'dispatch'] }
    vi.mocked(getTransfer).mockResolvedValue(authorized)
    render(<MemoryRouter><TransferDetail transfer={authorized} onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('radio', { name: 'Registrar salida de productos' }))
    expect(screen.getByText(/Registra la salida de 18 unidades de Sucursal Centro hacia Sucursal de prueba/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Confirmar salida' }).hasAttribute('disabled')).toBe(true)
    expect(changeTransfer).not.toHaveBeenCalled()
  })
  it('tras un bloqueo abre una revisión compacta y enlaza a Inventario, sin reactivar ni recibir', async () => {
    const incoming: Transfer = { ...transfer, state: 'EN_TRANSITO', actions: ['receive'] }
    vi.mocked(getTransfer).mockResolvedValue(incoming)
    vi.mocked(changeTransfer).mockRejectedValue(new Error('No se puede recibir Producto QA: el lote 2 está deshabilitado.'))
    vi.mocked(reviewReceipt).mockResolvedValue({ destination_name: 'Centro', items: [{ product_name: 'Producto QA', number: '2', incoming_quantity: 18, source_expiration: '2027-10-16', destination_lot_id: 'lot', destination_expiration: '2027-10-16', destination_active: false, destination_quantity: 0, conflicts: ['INACTIVE'], can_reactivate: true }] })
    const onChanged = vi.fn()
    render(<MemoryRouter><TransferDetail transfer={incoming} onClose={vi.fn()} onChanged={onChanged} /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('radio', { name: 'Registrar recepción de productos' }))
    expect(screen.queryByRole('button', { name: 'Revisar lote' })).toBeNull()
    expect(reviewReceipt).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Producto QA — esperadas: 18'), { target: { value: '18' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar recepción' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Revisar lote' }))
    const modal = await screen.findByRole('dialog', { name: 'Revisar lote destino' })
    expect(modal.classList.contains('app-modal')).toBe(false)
    expect(await within(modal).findByRole('link', { name: 'Ir al lote en Inventario' })).toBeTruthy()
    expect(within(modal).queryByLabelText('Motivo de reactivación')).toBeNull()
    expect(changeTransfer).toHaveBeenCalledTimes(1)
    expect(onChanged).not.toHaveBeenCalled()
  })
  it('explica el tránsito sin ofrecer rechazo ni ejecutar operaciones', async () => {
    const incoming: Transfer = { ...transfer, state: 'EN_TRANSITO', actions: ['receive'] }
    vi.mocked(getTransfer).mockResolvedValue(incoming)
    render(<MemoryRouter><TransferDetail transfer={incoming} onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
    await screen.findByRole('radio', { name: 'Registrar recepción de productos' })
    expect(screen.getByText(/No se puede rechazar esta transferencia/)).toBeTruthy()
    expect(screen.queryByRole('radio', { name: 'Rechazar transferencia' })).toBeNull()
    expect(changeTransfer).not.toHaveBeenCalled()
  })
  it('no ofrece acciones que el backend no permite', async () => {
    const readonly: Transfer = { ...transfer, actions: [] }
    vi.mocked(getTransfer).mockResolvedValue(readonly)
    render(<MemoryRouter><TransferDetail transfer={readonly} onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
    await waitFor(() => expect(screen.queryByRole('status')).toBeNull())
    expect(screen.queryByRole('radio')).toBeNull()
    expect(screen.queryByRole('button', { name: /Confirmar/ })).toBeNull()
  })
})

it('editar el conteo de recepción exige una nueva confirmación', async () => {
  const incoming: Transfer = { ...transfer, state: 'EN_TRANSITO', actions: ['receive'] }
  vi.mocked(getTransfer).mockResolvedValue(incoming)
  render(<MemoryRouter><TransferDetail transfer={incoming} onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
  fireEvent.click(await screen.findByRole('radio', { name: 'Registrar recepción de productos' }))
  const count = screen.getByLabelText('Producto QA — esperadas: 18')
  fireEvent.change(count, { target: { value: '18' } })
  fireEvent.click(screen.getByRole('checkbox'))
  expect(screen.getByRole('button', { name: 'Confirmar recepción' }).hasAttribute('disabled')).toBe(false)
  fireEvent.change(count, { target: { value: '17' } })
  expect((screen.getByRole('checkbox') as HTMLInputElement).checked).toBe(false)
  expect(screen.getByRole('button', { name: 'Confirmar recepción' }).hasAttribute('disabled')).toBe(true)
  expect(changeTransfer).not.toHaveBeenCalled()
})
