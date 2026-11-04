import Notification from '../../../components/Notification'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../../../services/http'
import PublicHeader from '../components/PublicHeader'
import GuestForm from '../components/GuestForm'
import { useCart } from '../hooks/useCart'
import { useGuest } from '../hooks/useGuest'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { createOrder, finishAttempt, orderAttempt, pendingOrder, recoverOrder, rememberOrder, orderAccess } from '../services/orders.api'
import type { OnlineOrder } from '../services/orders.api'
import '../guest.css'
import OrderPaymentPanel from '../components/OrderPaymentPanel'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
export default function OrderConfirmationPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedId = searchParams.get('order_id')
  const { draft, validation, loading: cartLoading, clear } = useCart()
  const { guest } = useGuest()
  const { customer, loading: sessionLoading, error: sessionError } = useCustomerSession()
  const [result, setResult] = useState<OnlineOrder | null>(null)
  const [busy, setBusy] = useState(false)
  const [recovering, setRecovering] = useState(() => !!(requestedId ? orderAccess(requestedId) : pendingOrder()))
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const sending = useRef(false)
  const fingerprint = JSON.stringify({ cart: draft, total: validation?.total, customer: customer?.id, guest: customer ? null : guest })
  const confirmed = confirmation === fingerprint
  const visibleResult = result && (!requestedId || result.id === requestedId) ? result : null
  const acceptOrder = useCallback((order: OnlineOrder, attempt: import('../services/orders.api').OrderAttempt) => {
    rememberOrder(order.id, attempt)
    setResult(order); finishAttempt(); clear()
    navigate(`/tienda/confirmar?order_id=${encodeURIComponent(order.id)}`, { replace: true })
  }, [clear, navigate])
  useEffect(() => {
    if (sessionLoading || sessionError) return
    const attempt = requestedId ? orderAccess(requestedId) : pendingOrder()
    if (!attempt) return
    let active = true
    void recoverOrder(attempt).then(order => {
      if (active) {
        if (requestedId) setResult(order)
        else acceptOrder(order, attempt)
      }
    }).catch(cause => {
      if (active && (requestedId || !(cause instanceof ApiError && cause.status === 404))) {
        setResult(null); setError(cause instanceof Error ? cause.message : 'No pudimos recuperar el pedido.')
      }
    }).finally(() => { if (active) setRecovering(false) })
    return () => { active = false }
  }, [sessionLoading, sessionError, customer?.id, requestedId, acceptOrder])
  async function submit() {
    if (!validation?.valid || validation.total == null || !confirmed || sending.current) {
      setError('Revisa el carrito y confirma los productos, cantidades y total.'); return
    }
    sending.current = true; setBusy(true); setError('')
    try {
      const attempt = orderAttempt()
      const order = await createOrder(draft, validation.total, customer ? null : guest, attempt)
      acceptOrder(order, attempt)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No pudimos confirmar el pedido. Reintenta; no se duplicará.')
      if (cause instanceof ApiError && cause.status === 409) {
        const attempt = pendingOrder()
        if (attempt) {
          try { const order = await recoverOrder(attempt); acceptOrder(order, attempt); setError('') }
          catch (recovery) { if (recovery instanceof ApiError && recovery.status === 404) finishAttempt() }
        }
      }
    } finally { sending.current = false; setBusy(false) }
  }
  return <main className="guest-page"><PublicHeader /><header className="store-page-heading"><div><p className="store-page-eyebrow">{visibleResult ? 'SEGUIMIENTO DE TU COMPRA' : 'REVISA TU SELECCIÓN'}</p><h1>{visibleResult ? 'Tu pedido' : 'Confirmar pedido'}</h1><p>{visibleResult ? 'Consulta el estado y los detalles de tu pedido.' : 'Comprueba tus datos, productos y sucursal antes de confirmar.'}</p></div></header>
    {error && <Notification message={error} kind="error" />}
    {visibleResult ? <section className="guest-review"><h2>Pedido {visibleResult.number}</h2>

      <p>Sucursal de retiro: {visibleResult.pickup_branch.name}</p>
      <ul>{visibleResult.items.map(item => <li key={item.product_id}>{item.name} · {item.quantity} unidades · {money(item.subtotal)}</li>)}</ul>
      <p>Total: <strong>{money(visibleResult.total)}</strong></p>
      <OrderPaymentPanel order={visibleResult} key={visibleResult.id} onUpdate={setResult} />
      {customer && <Link className="guest-link" to="/tienda/mis-pedidos">Ver mis pedidos</Link>}
    </section> : requestedId ? <section className="guest-review">
      {sessionError ? <p role="alert">{sessionError}</p> : recovering || sessionLoading ? <p role="status">Consultando el estado del pedido…</p> : <>
        <p>No pudimos abrir este pedido. Regresa desde Mercado Pago a la misma pestaña y dirección donde lo creaste.</p>
        {!customer && <Link to="/tienda/iniciar-sesion">Iniciar sesión de cliente</Link>}
      </>}
    </section> : sessionLoading || cartLoading || recovering ? <p role="status">Revisando la confirmación…</p>
      : sessionError ? <p role="alert">{sessionError}</p> : !validation?.valid ? <p>El carrito necesita revisión. Selecciona una sucursal y valida las cantidades antes de confirmar.</p> : <>
        {customer ? <>
          <section className="guest-review"><h2>Revisa antes de confirmar</h2><p>Sucursal de retiro: {validation.pickup_branch?.name}</p>
          <ul>{validation.items.map(item => <li key={item.product_id}>{item.name} · {item.quantity} unidades · {money(item.subtotal!)}{item.requires_transfer && <p>Requiere traslado desde otra sucursal. Todavía no está listo para retiro.</p>}</li>)}</ul>
          <p>Total: <strong>{money(validation.total!)}</strong></p>
          <p>Crear el pedido reserva las unidades. No realiza un pago ni una salida física.</p>
        </section>
          <section className="guest-form"><p>Confirmarás con tu cuenta: {customer.name}.</p>
            <label className="lot-status-confirm"><input type="checkbox" disabled={busy} checked={confirmed} onChange={event => setConfirmation(event.target.checked ? fingerprint : '')} />Confirmo los productos, cantidades, sucursal y total.</label>
            <button type="button" disabled={busy || !confirmed} onClick={() => void submit()}>{busy ? 'Confirmando…' : 'Crear pedido y reservar'}</button>
          </section>
        </> : <>
          <p>Como invitado, solo necesitamos nombre y correo. No se crea una cuenta.</p>
          <GuestForm busy={busy} onSubmit={submit} onEdit={() => { setConfirmation(''); setError('') }} submitDisabled={!confirmed} submitLabel="Crear pedido y reservar">
            <section className="guest-review"><h2>Revisa antes de confirmar</h2><p>Sucursal de retiro: {validation.pickup_branch?.name}</p>
          <ul>{validation.items.map(item => <li key={item.product_id}>{item.name} · {item.quantity} unidades · {money(item.subtotal!)}{item.requires_transfer && <p>Requiere traslado desde otra sucursal. Todavía no está listo para retiro.</p>}</li>)}</ul>
          <p>Total: <strong>{money(validation.total!)}</strong></p>
          <p>Crear el pedido reserva las unidades. No realiza un pago ni una salida física.</p>
        </section>
            <label className="lot-status-confirm"><input type="checkbox" disabled={busy} checked={confirmed} onChange={event => setConfirmation(event.target.checked ? fingerprint : '')} />Confirmo los productos, cantidades, sucursal y total.</label>
          </GuestForm>
        </>}
      </>}
    <Link className="guest-back" to="/tienda/carrito">Volver al carrito</Link>
  </main>
}
