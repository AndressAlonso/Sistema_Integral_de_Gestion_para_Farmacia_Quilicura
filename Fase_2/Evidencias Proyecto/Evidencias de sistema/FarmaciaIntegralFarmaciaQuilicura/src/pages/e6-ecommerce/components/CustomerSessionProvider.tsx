import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ApiError } from '../../../services/http'
import { CustomerSessionContext } from '../hooks/useCustomerSession'
import { getCustomerSession, logoutCustomer } from '../services/customers.api'
import type { Customer } from '../types/customer'

export default function CustomerSessionProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [loading, setLoading] = useState(true)
  const [closing, setClosing] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(false)
  const generation = useRef(0)
  const logoutPending = useRef(false)
  const initialRequest = useRef<ReturnType<typeof getCustomerSession> | null>(null)

  useEffect(() => {
    mounted.current = true
    let active = true
    const current = generation.current
    // Reuse the initial request during StrictMode's effect replay.
    initialRequest.current ??= getCustomerSession()
    void initialRequest.current.then(session => {
      if (active && current === generation.current) setCustomer(session.customer)
    }).catch(cause => {
      if (active && current === generation.current && !(cause instanceof ApiError && cause.status === 401)) {
        setError('No pudimos consultar tu sesión. Recarga la página para intentar nuevamente.')
      }
    }).finally(() => {
      if (active && current === generation.current) setLoading(false)
    })
    return () => { active = false; mounted.current = false }
  }, [])

  function updateCustomer(value: Customer) {
    generation.current += 1
    if (mounted.current) {
      setCustomer(value)
      setLoading(false)
      setError('')
    }
  }

  async function refreshCustomer() {
    const current = generation.current
    const session = await getCustomerSession()
    if (!mounted.current || current !== generation.current) return null
    updateCustomer(session.customer)
    return session
  }

  async function logout() {
    if (logoutPending.current) return
    logoutPending.current = true
    generation.current += 1
    setClosing(true)
    setLoading(false)
    setError('')
    try {
      await logoutCustomer()
      if (mounted.current) setCustomer(null)
    } catch (cause) {
      if (mounted.current) {
        if (cause instanceof ApiError && cause.status === 401) setCustomer(null)
        else setError('No pudimos cerrar tu sesión. Intenta nuevamente.')
      }
    } finally {
      logoutPending.current = false
      if (mounted.current) setClosing(false)
    }
  }

  return <CustomerSessionContext.Provider value={{ customer, loading, closing, error, updateCustomer, refreshCustomer, logout }}>
    {children}
  </CustomerSessionContext.Provider>
}
