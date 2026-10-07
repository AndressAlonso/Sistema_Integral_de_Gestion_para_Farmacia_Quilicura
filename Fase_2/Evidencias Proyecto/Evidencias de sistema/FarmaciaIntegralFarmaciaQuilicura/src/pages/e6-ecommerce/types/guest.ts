import type { CartValidation } from './cart'

export interface GuestData { name: string; email: string }
export interface GuestValidation { guest: GuestData; cart: CartValidation }
