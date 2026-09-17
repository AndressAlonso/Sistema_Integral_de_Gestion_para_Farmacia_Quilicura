import { ApiError as AuthError, apiRequest } from '../../../services/http'

export { ApiError as AuthError } from '../../../services/http'

export interface AuthSession {
  user: { id: number; email: string }
  expires_at: string
}

async function request(path: string, credentials?: { email: string; password: string }): Promise<Response> {
  return apiRequest(`/api/auth/${path}`, {
    method: credentials || path === 'logout' ? 'POST' : 'GET',
    headers: credentials ? { 'Content-Type': 'application/json' } : undefined,
    body: credentials ? JSON.stringify(credentials) : undefined,
  }, {
    400: 'Revisa el correo y la contraseña ingresados.',
    401: credentials ? 'Correo o contraseña incorrectos.' : 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.',
    403: 'No se pudo autorizar el acceso. Contacta al administrador.',
    422: 'Revisa el correo y la contraseña ingresados.',
  })
}

async function requestSession(path: string, credentials?: { email: string; password: string }): Promise<AuthSession> {
  const response = await request(path, credentials)
  try {
    const data: AuthSession = await response.json()
    if (!Number.isInteger(data.user?.id) || typeof data.user?.email !== 'string' ||
      !Number.isFinite(Date.parse(data.expires_at))) throw new Error('Invalid session')
    return data
  } catch {
    throw new AuthError('El servidor no pudo confirmar la sesión. Intenta nuevamente.')
  }
}

export const login = (email: string, password: string) => requestSession('login', { email, password })
export const getSession = () => requestSession('me')
export const logout = async () => { await request('logout') }
