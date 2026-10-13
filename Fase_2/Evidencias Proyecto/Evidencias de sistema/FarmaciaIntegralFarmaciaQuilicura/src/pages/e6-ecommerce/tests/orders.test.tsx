import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import OrderConfirmationPage from '../pages/OrderConfirmationPage'
import { createOrder } from '../services/orders.api'

const state = vi.hoisted(() => ({ clear: vi.fn(), customer: null as null | { id: string; name: string },
  draft: { items: [{ product_id: 'product', quantity: 2 }], pickup_branch_id: 'branch' },
  guest: { name: 'Invitado QA', email: 'qa@example.com' } }))
vi.mock('../hooks/useCart', () => ({ useCart: () => ({ draft: state.draft, loading: false, clear: state.clear,
  validation: { valid: true, total: '200', pickup_branch: { name: 'Centro' }, items: [{ product_id: 'product', name: 'Producto QA', quantity: 2, subtotal: '200' }] } }) }))
vi.mock('../hooks/useGuest', () => ({ useGuest: () => ({ guest: state.guest, update: vi.fn() }) }))
vi.mock('../hooks/useCustomerSession', () => ({ useCustomerSession: () => ({ customer: state.customer, loading: false }) }))
vi.mock('../components/PublicHeader', () => ({ default: () => null }))
vi.mock('../services/orders.api', async importOriginal => ({ ...await importOriginal<typeof import('../services/orders.api')>(), createOrder: vi.fn() }))
beforeEach(() => { sessionStorage.clear(); state.customer = null; vi.mocked(createOrder).mockReset(); state.clear.mockReset() })
afterEach(cleanup)
const mount = () => render(<MemoryRouter><OrderConfirmationPage /></MemoryRouter>)
it('no crea ni reserva un pedido al abrir la página o sin confirmación', async () => {
  mount()
  fireEvent.submit(screen.getByRole('button', { name: 'Crear pedido y reservar' }).closest('form')!)
  expect(createOrder).not.toHaveBeenCalled()
  expect(await screen.findByRole('alert')).toBeTruthy()
})
it('guarda los datos mínimos del invitado y evita un doble envío', async () => {
  let complete!: (value: Awaited<ReturnType<typeof createOrder>>) => void
  vi.mocked(createOrder).mockImplementation(() => new Promise(resolve => { complete = resolve }))
  mount(); fireEvent.click(screen.getByRole('checkbox'))
  const form = screen.getByRole('button', { name: 'Crear pedido y reservar' }).closest('form')!
  fireEvent.submit(form); fireEvent.submit(form)
  expect(createOrder).toHaveBeenCalledTimes(1)
  expect(vi.mocked(createOrder).mock.calls[0][2]).toEqual(state.guest)
  complete({ id: 'order', number: 'WEB-QA', created_at: new Date().toISOString(),
    status: 'PENDIENTE_PAGO', total: '200', currency: 'CLP', pickup_branch: { id: 'branch', name: 'Centro' }, items: [] })
  await screen.findByText('Pedido WEB-QA')
  expect(state.clear).toHaveBeenCalledTimes(1)
  expect(screen.getByText(/todavía no está pagado/)).toBeTruthy()
})
it('con sesión utiliza la cuenta sin enviar datos de invitado', async () => {
  state.customer = { id: 'customer', name: 'Cliente QA' }
  vi.mocked(createOrder).mockRejectedValue(new Error('Stock cambió'))
  mount(); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(screen.getByRole('button', { name: 'Crear pedido y reservar' }))
  await waitFor(() => expect(createOrder).toHaveBeenCalledTimes(1))
  expect(vi.mocked(createOrder).mock.calls[0][2]).toBeNull()
  await screen.findByText('Stock cambió')
  expect(state.clear).not.toHaveBeenCalled()
})

it('permite completar los datos antes de confirmar y exige revisar de nuevo si se editan', () => {
  mount()
  const name = screen.getByLabelText('Nombre')
  const email = screen.getByLabelText('Correo electrónico')
  const checkbox = screen.getByRole('checkbox')
  const button = screen.getByRole('button', { name: 'Crear pedido y reservar' })
  expect(name.compareDocumentPosition(email) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(email.compareDocumentPosition(checkbox) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(checkbox.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(button.hasAttribute('disabled')).toBe(true)
  fireEvent.change(name, { target: { value: 'Nombre revisado' } })
  fireEvent.click(checkbox)
  expect(button.hasAttribute('disabled')).toBe(false)
  fireEvent.change(email, { target: { value: 'otro@example.com' } })
  expect(button.hasAttribute('disabled')).toBe(true)
  expect(createOrder).not.toHaveBeenCalled()
})
