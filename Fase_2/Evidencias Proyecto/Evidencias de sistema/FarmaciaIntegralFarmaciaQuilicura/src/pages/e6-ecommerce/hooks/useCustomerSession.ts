import { createContext, useContext } from 'react'
import type { Customer, CustomerSession } from '../types/customer'

export interface CustomerSessionState {
  customer: Customer | null
  loading: boolean
  closing: boolean
  error: string
  updateCustomer: (customer: Customer) => void
  refreshCustomer: () => Promise<CustomerSession | null>
  logout: () => Promise<void>
}

export const CustomerSessionContext = createContext<CustomerSessionState | null>(null)

export function useCustomerSession() {
  const session = useContext(CustomerSessionContext)
  if (!session) throw new Error('La sesión de cliente requiere CustomerSessionProvider.')
  return session
}
