import { apiRequest } from '../../../services/http'
import type { OrderHistoryQuery, OrderHistoryResponse } from '../types/order-history'

/** Contrato futuro de E7-H1. No invocar hasta que exista la persistencia y el endpoint real. */
export async function getOrderHistory(query: OrderHistoryQuery = {}): Promise<OrderHistoryResponse> {
  const params = new URLSearchParams()
  if (query.cursor) params.set('cursor', query.cursor)
  if (query.limit !== undefined) params.set('limit', String(query.limit))
  const suffix = params.size ? `?${params}` : ''
  return (await apiRequest(`/api/customers/orders${suffix}`)).json()
}
