import { apiRequest } from '../../../services/http'
import type { OrderAttempt } from './orders.api'

export function safeCheckoutUrl(value: unknown): string {
  if (typeof value !== 'string') throw new Error('El enlace de pago no es válido.')
  const url = new URL(value)
  if (url.protocol !== 'https:' || !['www.mercadopago.cl', 'mercadopago.cl'].includes(url.hostname)
    || url.username || url.password || url.port || url.hash) {
    throw new Error('El enlace de pago no es válido.')
  }
  return url.href
}

export async function createCheckout(attempt: OrderAttempt): Promise<string> {
  const response = await apiRequest(`/api/customers/orders/${encodeURIComponent(attempt.request_id)}/checkout`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_token: attempt.request_token }),
  }, {
    502: 'No pudimos confirmar el enlace. Consulta el estado antes de volver a intentar.',
    503: 'El pago online no está disponible en este momento.',
  }, true)
  const data: unknown = await response.json()
  if (!data || typeof data !== 'object' || !('order_id' in data) || data.order_id !== attempt.request_id
    || !('checkout_url' in data)) throw new Error('La respuesta de pago no corresponde al pedido.')
  return safeCheckoutUrl(data.checkout_url)
}

export function redirectToCheckout(url: string) {
  window.location.assign(safeCheckoutUrl(url))
}
