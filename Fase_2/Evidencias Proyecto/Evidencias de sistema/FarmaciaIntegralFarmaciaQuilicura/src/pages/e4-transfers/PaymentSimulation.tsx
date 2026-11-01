import Notification from '../../components/Notification'
import { useEffect, useRef, useState } from 'react'
import { apiRequest } from '../../services/http'

interface PendingOrder {
  id: string; number: string; total: string
  pickup_branch: { name: string }
  items: { name: string; quantity: number }[]
}
interface SimulationResult {
  order: { number: string; status: string }
  transfer_ids: string[]
}
const base = '/api/orders/development'

export default function PaymentSimulation({ onChanged }: { onChanged: () => void }) {
  const [enabled, setEnabled] = useState(false)
  const [orders, setOrders] = useState<PendingOrder[]>([])
  const [selected, setSelected] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [revision, setRevision] = useState(0)
  const sending = useRef(false)
  useEffect(() => {
    let active = true
    async function load() {
      try {
        const availability: { enabled: boolean } = await (await apiRequest(base + '/availability')).json()
        if (!active || !availability.enabled) return
        setEnabled(true)
        const data: { orders: PendingOrder[] } = await (await apiRequest(base + '/orders')).json()
        if (active) { setOrders(data.orders); setError('') }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : 'No se pudo cargar el simulador.')
      }
    }
    void load()
    return () => { active = false }
  }, [revision])
  if (!enabled) return null
  const order = orders.find(row => row.id === selected)
  async function simulate(outcome: 'accepted' | 'failed') {
    if (!order || !confirmed || sending.current) return
    sending.current = true; setBusy(true); setError(''); setMessage('')
    try {
      const result: SimulationResult = await (await apiRequest(base + '/orders/' + order.id + '/payment', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome, confirmed: true }),
      }, {}, true)).json()
      setMessage(result.order.status === 'PAGADO'
        ? `Pago simulado aceptado. ${result.transfer_ids.length} transferencias automáticas. No se cobró dinero.`
        : 'Pago simulado fallido. Pedido cancelado y reservas liberadas.')
      setSelected(''); setConfirmed(false); setRevision(value => value + 1); onChanged()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo confirmar el resultado. Puedes reintentar.')
    } finally { sending.current = false; setBusy(false) }
  }
  return <details className="users-panel payment-simulation">
    <summary>Simulación de pago — desarrollo</summary>
    <p>Solo para pruebas de E7-H3. No procesa pagos con Flow ni registra una venta. Aceptar crea los traslados necesarios; fallar cancela el pedido y libera sus reservas.</p>
    {error && <Notification message={error} kind="error" />}
    {message && <Notification message={message} kind="success" />}
    <label>Pedido pendiente<select value={selected} disabled={busy} onChange={event => { setSelected(event.target.value); setConfirmed(false); setMessage('') }}>
      <option value="">Selecciona un pedido</option>
      {orders.map(row => <option key={row.id} value={row.id}>{row.number} · {row.pickup_branch.name}</option>)}
    </select></label>
    {!orders.length && <p>No hay pedidos pendientes. Crea uno desde la tienda y actualiza esta sección.</p>}
    {order && <div><p>{order.pickup_branch.name} · Total: {new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' }).format(Number(order.total))}</p>
      <ul>{order.items.map((item, index) => <li key={index}>{item.name} · {item.quantity} unidades</li>)}</ul>
      <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />Confirmo que quiero simular el resultado de este pedido de prueba.</label>
    </div>}
    <div className="transfer-actions">
      <button type="button" className="users-button primary" disabled={busy || !confirmed || !order} onClick={() => void simulate('accepted')}>Simular pago aceptado</button>
      <button type="button" className="users-button" disabled={busy || !confirmed || !order} onClick={() => void simulate('failed')}>Simular pago fallido</button>
      <button type="button" className="users-button" disabled={busy} onClick={() => setRevision(value => value + 1)}>Actualizar pedidos</button>
    </div>
  </details>
}

