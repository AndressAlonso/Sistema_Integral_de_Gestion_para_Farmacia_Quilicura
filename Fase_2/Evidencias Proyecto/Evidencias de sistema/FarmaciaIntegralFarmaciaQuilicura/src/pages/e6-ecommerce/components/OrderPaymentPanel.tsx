import useAutoRefresh from '../../../hooks/useAutoRefresh'
import { useEffect, useRef, useState } from 'react'
import { orderAccess, recoverOrder } from '../services/orders.api'
import type { OnlineOrder } from '../services/orders.api'
import { createCheckout, redirectToCheckout } from '../services/payments.api'
import '../payment.css'
import OrderPickupCode from './OrderPickupCode'

const labels: Record<string, string> = {
  PENDIENTE_PAGO: 'Pendiente de pago', PAGADO: 'Pago confirmado',
  CANCELADO: 'Pedido cancelado', REVISION_PAGO: 'Pago en revisión',
  EN_PREPARACION: 'En preparación', LISTO_PARA_RETIRO: 'Listo para retiro', RETIRADO: 'Pedido retirado',
}

export default function OrderPaymentPanel({ order, onUpdate }: {
  order: OnlineOrder; onUpdate: (order: OnlineOrder) => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const sending = useRef(false)
  const fetching = useRef(false)
  const access = orderAccess(order.id)
  const pending = order.status === 'PENDIENTE_PAGO'

  useAutoRefresh(check, !!access && !busy && !['CANCELADO', 'RETIRADO'].includes(order.status), 15_000, false)

  async function check() {
    if (!access || fetching.current) return
    fetching.current = true
    try {
      const next = await recoverOrder(access)
      if (!mounted.current) return
      onUpdate(next)
      setError('')
    } catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : 'No pudimos consultar el estado.') }
    finally { fetching.current = false }
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
    {order.status === 'RETIRADO' && <p>La entrega de tu pedido ya fue registrada. Gracias por tu compra.</p>}
    {order.status === 'CANCELADO' && <p>Este pedido ya no admite pagos. Si realizaste un pago, consulta con la farmacia antes de crear otro pedido.</p>}
    {order.status === 'REVISION_PAGO' && <p>El pago necesita revisión de la farmacia. No vuelvas a pagar este pedido.</p>}
    <OrderPickupCode orderId={order.id} status={order.status} />
    {error && <p className="guest-error" role="alert">{error}</p>}
    {!access && <p>No encontramos el acceso a este pedido en esta pestaña. Abre la confirmación desde la pestaña donde lo creaste.</p>}
    <div className="order-payment-actions">
      {pending && <button className="order-payment-primary" type="button" disabled={!access || busy} onClick={() => void pay()}>
        {busy ? 'Abriendo Mercado Pago…' : 'Pagar con Mercado Pago'}
      </button>}

    </div>
  </section>
}
