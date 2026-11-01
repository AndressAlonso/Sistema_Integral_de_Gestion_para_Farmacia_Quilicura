import { useEffect, useState } from 'react'
import { useCustomerSession } from '../hooks/useCustomerSession'
import OrderHistoryState from '../components/OrderHistoryState'
import OrderHistoryList from '../components/OrderHistoryList'
import PublicHeader from '../components/PublicHeader'
import { getOrderHistory } from '../services/order-history.api'
import type { OrderHistoryResponse } from '../types/order-history'
import '../order-history.css'

export default function OrderHistoryPage() {
  const session = useCustomerSession()
  const [cursor, setCursor] = useState<string | undefined>()
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<{ owner: string; cursor?: string; data?: OrderHistoryResponse; error?: string }>()
  useEffect(() => {
    if (!session.customer || session.loading || session.error) return
    let active = true
    const owner = session.customer.id
    void getOrderHistory({ cursor, limit: 15 }).then(data => {
      if (active) setResult({ owner, cursor, data })
    }).catch(() => {
      if (active) setResult({ owner, cursor, error: 'No pudimos consultar tus pedidos. Intenta nuevamente.' })
    })
    return () => { active = false }
  }, [session.customer, session.loading, session.error, cursor, retry])
  const current = result?.owner === session.customer?.id && result?.cursor === cursor ? result : undefined
  return <main className="order-history-page"><PublicHeader /><header className="store-page-heading"><div><p className="store-page-eyebrow">TU CUENTA</p><h1>Mis pedidos</h1><p>Revisa el estado, el total y la sucursal de tus pedidos.</p></div></header>
    {session.loading ? <OrderHistoryState state="loading" />
      : session.error ? <OrderHistoryState state="error" message={session.error} />
      : !session.customer ? <OrderHistoryState state="session-required" />
      : !current ? <OrderHistoryState state="loading" />
      : current.error ? <><OrderHistoryState state="error" message={current.error} /><button onClick={() => { setResult(undefined); setRetry(v => v + 1) }}>Reintentar</button></>
      : current.data ? <><p>Compras realizadas con tu cuenta en la tienda online.</p>
        {current.data.orders.length ? <OrderHistoryList orders={current.data.orders} /> : <OrderHistoryState state="empty" />}
        <nav aria-label="Páginas de pedidos">{cursor && <button onClick={() => setCursor(undefined)}>Volver al inicio</button>}
          {current.data.next_cursor && <button onClick={() => setCursor(current.data?.next_cursor ?? undefined)}>Siguiente</button>}</nav></> : null}
  </main>
}
