import type { AppliedPromotion } from './promotion'

export interface PublicBranch { id: string; name: string; address: string }
export interface Availability { branch_id: string; branch_name: string; available: number }
export interface PublicProduct {
  id: string
  name: string
  description: string
  category: { id: string; name: string }
  price: string
  base_price?: string | null
  discount?: string
  promotion?: AppliedPromotion | null
  requires_prescription: boolean
  online_purchase_allowed: boolean
  image_url: string | null
  availability: Availability[]
}
