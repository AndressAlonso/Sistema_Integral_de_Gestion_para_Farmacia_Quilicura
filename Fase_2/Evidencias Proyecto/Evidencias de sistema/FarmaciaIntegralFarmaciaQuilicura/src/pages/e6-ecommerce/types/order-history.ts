/** E6-H5: contrato propuesto; requiere confirmación e integración con E7-H1. */
export interface OnlineOrderSummary {
  id: string
  number: string
  created_at: string
  status: string
  total: string
  currency: string
  pickup_branch: { id: string; name: string }
}

export interface OrderHistoryResponse {
  orders: OnlineOrderSummary[]
  next_cursor: string | null
}

export interface OrderHistoryQuery {
  cursor?: string
  limit?: number
}
