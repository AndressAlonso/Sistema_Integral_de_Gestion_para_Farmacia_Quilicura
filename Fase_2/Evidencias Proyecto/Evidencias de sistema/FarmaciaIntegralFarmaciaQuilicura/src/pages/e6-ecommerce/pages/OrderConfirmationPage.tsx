import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../../../services/http'
import PublicHeader from '../components/PublicHeader'
import GuestForm from '../components/GuestForm'
import { useCart } from '../hooks/useCart'
import { useGuest } from '../hooks/useGuest'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { createOrder, finishAttempt, orderAttempt, pendingOrder, recoverOrder } from '../services/orders.api'
import type { OnlineOrder } from '../services/orders.api'
import '../guest.css'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
export default function OrderConfirmationPage() {
  const { draft, validation, loading: cartLoading, clear } = useCart()
  const { guest } = useGuest()
  const { customer, loading: sessionLoading, error: sessionError } = useCustomerSession()
  const [result, setResult] = useState<OnlineOrder | null>(null)
  const [busy, setBusy] = useState(false)
  const [recovering, setRecovering] = useState(() => !!pendingOrder())
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const started = useRef(false)
  const sending = useRef(false)
  const fingerprint = JSON.stringify({ cart: draft, total: validation?.total, customer: customer?.id, guest: customer ? null : guest })
  const confirmed = confirmation === fingerprint
  useEffect(() => {
    if (sessionLoading || sessionError || started.current) return
    started.current = true
    const attempt = pendingOrder()
    if (!attempt) return
    let active = true
    void recoverOrder(attempt).then(order => {
      if (active) { setResult(order); finishAttempt(); clear() }
    }).catch(cause => {
      if (active && !(cause instanceof ApiError && cause.status === 404)) setError('No pudimos recuperar la confirmación. Reintenta con los mismos datos.')
    }).finally(() => { if (active) setRecovering(false) })
    return () => { active = false; started.current = false }
  }, [sessionLoading, sessionError, clear])
  async function submit() {
    if (!validation?.valid || validation.total == null || !confirmed || sending.current) {
      setError('Revisa el carrito y confirma los productos, cantidades y total.'); return
    }
    sending.current = true; setBusy(true); setError('')
    try {
      const attempt = orderAttempt()
      const order = await createOrder(draft, validation.total, customer ? null : guest, attempt)
      setResult(order); finishAttempt(); clear()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No pudimos confirmar el pedido. Reintenta; no se duplicará.')
      if (cause instanceof ApiError && cause.status === 409) {
        const attempt = pendingOrder()
        if (attempt) {
          try { const order = await recoverOrder(attempt); setResult(order); finishAttempt(); clear(); setError('') }
          catch (recovery) { if (recovery instanceof ApiError && recovery.status === 404) finishAttempt() }
        }
      }
    } finally { sending.current = false; setBusy(false) }
  }
  return <main className="guest-page"><PublicHeader /><h1>{result ? 'Tu pedido' : 'Confirmar pedido'}</h1>
    {error && <p className="guest-error" role="alert">{error}</p>}
    {result ? <section className="guest-review"><h2>Pedido {result.number}</h2>
      <p>Estado: <strong>{result.status === 'CANCELADO' ? 'Cancelado' : 'Pendiente de pago'}</strong></p>
      <p>Sucursal de retiro: {result.pickup_branch.name}</p>
      <ul>{result.items.map(item => <li key={item.product_id}>{item.name} · {item.quantity} unidades · {money(item.subtotal)}</li>)}</ul>
      <p>Total: <strong>{money(result.total)}</strong></p>
      <p>Las unidades están reservadas. El pedido todavía no está pagado ni listo para retiro. El pago se habilitará en una próxima etapa.</p>
      {customer && <Link className="guest-link" to="/tienda/mis-pedidos">Ver mis pedidos</Link>}
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
