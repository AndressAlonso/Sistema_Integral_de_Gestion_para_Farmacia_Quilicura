import type { OnlineOrderSummary } from '../types/order-history'

export default function OrderHistoryItem({ order }: { order: OnlineOrderSummary }) {
  const date = new Date(order.created_at)
  const formattedDate = Number.isNaN(date.getTime()) ? 'Fecha no disponible' : new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
  const total = new Intl.NumberFormat('es-CL', { style: 'currency', currency: order.currency, maximumFractionDigits: 2 }).format(Number(order.total))
  return <li className="order-history-item"><h2>Pedido {order.number}</h2><dl>
    <div><dt>Fecha</dt><dd><time dateTime={order.created_at}>{formattedDate}</time></dd></div>
    <div><dt>Estado</dt><dd>{order.status}</dd></div>
    <div><dt>Total</dt><dd>{total}</dd></div>
    <div><dt>Sucursal de retiro</dt><dd>{order.pickup_branch.name}</dd></div>
  </dl></li>
}
