import { StrictMode } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CartContinuation from '../components/CartContinuation'
import CustomerAuthForm from '../components/CustomerAuthForm'
import CustomerSessionProvider from '../components/CustomerSessionProvider'
import PublicHeader from '../components/PublicHeader'
import { useCustomerSession } from '../hooks/useCustomerSession'
import EcommerceLayout from '../layouts/EcommerceLayout'
import GuestContinuationPage from '../pages/GuestContinuationPage'
import OrderHistoryPage from '../pages/OrderHistoryPage'
import type { CustomerSession } from '../types/customer'

const session: CustomerSession = {
  customer: { id: 'customer-test', name: 'Cliente de regresión', email: 'regression@example.com' },
  expires_at: '2099-01-01T00:00:00Z',
}
const requests: string[] = []
let authenticated = true
let initialSession: Promise<Response> | null = null
const json = (value: unknown) => new Response(JSON.stringify(value), {
  status: 200, headers: { 'Content-Type': 'application/json' },
})

beforeEach(() => {
  requests.length = 0
  authenticated = true
  initialSession = null
  sessionStorage.clear()
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    requests.push(`${init?.method ?? 'GET'} ${path}`)
    if (path === '/api/customers/me') {
      if (initialSession) return initialSession
      return authenticated ? json(session) : new Response(null, { status: 401 })
    }
    if (path === '/api/customers/login') { authenticated = true; return json(session) }
    if (path === '/api/customers/logout') { authenticated = false; return new Response(null, { status: 204 }) }
    if (path === '/api/ecommerce/cart/validate') {
      return json({ valid: false, pickup_branch: null, items: [], total: null, currency: 'CLP', issues: [] })
    }
    throw new Error(`Solicitud inesperada: ${path}`)
  }))
})

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear() })

function mount(section: 'cart' | 'guest' | 'history') {
  const page = section === 'cart' ? <><PublicHeader /><CartContinuation /></>
    : section === 'guest' ? <GuestContinuationPage /> : <OrderHistoryPage />
  return render(<StrictMode><MemoryRouter><Routes>
    <Route element={<EcommerceLayout />}><Route index element={page} /></Route>
  </Routes></MemoryRouter></StrictMode>)
}

