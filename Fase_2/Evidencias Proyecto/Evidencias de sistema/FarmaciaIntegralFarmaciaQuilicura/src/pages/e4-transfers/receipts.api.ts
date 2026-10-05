import { ApiError, apiRequest } from '../../services/http'

export interface ReceiptProduct { id: string; name: string; sku: string }
export async function receiptProducts(): Promise<ReceiptProduct[]> {
  const data: { products: ReceiptProduct[] } = await (await apiRequest('/api/goods-receipts/options')).json()
  return data.products
}

export interface ReceiptItem {
  product_id: string
  lot_number: string
  expiration_date: string
  quantity: number
}
export interface ReceiptInput {
  request_id: string
  branch_id: string
  supplier: string
  document_type: 'GUIA' | 'FACTURA'
  document_number: string
  document_date: string
  items: ReceiptItem[]
}
export interface Receipt extends Omit<ReceiptInput, 'request_id'> {
  id: string
  user_id: string
  created_at: string
}
export async function createReceipt(input: ReceiptInput): Promise<Receipt> {
  let response: Response
  try {
    response = await fetch('/api/goods-receipts', {
      method: 'POST', credentials: 'include', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
      signal: AbortSignal.timeout(15_000),
    })
  } catch {
    throw new ApiError('No pudimos confirmar la entrada. Reintenta la misma solicitud; no se duplicarán las unidades.')
  }
  if (!response.ok) {
    const fallback = response.status >= 500 ? 'No pudimos confirmar la entrada. Reintenta la misma solicitud.' : 'No se pudo registrar la entrada.'
    const data: unknown = await response.json().catch(() => null)
    const detail = response.status < 500 && data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string' ? data.detail : fallback
    throw new ApiError(detail, response.status)
  }
  return response.json()
}
