import { ApiError as AuthError, apiRequest } from '../../../services/http'

export { ApiError as AuthError } from '../../../services/http'

export interface AuthSession {
  user: { id: string; email: string; name: string; permissions: string[]; roles: string[]; branch_id: string; branch_name: string }
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
    if (typeof data.user?.id !== 'string' || typeof data.user?.email !== 'string' ||
      !Array.isArray(data.user?.roles) ||
      !data.user.roles.every(role => typeof role === 'string') ||
      !Array.isArray(data.user?.permissions) ||
      !data.user.permissions.every(permission => typeof permission === 'string') ||
      typeof data.user.branch_id !== 'string' || !data.user.branch_id ||
      typeof data.user.branch_name !== 'string' ||
      !Number.isFinite(Date.parse(data.expires_at))) throw new Error('Invalid session')
    return data
  } catch {
    throw new AuthError('El servidor no pudo confirmar la sesión. Intenta nuevamente.')
  }
}

export const login = (email: string, password: string) => requestSession('login', { email, password })
export const getSession = () => requestSession('me')
export const logout = async () => { await request('logout') }
