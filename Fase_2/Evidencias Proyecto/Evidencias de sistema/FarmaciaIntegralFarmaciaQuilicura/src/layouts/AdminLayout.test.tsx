import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import AdminLayout from './AdminLayout'

const session = { user: { email: 'admin@example.test', permissions: ['pedidos.consultar'], roles: ['ADMINISTRADOR'] } }
let mobile = true
let resize: () => void
const originalShow = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeEach(() => {
  localStorage.clear()
  mobile = true
  vi.stubGlobal('matchMedia', () => ({
    get matches() { return mobile },
    addEventListener: (_: string, listener: () => void) => { resize = listener },
    removeEventListener: vi.fn(),
  }))
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.removeAttribute('open'); this.dispatchEvent(new Event('close')) } })
})
afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals()
  if (originalShow) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', originalShow)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (originalClose) Object.defineProperty(HTMLDialogElement.prototype, 'close', originalClose)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})

function mount() {
  render(<MemoryRouter initialEntries={['/admin/orders']}><Routes>
    <Route element={<Outlet context={session} />}><Route element={<AdminLayout />}>
      <Route path="/admin/orders" element={<p>Listado de pedidos</p>} />
      <Route path="/admin/dashboard" element={<p>Indicadores</p>} />
    </Route></Route>
  </Routes></MemoryRouter>)
}

it('abre el menú móvil sin cambiar la preferencia del escritorio y lo cierra al navegar', () => {
  localStorage.setItem('sigfq-menu-expanded', 'true')
  mount()
  const toggle = screen.getByRole('button', { name: 'Menú de navegación' })
  expect(toggle.getAttribute('aria-expanded')).toBe('false')
  fireEvent.click(toggle)
  const dialog = screen.getByRole('dialog', { name: 'Menú principal' })
  expect(localStorage.getItem('sigfq-menu-expanded')).toBe('true')
  expect(within(dialog).queryByRole('link', { name: 'Inicio' })).toBeNull()
  fireEvent.click(within(dialog).getByRole('link', { name: 'Resumen' }))
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(screen.getByText('Indicadores')).toBeTruthy()
})

it('mantiene el recorrido de Tab dentro del menú y lo cierra al pasar a escritorio', () => {
  mount()
  fireEvent.click(screen.getByRole('button', { name: 'Menú de navegación' }))
  const dialog = screen.getByRole('dialog')
  const first = within(dialog).getByRole('button', { name: 'Cerrar menú' })
  const links = within(dialog).getAllByRole('link')
  const last = links[links.length - 1]
  last.focus()
  fireEvent.keyDown(last, { key: 'Tab' })
  expect(document.activeElement).toBe(first)
  fireEvent.keyDown(first, { key: 'Tab', shiftKey: true })
  expect(document.activeElement).toBe(last)
  mobile = false
  act(() => resize())
  expect(screen.queryByRole('dialog')).toBeNull()
})
