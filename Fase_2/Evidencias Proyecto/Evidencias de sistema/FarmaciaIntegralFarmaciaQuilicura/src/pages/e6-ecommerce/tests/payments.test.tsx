import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import OrderPaymentPanel from '../components/OrderPaymentPanel'
import OrderConfirmationPage from '../pages/OrderConfirmationPage'
import { finishAttempt, orderAccess, orderAttempt, pendingOrder, recoverOrder, rememberOrder } from '../services/orders.api'
import type { OnlineOrder } from '../services/orders.api'
import { createCheckout, redirectToCheckout, safeCheckoutUrl } from '../services/payments.api'

vi.mock('../services/orders.api', async original => ({ ...await original<typeof import('../services/orders.api')>(), recoverOrder: vi.fn() }))
vi.mock('../services/payments.api', async original => ({ ...await original<typeof import('../services/payments.api')>(), createCheckout: vi.fn(), redirectToCheckout: vi.fn() }))
vi.mock('../components/PublicHeader', () => ({ default: () => null }))
const clearCart = vi.hoisted(() => vi.fn())
vi.mock('../hooks/useCart', () => ({ useCart: () => ({ draft: { items: [] }, validation: null, loading: false, clear: clearCart }) }))
vi.mock('../hooks/useGuest', () => ({ useGuest: () => ({ guest: null }) }))
vi.mock('../hooks/useCustomerSession', () => ({ useCustomerSession: () => ({ customer: null, loading: false }) }))
const order: OnlineOrder = { id: '12345678-1234-1234-1234-123456789012', number: 'WEB-QA', status: 'PENDIENTE_PAGO', total: '1000', currency: 'CLP', created_at: new Date().toISOString(), pickup_branch: { id: 'branch', name: 'Centro' }, items: [] }
const access = { request_id: order.id, request_token: 'a'.repeat(64) }
beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks(); rememberOrder(order.id, access); vi.mocked(recoverOrder).mockResolvedValue(order) })
afterEach(() => { cleanup(); vi.useRealTimers() })

it('conserva la clave del pedido al terminar el intento y permite crear otro carrito', () => {
  orderAttempt(); finishAttempt()
  expect(pendingOrder()).toBeNull()
  expect(orderAccess(order.id)).toEqual(access)
  expect(orderAttempt().request_id).not.toBe(order.id)
})
it('abre checkout una sola vez ante doble clic', async () => {
  let resolve!: (url: string) => void
  vi.mocked(createCheckout).mockImplementation(() => new Promise(done => { resolve = done }))
  render(<OrderPaymentPanel order={order} onUpdate={vi.fn()} />)
  const button = screen.getByRole('button', { name: 'Pagar con Mercado Pago' })
  fireEvent.click(button); fireEvent.click(button)
  expect(createCheckout).toHaveBeenCalledTimes(1)
  await act(async () => { resolve('https://www.mercadopago.cl/checkout/test') })
  expect(redirectToCheckout).toHaveBeenCalledWith('https://www.mercadopago.cl/checkout/test')
  expect(orderAccess(order.id)).toEqual(access)
})
it('conserva acceso y muestra el error si checkout falla', async () => {
  vi.mocked(createCheckout).mockRejectedValue(new Error('Pago temporalmente no disponible'))
  render(<OrderPaymentPanel order={order} onUpdate={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Pagar con Mercado Pago' }))
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Pago temporalmente no disponible')
  expect(redirectToCheckout).not.toHaveBeenCalled()
  expect(orderAccess(order.id)).toEqual(access)
})
it.each(['PAGADO', 'CANCELADO', 'REVISION_PAGO', 'EN_PREPARACION', 'LISTO_PARA_RETIRO'])('impide pagar un pedido en estado %s', status => {
  render(<OrderPaymentPanel order={{ ...order, status }} onUpdate={vi.fn()} />)
  expect(screen.queryByRole('button', { name: 'Pagar con Mercado Pago' })).toBeNull()
})
it('actualiza el estado usando la respuesta del servidor', async () => {
  const update = vi.fn()
  vi.mocked(recoverOrder).mockResolvedValue({ ...order, status: 'PAGADO' })
  render(<OrderPaymentPanel order={order} onUpdate={update} />)
  fireEvent.click(screen.getByRole('button', { name: 'Consultar estado' }))
  await waitFor(() => expect(update).toHaveBeenCalledWith(expect.objectContaining({ status: 'PAGADO' })))
})
it('consulta automáticamente y detiene las consultas al desmontar', async () => {
  vi.useFakeTimers()
  const mounted = render(<OrderPaymentPanel order={order} onUpdate={vi.fn()} />)
  await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
  expect(recoverOrder).toHaveBeenCalledTimes(1)
  mounted.unmount()
  await vi.advanceTimersByTimeAsync(10000)
  expect(recoverOrder).toHaveBeenCalledTimes(1)
})
it('ignora status=approved en la URL y recupera el estado real al retornar', async () => {
  render(<MemoryRouter initialEntries={[`/tienda/confirmar?order_id=${order.id}&status=approved&collection_status=approved`]}><OrderConfirmationPage /></MemoryRouter>)
  expect(await screen.findByText('Pendiente de pago')).toBeTruthy()
  expect(screen.queryByText('Pago confirmado')).toBeNull()
  expect(recoverOrder).toHaveBeenCalledWith(access)
})
it('no crea otro pedido si falta la clave al retornar', async () => {
  sessionStorage.clear()
  render(<MemoryRouter initialEntries={[`/tienda/confirmar?order_id=${order.id}`]}><OrderConfirmationPage /></MemoryRouter>)
  expect(screen.getByText(/No pudimos abrir este pedido/)).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Crear pedido y reservar' })).toBeNull()
  expect(recoverOrder).not.toHaveBeenCalled()
})
describe('enlaces de checkout', () => {
  it('admite el dominio HTTPS esperado', () => expect(safeCheckoutUrl('https://www.mercadopago.cl/checkout/test')).toBe('https://www.mercadopago.cl/checkout/test'))
  it.each(['https://evil.example', 'https://mercadopago.cl.evil.example', 'javascript:alert(1)', 'http://www.mercadopago.cl', 'https://user@www.mercadopago.cl', 'https://www.mercadopago.cl:8080'])('rechaza %s', url => {
    expect(() => safeCheckoutUrl(url)).toThrow()
  })
})
