import { ApiError, apiRequest } from '../../services/http'

export interface StockLot {
  id: string; product_id: string; product_name: string; sku: string; branch_id: string
  number: string; expiration_date: string; quantity: number
}
export interface OperationOptions {
  products: { id: string; name: string; sku: string; branch_id: string; quantity: number }[]
  branches: { id: string; name: string }[]; lots: StockLot[]; can_receive: boolean; can_adjust: boolean
}
export interface AdjustmentInput {
  request_id: string; branch_id: string; reason: string
  items: { lot_id: string; expected_quantity: number; new_quantity: number }[]
}
export interface Adjustment {
  id: string; branch_id: string; user_id: string; reason: string; created_at: string
  items: { lot_id: string; lot_number: string; product_id: string; product_name: string; previous_quantity: number; new_quantity: number; difference: number }[]
}
export const operationOptions = async (): Promise<OperationOptions> => (await apiRequest('/api/stock-operations/options')).json()

export async function createAdjustment(input: AdjustmentInput): Promise<Adjustment> {
  let response: Response
  try {
    response = await fetch('/api/inventory-adjustments', {
      method: 'POST', credentials: 'include', cache: 'no-store', signal: AbortSignal.timeout(15_000),
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
    })
  } catch { throw new ApiError('No pudimos confirmar el ajuste. Reintenta la misma solicitud; no se duplicará.') }
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null)
    const detail = response.status < 500 && data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
      ? data.detail : 'No pudimos confirmar el ajuste. Reintenta la misma solicitud.'
    throw new ApiError(detail, response.status)
  }
  return response.json()
}
