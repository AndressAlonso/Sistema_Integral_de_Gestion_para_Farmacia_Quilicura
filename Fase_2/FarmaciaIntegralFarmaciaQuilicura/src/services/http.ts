export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest(path: string, init: RequestInit = {}, messages: Record<number, string> = {}): Promise<Response> {
  let response: Response
  try {
    response = await fetch(path, { ...init, credentials: 'include', signal: AbortSignal.timeout(10_000), cache: 'no-store' })
  } catch {
    throw new ApiError('No pudimos conectar con el servidor. Revisa tu conexión e intenta nuevamente.')
  }
  if (!response.ok) {
    if (response.status === 429) {
      const seconds = Number(response.headers.get('Retry-After'))
      const minutes = Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds / 60) : 15
      throw new ApiError(`Demasiados intentos de inicio de sesión. Espera ${minutes} ${minutes === 1 ? 'minuto' : 'minutos'} antes de volver a intentar.`, 429)
    }
    const defaults: Record<number, string> = {
      401: 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.',
      403: 'No tienes permiso para realizar esta acción.',
      404: 'El registro solicitado no existe.',
    }
    throw new ApiError(messages[response.status] ?? defaults[response.status] ?? 'No pudimos completar la solicitud. Intenta nuevamente más tarde.', response.status)
  }
  return response
}
