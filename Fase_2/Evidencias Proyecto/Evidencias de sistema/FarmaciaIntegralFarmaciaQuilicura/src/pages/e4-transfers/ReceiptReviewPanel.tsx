import Notification from '../../components/Notification'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { reviewReceipt } from './receipt-review.api'
import type { ReceiptReview } from './receipt-review.api'
const date = (value: string) => value.split('-').reverse().join('/')
export default function ReceiptReviewPanel({ transferId, disabled, onBusyChange, autoReview = false }: { transferId: string; disabled: boolean; onBusyChange?: (value: boolean) => void; autoReview?: boolean }) {
  const [review, setReview] = useState<ReceiptReview | null>(null)
  const [busy, setBusy] = useState(autoReview)
  const [error, setError] = useState('')
  const mounted = useRef(false)
  const operation = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => {
    if (!autoReview) return
    let active = true
    operation.current = true; onBusyChange?.(true)
    void reviewReceipt(transferId).then(result => { if (active) setReview(result) })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'No se pudo revisar el destino.') })
      .finally(() => { if (active) { operation.current = false; setBusy(false); onBusyChange?.(false) } })
    return () => { active = false }
  }, [autoReview, transferId, onBusyChange])
  async function inspect() {
    if (operation.current) return
    operation.current = true; setBusy(true); onBusyChange?.(true); setError('')
    try {
      const result = await reviewReceipt(transferId)
      if (mounted.current) setReview(result)
    } catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : 'No se pudo revisar el destino.') }
    finally { operation.current = false; if (mounted.current) { setBusy(false); onBusyChange?.(false) } }
  }
  return <section className="users-panel receipt-review" aria-label="Revisión de lotes destino">
    {!autoReview && <h3>Revisar lote destino</h3>}
    <p>El estado del lote se gestiona en Inventario. Esta revisión no cambia cantidades ni fechas.</p>
    <button type="button" className="users-button" disabled={disabled || busy} onClick={() => void inspect()}>{busy ? 'Consultando…' : autoReview ? 'Actualizar revisión' : 'Revisar lotes destino'}</button>
    {error && <Notification message={error} kind="error" />}
    {review && <><p>Destino: <strong>{review.destination_name}</strong></p>{review.items.map((lot, index) => <article key={`${lot.number}-${index}`} className="receipt-lot-review">
      <h4>{lot.product_name} · Lote {lot.number}</h4>
      <p>Enviado: {lot.incoming_quantity} unidades · Vence: {date(lot.source_expiration)}</p>
      {lot.destination_lot_id ? <p>En destino: {lot.destination_quantity} unidades · {lot.destination_active ? 'Habilitado' : 'Deshabilitado'} · Vence: {date(lot.destination_expiration!)}</p> : <p>El lote no existe en destino. Se registrará al confirmar la recepción.</p>}
      {lot.conflicts.includes('INACTIVE') && <p className="users-error">El lote destino está deshabilitado. Revísalo en Inventario antes de recibir.</p>}
      {lot.conflicts.includes('EXPIRATION_MISMATCH') && <p className="users-error">Los vencimientos no coinciden. Reactivar el lote no resuelve esta diferencia.</p>}
      {lot.destination_lot_id && <Link className="users-button" to={`/admin/inventory?tab=lots&lot_id=${encodeURIComponent(lot.destination_lot_id)}&transfer_id=${encodeURIComponent(transferId)}`}>Ir al lote en Inventario</Link>}
      {!lot.conflicts.length && <p>Sin conflicto de estado o vencimiento en destino.</p>}
    </article>)}</>}
  </section>
}
