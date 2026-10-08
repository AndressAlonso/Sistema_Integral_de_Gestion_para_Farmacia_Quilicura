import { ApiError, apiRequest } from '../../services/http'

export type Product = { id: string; name: string; sku: string; price: string; available: number; requires_prescription: boolean }
export type Item = { product_id: string; quantity: number }
export type SoldLot = { sale_lot_id: string; number: string; expires_at: string; quantity: number; returnable: number }
export type Line = Item & { name: string; sku: string; base_price: string; price: string; total: string; promotion: { name: string } | null; lots?: SoldLot[] }
export type Quote = { items: Line[]; subtotal: string; discount: string; total: string; version: string }
export type Payment = 'EFECTIVO' | 'DEBITO' | 'CREDITO' | 'TRANSFERENCIA'
export type Summary = { payments: Record<Payment, string>; refunds: Record<Payment, string>; sales_count: number; total: string; average_ticket: string; expected_cash: string; version: string; counted_cash?: string; difference?: string }
export type Cash = { id: string; opened_at: string; initial_amount: string; closed_at: string | null; summary: Summary | null }
export type Receipt = Omit<Quote, 'version'> & { id: string; date: string; branch: string; cashier: string; payment: Payment; notice: string }
export type SaleRequest = { request_id: string; items: Item[]; payment: Payment; quote_version: string }
export type ReversalRequest = { request_id: string; kind: 'DEVOLUCION' | 'ANULACION'; reason: string; items: Array<Item & { sale_lot_id: string; restock: boolean; condition: string }> }
export type SaleSummary = { id: string; date: string; total: string; payment: Payment }

export const currency = (value: string | number) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
export const paymentNames: Record<Payment, string> = { EFECTIVO: 'Efectivo', DEBITO: 'Débito', CREDITO: 'Crédito', TRANSFERENCIA: 'Transferencia' }

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await apiRequest(path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }, { 409: 'Los datos cambiaron o la operación ya no es posible. Actualiza el carrito o la caja y vuelve a revisar.', 422: 'Revisa las cantidades, importes y campos obligatorios.' }, true)
  return response.json() as Promise<T>
}

export const posApi = {
  sales: () => request<{ sales: SaleSummary[] }>('/api/pos/sales'),
  reverse: (id: string, data: ReversalRequest) => request<{ id: string; amount: string }>(`/api/pos/sales/${id}/reversals`, data),
  products: (q: string) => request<{ products: Product[] }>(`/api/pos/products?q=${encodeURIComponent(q)}`),
  quote: (items: Item[]) => request<Quote>('/api/pos/quote', { items }),
  sell: (data: SaleRequest) => request<Receipt>('/api/pos/sales', data),
  receipt: (id: string) => request<Receipt>(`/api/pos/sales/${encodeURIComponent(id)}/receipt`),
  cash: () => request<Cash | null>('/api/cash/current'),
  open: (request_id: string, initial_amount: string) => request<Cash>('/api/cash/open', { request_id, initial_amount }),
  summary: (id: string) => request<Summary>(`/api/cash/${id}/summary`),
  close: (id: string, counted_cash: string, summary_version: string) => request<Cash>(`/api/cash/${id}/close`, { counted_cash, summary_version }),
}
export const errorMessage = (error: unknown) => error instanceof ApiError ? error.message : 'No pudimos completar la operación.'
