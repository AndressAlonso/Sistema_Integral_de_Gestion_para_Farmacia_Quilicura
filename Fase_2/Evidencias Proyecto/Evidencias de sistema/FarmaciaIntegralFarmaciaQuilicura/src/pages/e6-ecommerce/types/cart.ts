export interface CartDraft { version: 1; items: { product_id: string; quantity: number }[]; pickup_branch_id: string | null }
export interface CartLine {
  product_id: string; name: string | null; quantity: number; unit_price: string | null; subtotal: string | null
  local_available: number | null; global_available: number; requires_transfer: boolean; valid: boolean; issues: string[]
}
export interface CartValidation {
  valid: boolean; pickup_branch: { id: string; name: string; address: string } | null
  items: CartLine[]; total: string | null; currency: string; issues: string[]
}
