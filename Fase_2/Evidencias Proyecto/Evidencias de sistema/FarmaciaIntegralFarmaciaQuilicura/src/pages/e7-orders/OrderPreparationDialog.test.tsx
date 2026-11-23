import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import OrderPreparationDialog from './OrderPreparationDialog'
import { changeOrder, getOrder, type OrderDetail } from './orders.api'

vi.mock('./orders.api', async () => ({ ...await vi.importActual('./orders.api'), getOrder: vi.fn(), changeOrder: vi.fn() }))
const order: OrderDetail = { id: 'qa', number: 'WEB-QA', status: 'EN_PREPARACION', created_at: '2026-10-20T12:00:00Z',
  currency: 'CLP', total: '100', pickup_branch: { id: 'branch', name: 'Centro' }, customer: { name: 'Cliente QA', email: 'qa@example.com' },
  items: [{ product_id: 'product', name: 'Producto QA', quantity: 1, unit_price: '100', subtotal: '100', promotion: null }],
  actions: ['ready'], transfers: [], history: [], ready_blocked_reason: null }
beforeEach(() => {
  vi.resetAllMocks()
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.removeAttribute('open') } })
  vi.mocked(getOrder).mockResolvedValue(order)
})
afterEach(cleanup)
it('exige confirmar y evita solicitudes duplicadas', async () => {
  vi.mocked(changeOrder).mockImplementation(() => new Promise(() => {}))
  render(<MemoryRouter><OrderPreparationDialog id="qa" onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
  const button = await screen.findByRole('button', { name: 'Marcar listo para retiro' })
  expect(button.hasAttribute('disabled')).toBe(true)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(button); fireEvent.click(button)
  expect(changeOrder).toHaveBeenCalledTimes(1)
  expect(changeOrder).toHaveBeenCalledWith(order, 'ready')
})
it('explica la transferencia pendiente y deshabilita marcar listo', async () => {
  vi.mocked(getOrder).mockResolvedValue({ ...order, actions: [], ready_blocked_reason: 'Falta recibir una transferencia del pedido.' })
  render(<MemoryRouter><OrderPreparationDialog id="qa" onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
  await screen.findByText('Falta recibir una transferencia del pedido.')
  expect(screen.getByRole('button', { name: 'Marcar listo para retiro' }).hasAttribute('disabled')).toBe(true)
})
it('muestra conflictos devueltos por el backend', async () => {
  vi.mocked(changeOrder).mockRejectedValue(new Error('Las reservas cambiaron. Actualiza el pedido.'))
  render(<MemoryRouter><OrderPreparationDialog id="qa" onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
  await screen.findByRole('checkbox')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Marcar listo para retiro' }))
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Las reservas cambiaron'))
})
it('permite iniciar preparación desde la sección de estado y refleja la respuesta', async () => {
  vi.mocked(getOrder).mockResolvedValue({ ...order, status: 'PAGADO', actions: ['preparation'] })
  vi.mocked(changeOrder).mockResolvedValue(order)
  const changed = vi.fn()
  render(<MemoryRouter><OrderPreparationDialog id="qa" onClose={vi.fn()} onChanged={changed} /></MemoryRouter>)
  fireEvent.click(await screen.findByRole('button', { name: 'Iniciar preparación' }))
  await screen.findByRole('button', { name: 'Marcar listo para retiro' })
  expect(changeOrder).toHaveBeenCalledWith(expect.objectContaining({ status: 'PAGADO' }), 'preparation')
  expect(changed).toHaveBeenCalledTimes(1)
})
it('explica que un pedido pendiente de pago no puede prepararse', async () => {
  vi.mocked(getOrder).mockResolvedValue({ ...order, status: 'PENDIENTE_PAGO', actions: [] })
  render(<MemoryRouter><OrderPreparationDialog id="qa" onClose={vi.fn()} onChanged={vi.fn()} /></MemoryRouter>)
  await screen.findByText('Falta confirmar el pago para iniciar la preparación.')
  expect(screen.queryByRole('button', { name: 'Iniciar preparación' })).toBeNull()
})
