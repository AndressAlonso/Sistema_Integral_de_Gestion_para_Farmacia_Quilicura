import { useEffect, useRef, useState } from 'react'
import { confirmPickup, validatePickup, type PickupPreview } from './orders.api'

export default function OrderPickupDialog({ onClose, onChanged }: { onClose: () => void; onChanged: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const sending = useRef(false)
  const [code, setCode] = useState('')
  const [order, setOrder] = useState<PickupPreview | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { const el = dialog.current; el?.showModal(); return () => el?.close() }, [])
  async function submit() {
    if (sending.current || done || (order && !confirmed)) return
    sending.current = true; setBusy(true); setError('')
    try {
      if (order) { await confirmPickup(code.trim(), order.id); setDone(true); onChanged() }
      else { setOrder(await validatePickup(code.trim())); setConfirmed(false) }
    } catch (cause) {
      setOrder(null); setConfirmed(false)
      setError(cause instanceof Error ? cause.message : 'No se pudo registrar el retiro.')
    } finally { sending.current = false; setBusy(false) }
  }
  return <dialog ref={dialog} className="app-modal users-dialog compact-dialog order-pickup-dialog" aria-labelledby="pickup-title" onCancel={event => { event.preventDefault(); if (!sending.current) onClose() }}>
    <header className="users-dialog-heading"><h2 id="pickup-title">Retirar pedido</h2><button className="users-close" disabled={busy} aria-label="Cerrar retiro" onClick={onClose}>×</button></header>
    {done ? <p role="status">Retiro registrado. Los productos fueron entregados y el inventario quedó actualizado.</p> : <form onSubmit={event => { event.preventDefault(); void submit() }}>
      <p>Escanea el QR o escribe el código numérico del correo del cliente.</p>
      <label className="pickup-code">QR o código de retiro<input autoFocus value={code} disabled={busy} maxLength={100} autoComplete="off" spellCheck={false} placeholder="Ej.: 1234 5678 9012 3456" onChange={event => { setCode(event.target.value); setOrder(null); setConfirmed(false); setError('') }} /></label>
      {error && <p className="users-error" role="alert">{error}</p>}
      {order && <section className="pickup-preview" aria-label="Revisar entrega"><strong className="order-code">{order.number}</strong><p>{order.customer.name} · {order.pickup_branch.name}</p><ul>{order.items.map(item => <li key={item.product_id}>{item.name} · <strong>{item.quantity} unidades</strong></li>)}</ul><p>Total pagado: {new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP' }).format(Number(order.total))}</p><label className="orders-confirmation"><input type="checkbox" disabled={busy} checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />Confirmo que entrego estos productos al cliente.</label></section>}
      <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={onClose}>Cancelar</button><button className="users-button primary" disabled={busy || !code.trim() || (!!order && !confirmed)}>{busy ? 'Procesando…' : order ? 'Confirmar retiro' : 'Validar código'}</button></footer>
    </form>}
    {done && <footer className="users-dialog-actions"><button className="users-button" onClick={onClose}>Cerrar</button></footer>}
  </dialog>
}
