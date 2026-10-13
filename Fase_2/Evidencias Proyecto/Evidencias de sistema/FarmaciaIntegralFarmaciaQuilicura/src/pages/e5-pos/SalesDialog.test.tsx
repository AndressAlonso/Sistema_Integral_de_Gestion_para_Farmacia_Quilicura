import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import SalesDialog from './SalesDialog'
import { posApi } from './pos.api'
vi.mock('./pos.api', async importOriginal => {
  const original = await importOriginal<typeof import('./pos.api')>()
  return { ...original, posApi: { ...original.posApi, sales: vi.fn(), receipt: vi.fn(), reverse: vi.fn() } }
})
const originalShow = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
beforeEach(() => {
  sessionStorage.clear(); vi.resetAllMocks()
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute('open', '') } })
  vi.mocked(posApi.sales).mockResolvedValue({ sales: [{ id: 'sale', date: '2026-10-13T12:00:00Z', total: '200', payment: 'EFECTIVO' }] })
  vi.mocked(posApi.receipt).mockResolvedValue({ id: 'sale', date: '2026-10-13T12:00:00Z', branch: 'Centro', cashier: 'QA', payment: 'EFECTIVO', notice: '', subtotal: '200', discount: '0', total: '200', items: [{ product_id: 'product', name: 'Producto QA', sku: 'QA', quantity: 2, base_price: '100', price: '100', total: '200', promotion: null, lots: [{ sale_lot_id: 'lot-id', number: 'Lote QA', expires_at: '2027-01-01', quantity: 2, returnable: 2 }] }] })
})
afterEach(() => {
  cleanup(); vi.restoreAllMocks()
  if (originalShow) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', originalShow)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
})
it('editar una devolución invalida la confirmación de cantidad, condición, motivo y operación', async () => {
  render(<SalesDialog userId="qa" canReverse onClose={vi.fn()} onReceipt={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Ver venta' }))
  const quantity = await screen.findByRole('spinbutton')
  const condition = screen.getByLabelText('Condición de Producto QA')
  const reason = screen.getByLabelText('Motivo obligatorio')
  const confirmation = screen.getByLabelText('Confirmo las cantidades, la condición y el reembolso. Esta operación quedará registrada.')
  const submit = screen.getByRole('button', { name: 'Confirmar operación' })
  fireEvent.change(quantity, { target: { value: '1' } })
  fireEvent.change(condition, { target: { value: 'Envase revisado' } })
  fireEvent.change(reason, { target: { value: 'Devolución de prueba' } })
  const edits = [
    () => fireEvent.change(quantity, { target: { value: '2' } }),
    () => fireEvent.change(condition, { target: { value: 'Envase intacto' } }),
    () => fireEvent.change(reason, { target: { value: 'Motivo actualizado' } }),
    () => fireEvent.change(screen.getByLabelText('Tipo de operación'), { target: { value: 'ANULACION' } }),
    () => fireEvent.click(screen.getByLabelText('Confirmo que está apto para venta')),
  ]
  for (const edit of edits) {
    fireEvent.click(confirmation)
    expect(submit.hasAttribute('disabled')).toBe(false)
    edit()
    expect((confirmation as HTMLInputElement).checked).toBe(false)
    expect(submit.hasAttribute('disabled')).toBe(true)
  }
  expect(posApi.reverse).not.toHaveBeenCalled()
})
