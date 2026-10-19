import { apiRequest } from '../../services/http'
export interface LotStatus {
  lot_id: string; number: string; product_name: string; branch_name: string
  expiration_date: string; quantity: number; is_active: boolean; can_reactivate: boolean; can_disable: boolean
}
export const getLotStatus = async (id: string): Promise<LotStatus> =>
  (await apiRequest(`/api/inventory/lots/${encodeURIComponent(id)}/status`)).json()
export const reactivateLot = async (lot: LotStatus, reason: string): Promise<{ lot_id: string; changed: boolean }> =>
  (await apiRequest(`/api/inventory/lots/${encodeURIComponent(lot.lot_id)}/reactivate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, confirmed: true, expected_expiration_date: lot.expiration_date, expected_quantity: lot.quantity }),
  }, { 422: 'Escribe un motivo de entre 3 y 250 caracteres y confirma la revisión.' }, true)).json()

export const disableLot = async (lot: LotStatus, reason: string): Promise<{ lot_id: string; changed: boolean }> =>
  (await apiRequest(`/api/inventory/lots/${encodeURIComponent(lot.lot_id)}/disable`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, confirmed: true, expected_expiration_date: lot.expiration_date, expected_quantity: lot.quantity }),
  }, { 422: 'Escribe un motivo de entre 3 y 250 caracteres y confirma la revisión.' }, true)).json()
