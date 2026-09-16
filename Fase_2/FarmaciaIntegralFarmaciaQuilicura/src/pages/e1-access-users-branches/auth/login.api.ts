export interface AuthSession {
  user: { id: number; email: string }
  expires_at: string
}

export class AuthError extends Error {
  readonly status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'AuthError'
    this.status = status
  }
}

async function request(path: string, credentials?: { email: string; password: string }): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`/api/auth/${path}`, {
      method: credentials || path === 'logout' ? 'POST' : 'GET',
      credentials: 'include',
      headers: credentials ? { 'Content-Type': 'application/json' } : undefined,
      body: credentials ? JSON.stringify(credentials) : undefined,
      signal: AbortSignal.timeout(10_000),
      cache: 'no-store',
    })
  } catch {
    throw new AuthError('No pudimos conectar con el servidor. Revisa tu conexión e intenta nuevamente.')
  }
  if (!response.ok) {
    if (response.status === 429) {
      const seconds = Number(response.headers.get('Retry-After'))
      const minutes = Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds / 60) : 15
      throw new AuthError(`Demasiados intentos de inicio de sesión. Espera ${minutes} ${minutes === 1 ? 'minuto' : 'minutos'} antes de volver a intentar.`, 429)
    }
    const messages: Record<number, string> = {
      400: 'Revisa el correo y la contraseña ingresados.',
      401: credentials ? 'Correo o contraseña incorrectos.' : 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.',
      403: 'No se pudo autorizar el acceso. Contacta al administrador.',
      422: 'Revisa el correo y la contraseña ingresados.',
    }
    throw new AuthError(messages[response.status] ?? 'No pudimos completar la solicitud. Intenta nuevamente más tarde.', response.status)
  }
  return response
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
