import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import OrderPickupDialog from './OrderPickupDialog'
import { confirmPickup, validatePickup, type PickupPreview } from './orders.api'

vi.mock('./orders.api', () => ({ confirmPickup: vi.fn(), validatePickup: vi.fn() }))
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  vi.mocked(validatePickup).mockReset()
  vi.mocked(confirmPickup).mockReset()
})
afterEach(cleanup)
const order: PickupPreview = { id: 'order', number: 'WEB-QA', status: 'LISTO_PARA_RETIRO', created_at: '2026-11-03T12:00:00Z', currency: 'CLP', total: '1000', pickup_branch: { id: 'branch', name: 'Centro' }, customer: { name: 'Invitado QA', email: 'qa@example.com' }, items: [{ product_id: 'product', name: 'Paracetamol', quantity: 2, unit_price: '500', subtotal: '1000', promotion: null }] }

it('revisa productos y exige confirmación antes de entregar una sola vez', async () => {
  vi.mocked(validatePickup).mockResolvedValue(order)
  vi.mocked(confirmPickup).mockResolvedValue({ ...order, status: 'RETIRADO' })
  const changed = vi.fn()
  render(<OrderPickupDialog onClose={vi.fn()} onChanged={changed} />)
  fireEvent.change(screen.getByLabelText('QR o código de retiro'), { target: { value: 'QR-del-cliente' } })
  fireEvent.click(screen.getByRole('button', { name: 'Validar código' }))
  expect(await screen.findByText(/Paracetamol/)).toBeTruthy()
  const confirm = screen.getByRole('button', { name: 'Confirmar retiro' }) as HTMLButtonElement
  expect(confirm.disabled).toBe(true)
  expect(confirmPickup).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(confirm); fireEvent.click(confirm)
  expect(await screen.findByRole('status')).toBeTruthy()
  expect(confirmPickup).toHaveBeenCalledExactlyOnceWith('QR-del-cliente', 'order')
  expect(changed).toHaveBeenCalledOnce()
})

it('cambiar el código invalida la revisión anterior', async () => {
  vi.mocked(validatePickup).mockResolvedValue(order)
  render(<OrderPickupDialog onClose={vi.fn()} onChanged={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('QR o código de retiro'), { target: { value: 'QR-1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Validar código' }))
  await screen.findByText(/Paracetamol/)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.change(screen.getByLabelText('QR o código de retiro'), { target: { value: 'QR-2' } })
  expect(screen.queryByRole('checkbox')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Confirmar retiro' })).toBeNull()
  expect(confirmPickup).not.toHaveBeenCalled()
})

it('muestra el rechazo del servidor sin confirmar la entrega', async () => {
  vi.mocked(validatePickup).mockRejectedValue(new Error('Este pedido ya fue retirado.'))
  render(<OrderPickupDialog onClose={vi.fn()} onChanged={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('QR o código de retiro'), { target: { value: 'QR-usado' } })
  fireEvent.click(screen.getByRole('button', { name: 'Validar código' }))
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('ya fue retirado'))
  expect(confirmPickup).not.toHaveBeenCalled()
})

it('permite escribir el número del correo conservando los ceros iniciales', async () => {
  vi.mocked(validatePickup).mockResolvedValue(order)
  vi.mocked(confirmPickup).mockResolvedValue({ ...order, status: 'RETIRADO' })
  render(<OrderPickupDialog onClose={vi.fn()} onChanged={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('QR o código de retiro'), { target: { value: '0000 1234 0000 5678' } })
  fireEvent.click(screen.getByRole('button', { name: 'Validar código' }))
  await screen.findByText(/Paracetamol/)
  expect(validatePickup).toHaveBeenCalledExactlyOnceWith('0000 1234 0000 5678')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar retiro' }))
  await screen.findByRole('status')
  expect(confirmPickup).toHaveBeenCalledExactlyOnceWith('0000 1234 0000 5678', 'order')
})
