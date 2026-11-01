import { apiRequest } from '../../services/http'
import type { OnlineOrder } from '../e6-ecommerce/services/orders.api'

export const orderStates: Record<string, string> = {
  PENDIENTE_PAGO: 'Pendiente de pago', PAGADO: 'Pagado', EN_PREPARACION: 'En preparación',
  LISTO_PARA_RETIRO: 'Listo para retiro', CANCELADO: 'Cancelado',
}
export const orderStateLabel = (state: string) => orderStates[state] ?? state
export type OrderAction = 'preparation' | 'ready'
export type OrderSort = 'newest' | 'state_asc' | 'state_desc' | 'branch_asc' | 'branch_desc'
export interface OrderDetail extends OnlineOrder {
  customer: { name: string; email: string }
  actions: OrderAction[]
  ready_blocked_reason: string | null
  transfers: { id: string; status: string; origin: string; destination: string }[]
  history: { at: string; actor: string; previous: string | null; status: string }[]
}
export interface OrderList {
  orders: OnlineOrder[]; total: number; page: number; limit: number
  branches: { id: string; name: string }[]
}
export async function listOrders(states: string[], branches: string[] | null, page: number, sort: OrderSort = 'newest'): Promise<OrderList> {
  const query = new URLSearchParams({ page: String(page), limit: '15' })
  states.forEach(state => query.append('states', state))
  query.set('sort', sort)
  branches?.forEach(branch => query.append('branch_ids', branch))
  return (await apiRequest(`/api/orders?${query}`, {}, {}, true)).json()
}
export async function getOrder(id: string): Promise<OrderDetail> {
  return (await apiRequest(`/api/orders/${encodeURIComponent(id)}`)).json()
}
export async function changeOrder(order: OrderDetail, action: OrderAction): Promise<OrderDetail> {
  return (await apiRequest(`/api/orders/${encodeURIComponent(order.id)}/${action}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_state: order.status }),
  }, {}, true)).json()
}
