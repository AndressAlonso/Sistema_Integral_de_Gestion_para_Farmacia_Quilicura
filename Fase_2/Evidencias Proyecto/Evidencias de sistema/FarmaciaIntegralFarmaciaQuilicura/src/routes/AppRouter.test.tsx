import { StrictMode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AppRouter from './AppRouter'
import type { AuthSession } from '../pages/e1-access-users-branches/auth/login.api'

// Exercise the real router, login, guard, layout and permission-aware landing page.
vi.mock('../pages/e9-dashboard/DashboardPage', () => ({ default: () => <h1>Dashboard de prueba</h1> }))

let session: AuthSession
let authenticated: boolean
let unavailable: boolean
let requests: string[]
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json' },
})

beforeEach(() => {
  authenticated = true
  unavailable = false
  requests = []
  session = {
    user: { id: 'test', email: 'interno@example.com', name: 'Operador', roles: ['ADMINISTRADOR'],
      permissions: [], branch_id: 'branch', branch_name: 'Sucursal de prueba' },
    expires_at: new Date(Date.now() + 3_600_000).toISOString(),
  }
  vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    requests.push(`${init?.method ?? 'GET'} ${path}`)
    // Fail boundedly if a regression creates the /login <-> /session cycle.
    if (requests.length > 12) throw new Error('Repeated authentication requests')
    if (unavailable) return json({}, 503)
    if (path === '/api/auth/me') return authenticated ? json(session) : json({}, 401)
    if (path === '/api/auth/login') {
      const body = JSON.parse(String(init?.body))
      if (body.password !== 'valid-test-password') return json({}, 401)
      authenticated = true
      return json(session)
    }
    if (path === '/api/auth/logout') { authenticated = false; return new Response(null, { status: 204 }) }
    throw new Error(`Unexpected request: ${path}`)
  }))
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear() })

function mount(path: string) {
  window.history.replaceState(null, '', path)
  return render(<StrictMode><AppRouter /></StrictMode>)
}

describe('E1-H1: entrada interna sin ciclos de navegación', () => {
  it.each(['/session', '/login', '/admin/dashboard'])('abre dashboard con sesión válida desde %s', async path => {
    mount(path)
    await screen.findByRole('heading', { name: 'Dashboard de prueba' })
    expect(window.location.pathname).toBe('/admin/dashboard')
    expect(requests.length).toBeLessThanOrEqual(4) // StrictMode validates mount twice in development.
  })

  it('muestra las secciones permitidas cuando no tiene acceso al dashboard', async () => {
    session.user.roles = ['VENDEDOR']
    session.user.permissions = ['pos.operar']
    mount('/session')
    await screen.findByRole('heading', { name: 'Bienvenido, Operador' })
    expect(window.location.pathname).toBe('/session')
    expect(screen.getAllByRole('link', { name: 'POS / Ventas' }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('link', { name: 'Dashboard' })).toBeNull()
    expect(requests.length).toBeLessThanOrEqual(2)
  })

  it('vuelve a la entrada interna al abrir una sección sin permisos, sin pasar por login', async () => {
    session.user.roles = []
    mount('/admin/dashboard')
    await screen.findByRole('heading', { name: 'Bienvenido, Operador' })
    expect(window.location.pathname).toBe('/session')
    expect(requests.length).toBeLessThanOrEqual(2)
  })

  it('inicia y cierra sesión, y protege el acceso directo después del cierre', async () => {
    authenticated = false
    const view = mount('/session')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: session.user.email } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'valid-test-password' } })
    fireEvent.click(screen.getByRole('button', { name: /Ingresar al sistema/ }))
    await screen.findByRole('heading', { name: 'Dashboard de prueba' })
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    expect(window.location.pathname).toBe('/login')
    expect(requests.filter(r => r === 'POST /api/auth/login')).toHaveLength(1)
    expect(requests.filter(r => r === 'POST /api/auth/logout')).toHaveLength(1)
    view.unmount()
    requests = []
    mount('/admin/dashboard')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    expect(window.location.pathname).toBe('/login')
  })

  it('rechaza credenciales incorrectas sin navegar a /session', async () => {
    authenticated = false
    mount('/login')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: session.user.email } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'wrong-password' } })
    fireEvent.click(screen.getByRole('button', { name: /Ingresar al sistema/ }))
    await screen.findByText('Correo o contraseña incorrectos.')
    expect(window.location.pathname).toBe('/login')
  })

  it('deja el formulario visible cuando la sesión ya expiró', async () => {
    session.expires_at = new Date(Date.now() - 1000).toISOString()
    mount('/session')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    expect(window.location.pathname).toBe('/login')
    expect(requests.length).toBeLessThanOrEqual(4)
  })

  it('permite reintentar un fallo del servidor sin un ciclo de redirecciones', async () => {
    unavailable = true
    mount('/session')
    const retry = await screen.findByRole('button', { name: 'Reintentar' })
    expect(window.location.pathname).toBe('/session')
    unavailable = false
    fireEvent.click(retry)
    await waitFor(() => expect(window.location.pathname).toBe('/admin/dashboard'))
    expect(requests.length).toBeLessThanOrEqual(3)
  })
})
