import { apiRequest } from '../../../services/http'
import type { OrderHistoryQuery, OrderHistoryResponse } from '../types/order-history'

/** Historial privado de pedidos persistidos; el backend filtra por la sesión. */
export async function getOrderHistory(query: OrderHistoryQuery = {}): Promise<OrderHistoryResponse> {
  const params = new URLSearchParams()
  if (query.cursor) params.set('cursor', query.cursor)
  if (query.limit !== undefined) params.set('limit', String(query.limit))
  const suffix = params.size ? `?${params}` : ''
  return (await apiRequest(`/api/customers/orders${suffix}`)).json()
}
