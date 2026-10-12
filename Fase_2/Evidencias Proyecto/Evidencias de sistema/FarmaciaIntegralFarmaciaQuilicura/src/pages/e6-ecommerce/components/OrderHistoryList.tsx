import type { OnlineOrderSummary } from '../types/order-history'
import OrderHistoryItem from './OrderHistoryItem'

/** Renderizar únicamente con resultados obtenidos del futuro endpoint real. */
export default function OrderHistoryList({ orders }: { orders: OnlineOrderSummary[] }) {
  return <ul className="order-history-list" aria-label="Pedidos online">{orders.map(order => <OrderHistoryItem key={order.id} order={order} />)}</ul>
}
