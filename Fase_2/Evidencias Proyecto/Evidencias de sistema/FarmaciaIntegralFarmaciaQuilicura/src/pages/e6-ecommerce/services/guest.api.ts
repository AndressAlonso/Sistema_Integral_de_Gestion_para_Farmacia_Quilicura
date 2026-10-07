import { apiRequest } from '../../../services/http'
import type { CartDraft } from '../types/cart'
import type { GuestData, GuestValidation } from '../types/guest'

export async function validateGuest(guest: GuestData, cart: CartDraft): Promise<GuestValidation> {
  return (await apiRequest('/api/ecommerce/guest/validate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ guest, cart: { items: cart.items, pickup_branch_id: cart.pickup_branch_id } }),
  }, { 422: 'Revisa el nombre, el correo y el carrito. Selecciona una sucursal de retiro activa.' })).json()
}
