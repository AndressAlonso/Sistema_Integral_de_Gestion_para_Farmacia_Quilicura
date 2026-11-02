import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../services/http'
import { orderAccess, recoverOrder } from '../services/orders.api'
import type { OnlineOrder } from '../services/orders.api'
import { createCheckout, redirectToCheckout } from '../services/payments.api'
import '../payment.css'

const labels: Record<string, string> = {
  PENDIENTE_PAGO: 'Pendiente de pago', PAGADO: 'Pago confirmado',
  CANCELADO: 'Pedido cancelado', REVISION_PAGO: 'Pago en revisión',
  EN_PREPARACION: 'En preparación', LISTO_PARA_RETIRO: 'Listo para retiro',
}

export default function OrderPaymentPanel({ order, onUpdate }: {
  order: OnlineOrder; onUpdate: (order: OnlineOrder) => void
}) {
  const [busy, setBusy] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const sending = useRef(false)
  const fetching = useRef(false)
  const access = orderAccess(order.id)
  const token = access?.request_token
  const pending = order.status === 'PENDIENTE_PAGO'

  useEffect(() => {
    if (!pending || !token) return
    let active = true
    let tries = 0
    const timer = window.setInterval(() => {
      if (fetching.current) return
      if (++tries > 24) {
        window.clearInterval(timer)
        setNotice('La confirmación sigue pendiente. Puedes consultar el estado nuevamente.')
        return
      }
      fetching.current = true
      void recoverOrder({ request_id: order.id, request_token: token }).then(next => {
        if (active) { onUpdate(next); setError('') }
      }).catch(cause => {
        if (!active) return
        setError(cause instanceof Error ? cause.message : 'No pudimos consultar el estado.')
        if (cause instanceof ApiError && [401, 403, 404].includes(cause.status)) window.clearInterval(timer)
      }).finally(() => { fetching.current = false })
    }, 5000)
    return () => { active = false; window.clearInterval(timer) }
  }, [order.id, pending, token, onUpdate])

  async function check() {
    if (!access || fetching.current) return
    fetching.current = true; setChecking(true); setError('')
    try {
      const next = await recoverOrder(access)
      if (!mounted.current) return
      onUpdate(next)
      setNotice(next.status === 'PENDIENTE_PAGO' ? 'Todavía esperamos la confirmación del pago.' : '')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'No pudimos consultar el estado.') }
    finally { fetching.current = false; setChecking(false) }
  }

  async function pay() {
    if (!access || sending.current || !pending) return
    sending.current = true; setBusy(true); setError('')
    try {
      const url = await createCheckout(access)
      if (mounted.current) redirectToCheckout(url)
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No pudimos abrir el pago.') }
    finally { sending.current = false; setBusy(false) }
  }

  return <section className={`order-payment ${pending ? '' : 'order-payment-resolved'}`} aria-label="Pago del pedido">
    <p className="order-payment-status" role="status">{labels[order.status] ?? order.status}</p>
    {pending && <p>El pedido todavía no está pagado. La reserva tiene un plazo de 15 minutos desde su creación. Completa el pago para continuar.</p>}
    {order.status === 'PAGADO' && <p>Recibimos la confirmación del pago. Tu pedido aún debe prepararse; este mensaje no confirma que esté listo para retiro.</p>}
    {order.status === 'EN_PREPARACION' && <p>Estamos preparando tu pedido. Te avisaremos cuando esté listo para retiro.</p>}
    {order.status === 'LISTO_PARA_RETIRO' && <p>Tu pedido está listo para retiro en la sucursal seleccionada.</p>}
    {order.status === 'CANCELADO' && <p>Este pedido ya no admite pagos. Si realizaste un pago, consulta con la farmacia antes de crear otro pedido.</p>}
    {order.status === 'REVISION_PAGO' && <p>El pago necesita revisión de la farmacia. No vuelvas a pagar este pedido.</p>}
    {error && <p className="guest-error" role="alert">{error}</p>}
    {notice && pending && <p aria-live="polite">{notice}</p>}
    {!access && <p>No encontramos el acceso a este pedido en esta pestaña. Abre la confirmación desde la pestaña donde lo creaste.</p>}
    <div className="order-payment-actions">
      {pending && <button className="order-payment-primary" type="button" disabled={!access || busy} onClick={() => void pay()}>
        {busy ? 'Abriendo Mercado Pago…' : 'Pagar con Mercado Pago'}
      </button>}
      {access && <button className="order-payment-secondary" type="button" disabled={checking || busy} onClick={() => void check()}>
        {checking ? 'Consultando…' : 'Consultar estado'}
      </button>}
    </div>
  </section>
}