describe('Sesión compartida del ecommerce', () => {
  it.each(['cart', 'guest', 'history'] as const)('sincroniza el logout del encabezado y %s sin recargar', async section => {
    mount(section)
    await screen.findByText(session.customer.name)
    expect(screen.getByRole('link', { name: 'Mis pedidos' })).toBeTruthy()
    expect(requests.filter(path => path === 'GET /api/customers/me')).toHaveLength(1)
    if (section === 'cart') expect(screen.getByText(/Continuarás con tu cuenta/)).toBeTruthy()
    if (section === 'guest') expect(screen.getByText(/Hay una sesión de cliente activa/)).toBeTruthy()
    if (section === 'history') expect(screen.getByText(/El historial estará disponible/)).toBeTruthy()
    const documentBefore = document.documentElement
    const locationBefore = window.location.href
    const beforeUnload = vi.fn()
    window.addEventListener('beforeunload', beforeUnload)
    try {
      fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
      await screen.findByRole('link', { name: 'Crear cuenta' })
      expect(screen.queryByText(session.customer.name)).toBeNull()
      expect(screen.queryByRole('link', { name: 'Mis pedidos' })).toBeNull()
      expect(within(screen.getByRole('navigation', { name: 'Navegación pública' })).getByRole('link', { name: 'Iniciar sesión' })).toBeTruthy()
      expect(screen.getByRole('link', { name: 'Acceso interno' })).toBeTruthy()
      if (section === 'cart') {
        expect(screen.getByText('Continuar sin cuenta')).toBeTruthy()
        expect(screen.queryByText(/Continuarás con tu cuenta/)).toBeNull()
      }
      if (section === 'guest') {
        expect(screen.getByRole('textbox', { name: /Nombre/ })).toBeTruthy()
        expect(screen.queryByText(/Hay una sesión de cliente activa/)).toBeNull()
      }
      if (section === 'history') {
        expect(screen.getByText('Acceso requerido')).toBeTruthy()
        expect(screen.queryByText(/El historial estará disponible/)).toBeNull()
      }
      expect(requests.filter(path => path.includes('logout'))).toEqual(['POST /api/customers/logout'])
      expect(requests.some(path => path.includes('/api/auth/'))).toBe(false)
      expect(requests.some(path => path.includes('/orders'))).toBe(false)
      expect(requests.filter(path => path === 'GET /api/customers/me')).toHaveLength(1)
      expect(document.documentElement).toBe(documentBefore)
      expect(window.location.href).toBe(locationBefore)
      expect(beforeUnload).not.toHaveBeenCalled()
    } finally { window.removeEventListener('beforeunload', beforeUnload) }
  })

  it('actualiza la sesión al iniciar sesión antes de navegar al catálogo', async () => {
    authenticated = false
    render(<MemoryRouter initialEntries={['/tienda/iniciar-sesion']}><Routes>
      <Route element={<EcommerceLayout />}>
        <Route path="/tienda/iniciar-sesion" element={<CustomerAuthForm />} />
        <Route path="/tienda" element={<PublicHeader />} />
      </Route>
    </Routes></MemoryRouter>)
    await screen.findByRole('link', { name: 'Crear cuenta' })
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: session.customer.email } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'Solo-un-valor-de-prueba' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Iniciar sesión' }).closest('form')!)
    await screen.findByText(session.customer.name)
    expect(screen.getByRole('link', { name: 'Mis pedidos' })).toBeTruthy()
    expect(requests.filter(path => path === 'GET /api/customers/me')).toHaveLength(1)
  })

  it('descarta una respuesta inicial tardía después del logout', async () => {
    let resolveSession!: (response: Response) => void
    initialSession = new Promise(resolve => { resolveSession = resolve })
    function SessionControls() {
      const { customer, updateCustomer, logout } = useCustomerSession()
      return <><p>{customer ? 'Consumidor autenticado' : 'Consumidor sin sesión'}</p>
        <button onClick={() => updateCustomer(session.customer)}>Actualizar sesión</button>
        <button onClick={() => { void logout() }}>Cerrar sesión de prueba</button></>
    }
    render(<CustomerSessionProvider><SessionControls /></CustomerSessionProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar sesión' }))
    expect(screen.getByText('Consumidor autenticado')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión de prueba' }))
    await screen.findByText('Consumidor sin sesión')
    await act(async () => { resolveSession(json(session)); await initialSession })
    expect(screen.queryByText('Consumidor autenticado')).toBeNull()
    expect(requests.filter(path => path === 'GET /api/customers/me')).toHaveLength(1)
  })

  it('comparte la ausencia de sesión cuando el logout responde 401', async () => {
    mount('cart')
    await screen.findByText(session.customer.name)
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(new Response(null, { status: 401 }))
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    await waitFor(() => expect(screen.queryByText(session.customer.name)).toBeNull())
    expect(screen.getByText('Continuar sin cuenta')).toBeTruthy()
  })

  it('descarta también una comprobación de sesión tardía iniciada por otro consumidor', async () => {
    let resolveSession!: (response: Response) => void
    function SessionControls() {
      const { customer, refreshCustomer, logout } = useCustomerSession()
      return <><p>{customer ? 'Consumidor autenticado' : 'Consumidor sin sesión'}</p>
        <button onClick={() => { void refreshCustomer() }}>Comprobar sesión</button>
        <button onClick={() => { void logout() }}>Cerrar sesión de prueba</button></>
    }
    render(<CustomerSessionProvider><SessionControls /></CustomerSessionProvider>)
    await screen.findByText('Consumidor autenticado')
    initialSession = new Promise(resolve => { resolveSession = resolve })
    fireEvent.click(screen.getByRole('button', { name: 'Comprobar sesión' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión de prueba' }))
    await screen.findByText('Consumidor sin sesión')
    await act(async () => { resolveSession(json(session)); await initialSession })
    expect(screen.queryByText('Consumidor autenticado')).toBeNull()
  })
})
