import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import PaymentSimulation from './PaymentSimulation'
import { apiRequest } from '../../services/http'

vi.mock('../../services/http', () => ({ apiRequest: vi.fn() }))
const response = (body: unknown) => ({ json: async () => body }) as Response
const order = { id: 'order-1', number: 'WEB-1', total: '500', pickup_branch: { name: 'Centro' }, items: [{ name: 'Producto', quantity: 2 }] }
beforeEach(() => vi.resetAllMocks())
afterEach(cleanup)

it('no presenta botones cuando el servidor deshabilita la simulación', async () => {
  vi.mocked(apiRequest).mockResolvedValue(response({ enabled: false }))
  render(<PaymentSimulation onChanged={vi.fn()} />)
  await waitFor(() => expect(apiRequest).toHaveBeenCalledTimes(1))
  expect(screen.queryByText('Simular pago aceptado')).toBeNull()
})

it('exige seleccionar y confirmar; bloquea doble envío y actualiza después de aceptar', async () => {
  let finish: (result: Response) => void = () => {}
  const pending = new Promise<Response>(resolve => { finish = resolve })
  vi.mocked(apiRequest).mockImplementation(async (path, init) => {
    if (init?.method === 'POST') return pending
    return response(path.endsWith('availability') ? { enabled: true } : { orders: [order] })
  })
  const changed = vi.fn()
  render(<PaymentSimulation onChanged={changed} />)
  fireEvent.click(await screen.findByText('Simulación de pago — desarrollo'))
  await screen.findByRole('option', { name: 'WEB-1 · Centro' })
  fireEvent.change(screen.getByRole('combobox'), { target: { value: order.id } })
  const button = screen.getByRole('button', { name: 'Simular pago aceptado' })
  expect(button.hasAttribute('disabled')).toBe(true)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(button)
  fireEvent.click(button)
  expect(vi.mocked(apiRequest).mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
  finish(response({ order: { status: 'PAGADO' }, transfer_ids: ['transfer-1'] }))
  await screen.findByText(/1 transferencias automáticas/)
  expect(changed).toHaveBeenCalledTimes(1)
})

