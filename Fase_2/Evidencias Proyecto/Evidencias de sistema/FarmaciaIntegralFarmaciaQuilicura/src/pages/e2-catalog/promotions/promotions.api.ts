import { apiRequest } from '../../../services/http'

export interface PromotionInput {
  name: string
  kind: 'PERCENT' | 'FIXED_PRICE'
  value: string
  starts_at: string
  ends_at: string
  product_id: string | null
  category_id: string | null
  is_active: boolean
}
export interface Promotion extends PromotionInput { id: string; created_at: string }
export async function listPromotions(): Promise<Promotion[]> {
  return (await apiRequest('/api/promotions')).json()
}
export async function savePromotion(data: PromotionInput, id?: string): Promise<Promotion> {
  return (await apiRequest(id ? `/api/promotions/${encodeURIComponent(id)}` : '/api/promotions', {
    method: id ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }, { 422: 'Revisa valor, vigencia y el producto o categoría seleccionados.' }, true)).json()
}
