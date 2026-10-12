import { createContext, useContext } from 'react'
import type { CartDraft, CartValidation } from '../types/cart'

export interface CartState {
  draft: CartDraft; validation: CartValidation | null; loading: boolean; error: string
  add: (id: string) => Promise<string | null>; change: (id: string, quantity: number) => void
  remove: (id: string) => void; selectBranch: (id: string) => void; refresh: () => void
}
export const CartContext = createContext<CartState | null>(null)
export function useCart() {
  const value = useContext(CartContext)
  if (!value) throw new Error('El carrito requiere su contenedor público.')
  return value
}
