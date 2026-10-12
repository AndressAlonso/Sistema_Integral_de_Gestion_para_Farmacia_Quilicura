import { request } from './transfers.api'
export interface ReceiptLotReview {
  product_name: string; number: string; incoming_quantity: number; source_expiration: string
  destination_lot_id: string | null; destination_expiration: string | null
  destination_active: boolean | null; destination_quantity: number | null
  conflicts: ('INACTIVE' | 'EXPIRATION_MISMATCH')[]; can_reactivate: boolean
}
export interface ReceiptReview { destination_name: string; items: ReceiptLotReview[] }
export const reviewReceipt = (id: string) => request<ReceiptReview>(`/${encodeURIComponent(id)}/receipt-review`)
export const reactivateDestinationLot = (transferId: string, lot: ReceiptLotReview, reason: string) =>
  request<{ lot_id: string; changed: boolean }>(`/${encodeURIComponent(transferId)}/destination-lots/${encodeURIComponent(lot.destination_lot_id!)}/reactivate`, {
    reason, confirmed: true, expected_expiration_date: lot.destination_expiration, expected_quantity: lot.destination_quantity,
  })
