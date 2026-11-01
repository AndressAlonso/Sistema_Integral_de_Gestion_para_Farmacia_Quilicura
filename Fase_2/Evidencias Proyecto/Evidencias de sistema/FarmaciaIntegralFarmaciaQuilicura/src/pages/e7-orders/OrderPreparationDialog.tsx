import Notification from '../../components/Notification'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { changeOrder, getOrder, orderStateLabel, type OrderAction, type OrderDetail } from './orders.api'

const transferStates: Record<string, string> = { AUTORIZADA: 'Pendiente de despacho', EN_TRANSITO: 'En camino', RECIBIDA: 'Recibida', RECHAZADA: 'Rechazada', SOLICITADA: 'Solicitada' }
const date = (value: string) => new Date(value).toLocaleString('es-CL')

export default function OrderPreparationDialog({ id, onClose, onChanged }: {
  id: string; onClose: () => void; onChanged: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const sending = useRef(false)
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [loading, setLoading] = useState(true)
  useEffect(() => { const el = dialog.current; el?.showModal(); return () => el?.close() }, [])
  useEffect(() => {
    let active = true
    getOrder(id).then(data => { if (active) { setOrder(data); setError('') } })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'No se pudo cargar el pedido.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id, attempt])
  async function change(action: OrderAction) {
    if (!order || loading || !order.actions.includes(action) || sending.current || (action === 'ready' && !confirmed)) return
    sending.current = true; setBusy(true); setError('')
    try { setOrder(await changeOrder(order, action)); setConfirmed(false); onChanged() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo actualizar el pedido.') }
    finally { sending.current = false; setBusy(false) }
  }
  return <dialog className="app-modal users-dialog users-dialog-fullscreen orders-dialog" ref={dialog} aria-labelledby="order-detail-title" onCancel={event => { event.preventDefault(); if (!sending.current) onClose() }}>
    <header className="users-dialog-heading"><div><span className="orders-eyebrow">PEDIDOS ONLINE</span><h2 id="order-detail-title">Detalle y preparación</h2><p className="order-code">{order?.number}</p></div><button className="users-close" disabled={busy} onClick={onClose} aria-label="Cerrar pedido">×</button></header>
    {loading && <p role="status">Cargando pedido…</p>}
    {error && <Notification message={error} kind="error" />}
    {order && <div className="orders-detail-content">
      <section className="orders-overview" aria-label="Resumen del pedido">
        <div><span className="orders-field-label">Estado actual</span><span className={`order-state order-state-${order.status}`}>{orderStateLabel(order.status)}</span></div>
        <div><span className="orders-field-label">Sucursal de retiro</span><strong>{order.pickup_branch.name}</strong><p>{date(order.created_at)}</p></div>
        <div><span className="orders-field-label">Cliente</span><strong>{order.customer.name}</strong><p>{order.customer.email}</p></div>
      </section>
      <section className="orders-state-management" aria-labelledby="manage-order-state">
        <div><h3 id="manage-order-state">Gestionar estado</h3><ol className="orders-progress" aria-label="Etapas de preparación">{['PAGADO', 'EN_PREPARACION', 'LISTO_PARA_RETIRO'].map((state, index) => {
          const current = ['PAGADO', 'EN_PREPARACION', 'LISTO_PARA_RETIRO'].indexOf(order.status)
          return <li key={state} className={current >= index ? 'is-reached' : ''} aria-current={order.status === state ? 'step' : undefined}><span aria-hidden="true">{current > index ? '✓' : index + 1}</span>{orderStateLabel(state)}</li>
        })}</ol></div>
        {order.status === 'PAGADO' && <div className="orders-next-action"><button className="users-button primary" disabled={busy || loading || !order.actions.includes('preparation')} onClick={() => void change('preparation')}>{busy ? 'Guardando…' : 'Iniciar preparación'}</button><small>{order.actions.includes('preparation') ? 'El pedido pasará a En preparación.' : 'No puedes iniciar la preparación con los permisos o la sucursal actuales.'}</small></div>}
        {order.status === 'EN_PREPARACION' && <div className="orders-next-action">
          {order.actions.includes('ready') && <label className="orders-confirmation"><input type="checkbox" checked={confirmed} disabled={busy || loading} onChange={e => setConfirmed(e.target.checked)} />Confirmo que todos los productos están preparados.</label>}
          <button className="users-button primary" disabled={!order.actions.includes('ready') || !confirmed || busy || loading} onClick={() => void change('ready')}>{busy ? 'Guardando…' : 'Marcar listo para retiro'}</button>
          {order.ready_blocked_reason ? <p role="status">{order.ready_blocked_reason}</p> : !order.actions.includes('ready') ? <p>No puedes cambiar el estado con los permisos o la sucursal actuales.</p> : !confirmed && <small>Marca la confirmación para continuar.</small>}
        </div>}
        {order.status === 'PENDIENTE_PAGO' && <p>Falta confirmar el pago para iniciar la preparación.</p>}
        {order.status === 'CANCELADO' && <p>Este pedido está cancelado y no puede prepararse.</p>}
        {order.status === 'LISTO_PARA_RETIRO' && <p role="status">Preparación completada. El pedido está listo para retiro.</p>}
      </section>
      <div className="orders-detail-grid"><div className="orders-main-column"><section className="orders-detail-card">
      <header className="orders-card-heading"><h3>Productos a preparar</h3><span>{order.items.reduce((sum, item) => sum + item.quantity, 0)} unidades</span></header>
      <div className="users-table-scroll"><table className="users-table"><thead><tr><th>Producto</th><th>Unidades</th></tr></thead><tbody>{order.items.map(item => <tr key={item.product_id}><td>{item.name}</td><td><strong>{item.quantity}</strong></td></tr>)}</tbody></table></div>
      </section><section className="orders-detail-card"><header className="orders-card-heading"><h3>Traslado de productos</h3></header>
      {order.transfers.length ? <ul className="orders-transfers">{order.transfers.map(t => <li key={t.id}><span>{t.origin} → {t.destination}</span><strong>{transferStates[t.status] ?? t.status}</strong><Link to={`/admin/transfers?transfer_id=${t.id}`}>Ver transferencia</Link></li>)}</ul> : <p className="orders-card-empty">{order.status === 'PENDIENTE_PAGO' ? 'Los traslados se determinarán al confirmar el pago.' : 'Sin transferencias asociadas.'}</p>}
      </section></div><section className="orders-detail-card orders-history-card"><header className="orders-card-heading"><h3>Historial del pedido</h3></header>
      <ol className="orders-history"><li><strong>Pedido creado</strong><span>{date(order.created_at)}</span></li>{order.history.map((event, index) => <li key={`${event.at}-${index}`}><strong>{event.previous ? `${orderStateLabel(event.previous)} → ` : ''}{orderStateLabel(event.status)}</strong><span>{event.actor} · {date(event.at)}</span></li>)}</ol>
      </section></div>
    </div>}
    <footer className="users-dialog-actions orders-actions">
      <button className="users-button" disabled={busy || loading} onClick={() => { setLoading(true); setConfirmed(false); setAttempt(n => n + 1) }}>Actualizar</button>
      <button className="users-button" disabled={busy} onClick={onClose}>Cerrar detalle</button>
    </footer>
  </dialog>
}
