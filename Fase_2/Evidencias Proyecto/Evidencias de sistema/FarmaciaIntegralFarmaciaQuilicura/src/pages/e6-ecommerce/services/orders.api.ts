import { apiRequest } from '../../../services/http'
import type { CartDraft } from '../types/cart'
import type { GuestData } from '../types/guest'
import type { OnlineOrderSummary } from '../types/order-history'

export interface OnlineOrder extends OnlineOrderSummary {
  items: { product_id: string; name: string; quantity: number; unit_price: string; subtotal: string; promotion: string | null }[]
}
export interface OrderAttempt { request_id: string; request_token: string }
const storageKey = 'sigfq_pending_order'
export function pendingOrder(): OrderAttempt | null {
  try {
    const data = JSON.parse(sessionStorage.getItem(storageKey) ?? 'null')
    return data && /^[0-9a-f-]{36}$/i.test(data.request_id) && /^[0-9a-f]{64}$/i.test(data.request_token) ? data : null
  } catch { return null }
}
export function orderAttempt(): OrderAttempt {
  const saved = pendingOrder()
  if (saved) return saved
  const attempt = { request_id: crypto.randomUUID(), request_token: Array.from(crypto.getRandomValues(new Uint8Array(32)), n => n.toString(16).padStart(2, '0')).join('') }
  sessionStorage.setItem(storageKey, JSON.stringify(attempt))
  return attempt
}
export function finishAttempt() { sessionStorage.removeItem(storageKey) }
export async function createOrder(cart: CartDraft, total: string, guest: GuestData | null, attempt: OrderAttempt): Promise<OnlineOrder> {
  return (await apiRequest('/api/customers/orders', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...attempt, items: cart.items, pickup_branch_id: cart.pickup_branch_id,
      expected_total: total, guest, confirmed: true }) }, {}, true)).json()
}
export async function recoverOrder(attempt: OrderAttempt): Promise<OnlineOrder> {
  return (await apiRequest(`/api/customers/orders/${encodeURIComponent(attempt.request_id)}/status`, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ request_token: attempt.request_token }) }, {}, true)).json()
}
