import { useState, type ReactNode } from 'react'
import { GuestContext } from '../hooks/useGuest'
import type { GuestData } from '../types/guest'

export default function GuestProvider({ children }: { children: ReactNode }) {
  const [guest, update] = useState<GuestData>({ name: '', email: '' })
  return <GuestContext.Provider value={{ guest, update }}>{children}</GuestContext.Provider>
}
