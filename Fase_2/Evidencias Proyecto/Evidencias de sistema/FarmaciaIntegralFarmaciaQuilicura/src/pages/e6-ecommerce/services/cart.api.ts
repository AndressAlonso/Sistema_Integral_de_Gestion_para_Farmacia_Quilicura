import { apiRequest } from '../../../services/http'
import type { CartDraft, CartValidation } from '../types/cart'

export async function validateCart(draft: CartDraft): Promise<CartValidation> {
  return (await apiRequest('/api/ecommerce/cart/validate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: draft.items, pickup_branch_id: draft.pickup_branch_id }),
  }, { 422: 'El carrito admite hasta 50 productos distintos y de 1 a 99 unidades por producto.' })).json()
}
