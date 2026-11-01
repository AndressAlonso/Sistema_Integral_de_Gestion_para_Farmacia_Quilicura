import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import CartItem from '../components/CartItem'
import { useCart } from '../hooks/useCart'
import type { CartState } from '../hooks/useCart'
import type { CartLine } from '../types/cart'

vi.mock('../hooks/useCart', () => ({ useCart: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
const line: CartLine = { product_id: 'p', name: 'Producto', quantity: 1, unit_price: '100', subtotal: '100', local_available: null, global_available: 10, requires_transfer: false, valid: true, issues: [] }
function setup() {
  const change = vi.fn()
  vi.mocked(useCart).mockReturnValue({ change, remove: vi.fn() } as unknown as CartState)
  render(<CartItem line={line} />)
  return change
}
it('muestra la foto con carga diferida y una alternativa si falla sin reintentar al cambiar cantidad', () => {
  setup()
  const photo = screen.getByRole('img', { name: 'Imagen de Producto' })
  expect(photo.getAttribute('src')).toBe('/api/ecommerce/products/p/image')
  expect(photo.getAttribute('loading')).toBe('lazy')
  fireEvent.error(photo)
  expect(screen.queryByRole('img')).toBeNull()
  expect(screen.getByText('Sin imagen')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Aumentar cantidad de Producto' }))
  expect(screen.queryByRole('img')).toBeNull()
})
it('actualiza con más y menos sin botón de guardar y respeta el mínimo', () => {
  const change = setup()
  expect(screen.getByRole('button', { name: 'Reducir cantidad de Producto' }).hasAttribute('disabled')).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Aumentar cantidad de Producto' }))
  expect(change).toHaveBeenLastCalledWith('p', 2)
  fireEvent.click(screen.getByRole('button', { name: 'Reducir cantidad de Producto' }))
  expect(change).toHaveBeenLastCalledWith('p', 1)
  expect(screen.queryByRole('button', { name: 'Actualizar cantidad' })).toBeNull()
})
it('guarda la cantidad escrita al salir del campo y rechaza cantidades inválidas', () => {
  const change = setup()
  const input = screen.getByRole('spinbutton')
  fireEvent.change(input, { target: { value: '12' } })
  fireEvent.blur(input)
  expect(change).toHaveBeenLastCalledWith('p', 12)
  change.mockClear()
  fireEvent.change(input, { target: { value: '100' } })
  fireEvent.blur(input)
  expect(change).not.toHaveBeenCalled()
  expect(screen.getByRole('alert').textContent).toContain('entre 1 y 99')
})
