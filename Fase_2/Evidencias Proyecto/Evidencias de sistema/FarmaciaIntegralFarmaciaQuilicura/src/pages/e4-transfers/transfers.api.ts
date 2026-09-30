import { ApiError } from '../../services/http'

export type TransferState = 'SOLICITADA' | 'AUTORIZADA' | 'EN_TRANSITO' | 'RECIBIDA' | 'RECHAZADA'
export type TransferAction = 'approve' | 'reject' | 'dispatch' | 'receive'
export interface TransferInput {
  request_id: string; origin_id: string; destination_id: string
  items: { product_id: string; quantity: number }[]
}
export interface Transfer {
  id: string; origin_id: string; origin_name: string; destination_id: string; destination_name: string
  state: TransferState; created_at: string; requested_by: string; rejection_reason: string | null
  actions: TransferAction[]
  items: { product_id: string; product_name: string; sku: string; quantity: number
    lots: { number: string; expiration_date: string; quantity: number }[] }[]
  timeline: { event: string; at: string; user: string }[]
}
export interface TransferOptions {
  branches: { id: string; name: string }[]
  stock: { product_id: string; product_name: string; sku: string; branch_id: string; available: number }[]
  origin_ids: string[]; can_create: boolean
}
export const states: Record<TransferState, string> = {
  SOLICITADA: 'Solicitada', AUTORIZADA: 'Autorizada', EN_TRANSITO: 'En tránsito', RECIBIDA: 'Recibida', RECHAZADA: 'Rechazada',
}
export const actions: Record<TransferAction, string> = {
  approve: 'Aprobar', reject: 'Rechazar', dispatch: 'Confirmar despacho', receive: 'Confirmar recepción',
}
export const transferCode = (id: string) => `TR-${id.slice(0, 8).toUpperCase()}`
export const units = (transfer: Transfer) => transfer.items.reduce((total, item) => total + item.quantity, 0)

async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/transfers${path}`, { credentials: 'include', cache: 'no-store',
      method: body === undefined ? 'GET' : 'POST', signal: AbortSignal.timeout(15_000),
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch { throw new ApiError('No pudimos confirmar la operación. Puedes reintentar; la misma solicitud no se procesará dos veces.') }
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null)
    const detail = response.status < 500 && data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
      ? data.detail : 'No pudimos confirmar la operación. Reintenta o actualiza el listado.'
    throw new ApiError(detail, response.status)
  }
  return response.json() as Promise<T>
}
export const listTransfers = () => request<{ transfers: Transfer[] }>('')
export const transferOptions = () => request<TransferOptions>('/options')
export const getTransfer = (id: string) => request<Transfer>(`/${id}`)
export const createTransfer = (data: TransferInput) => request<Transfer>('', data)
export const changeTransfer = (id: string, action: TransferAction, data: unknown = {}) => request<Transfer>(`/${id}/${action}`, data)
