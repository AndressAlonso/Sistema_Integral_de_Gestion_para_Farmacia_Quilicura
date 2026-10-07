import { createContext, useContext } from 'react'
import type { GuestData } from '../types/guest'

export const GuestContext = createContext<{ guest: GuestData; update: (guest: GuestData) => void } | null>(null)
export function useGuest() {
  const context = useContext(GuestContext)
  if (!context) throw new Error('La revisión requiere su contenedor público.')
  return context
}
