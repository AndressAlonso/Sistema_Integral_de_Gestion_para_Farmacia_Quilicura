import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { actions, changeTransfer, getTransfer, states, transferCode, units, type Transfer, type TransferAction } from './transfers.api'
import ReceiptReviewDialog from './ReceiptReviewDialog'

const choiceLabels = { ...actions, approve: 'Autorizar transferencia', reject: 'Rechazar transferencia', dispatch: 'Registrar salida de productos', receive: 'Registrar recepción de productos' }
const confirmationLabels = { approve: 'Confirmar autorización', reject: 'Confirmar rechazo', dispatch: 'Confirmar salida', receive: 'Confirmar recepción' }

export default function TransferDetail({ transfer, initialAction, onClose, onChanged }: {
  transfer: Transfer; initialAction?: TransferAction; onClose: () => void; onChanged: (transfer: Transfer) => void
}) {
  const actionGroup = useId()
  const [current, setCurrent] = useState(transfer)
  const [action, setAction] = useState(initialAction)
  const [reason, setReason] = useState('')
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reviewOpen, setReviewOpen] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const dialog = useRef<HTMLDialogElement>(null)
  const sending = useRef(false)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { if (element?.open) element.close() }
  }, [])
  useEffect(() => {
    let active = true
    getTransfer(transfer.id).then(data => { if (active) { setCurrent(data); setLoading(false); setError('') } })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'No se pudo actualizar el detalle.') })
    return () => { active = false }
  }, [transfer.id, attempt])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!action || sending.current || !confirmed || busy) return
    sending.current = true; setBusy(true); setError('')
    const body = action === 'reject' ? { reason } : action === 'receive' ? {
      items: current.items.map(item => ({ product_id: item.product_id, quantity: Number(counts[item.product_id]) })),
    } : {}
    try { onChanged(await changeTransfer(current.id, action, body)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo confirmar la operación.') }
    finally { sending.current = false; setBusy(false) }
  }

  return <dialog ref={dialog} className="app-modal users-dialog users-dialog-fullscreen transfers-dialog" aria-labelledby="transfer-detail-title" aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!sending.current && !busy) onClose() }}>
    <form onSubmit={event => { void submit(event) }}>
      <header className="users-dialog-heading"><div><h2 id="transfer-detail-title">{transferCode(current.id)}</h2><p>{current.origin_name} → {current.destination_name}</p>
        <small>ID completo: {current.id}</small></div><button type="button" className="users-close" aria-label="Cerrar detalle" disabled={busy} onClick={onClose}>×</button></header>
      <p><span className={`transfer-state ${current.state.toLowerCase()}`}>{states[current.state]}</span> · Solicitada por {current.requested_by}</p>
      {loading && <p role="status">Comprobando estado y permisos actuales…</p>}
      <section className="users-panel" aria-label="Cómo funciona la transferencia">
        <h3>Solicitar → Autorizar → Enviar → Recibir</h3>
        <p>Solicitar aparta unidades en origen. Autorizar permite enviarlas. Confirmar salida registra que salieron físicamente. Confirmar recepción las incorpora al destino.</p>
        {current.state === 'EN_TRANSITO' && <p><strong>Los productos ya salieron del origen.</strong> No se puede rechazar esta transferencia. Si la recepción está bloqueada, revisa el lote destino en Inventario; no lo reactives sin comprobar que corresponde.</p>}
        {(current.state === 'SOLICITADA' || current.state === 'AUTORIZADA') && <p>Puedes rechazar antes de confirmar la salida: se liberan las unidades reservadas y se conserva el historial.</p>}
      </section>
      <section className="users-panel"><h3>Productos y lotes</h3>
        {current.items.map(item => <div className="transfer-detail-item" key={item.product_id}>
          <strong>{item.product_name}</strong><span>{item.sku} · {item.quantity} unidades</span>
          <ul>{item.lots.map(lot => <li key={lot.number}>Lote {lot.number} · {lot.quantity} unidades · vence {lot.expiration_date}</li>)}</ul>
        </div>)}
      </section>
      <section className="users-panel transfer-timeline"><h3>Trazabilidad</h3><ol>{current.timeline.map(event => <li key={event.event}>
        <strong>{event.event}</strong> · {event.user} · {new Date(event.at).toLocaleString('es-CL')}
      </li>)}</ol>{current.rejection_reason && <p>Motivo de rechazo: {current.rejection_reason}</p>}</section>
      {!loading && current.actions.length > 0 && <fieldset className="transfer-choice" disabled={busy}>
        <legend>¿Qué deseas hacer?</legend>
        <div className="transfer-choice-options">{current.actions.map(name => <label key={name} className="transfer-choice-option">
          <input type="radio" name={actionGroup} value={name} checked={action === name}
            onChange={() => { setAction(name); setConfirmed(false); setError('') }} />
          <span>{choiceLabels[name]}</span>
        </label>)}</div>
      </fieldset>}
      {action && !loading && current.actions.includes(action) && <fieldset className="users-fields" disabled={busy}>
        <legend className="sr-only">{confirmationLabels[action]}</legend>
        <p className="transfer-wide">{action === 'approve' ? 'Autorizar permite enviar los productos. Todavía no salen del origen: siguen reservados.'
          : action === 'reject' ? 'Se liberarán las unidades reservadas. La solicitud y su historial se conservarán.'
          : action === 'dispatch' ? `Registra la salida de ${units(current)} unidades de ${current.origin_name} hacia ${current.destination_name}. Se descontarán del stock de ${current.origin_name} y quedarán en tránsito hasta confirmar su llegada.`
          : 'Escribe cuántas unidades llegaron físicamente al destino. Deben coincidir con las enviadas. Si hay diferencias o un lote bloqueado, no se completa la recepción y la transferencia sigue en tránsito.'}</p>
        {action === 'reject' && <label className="transfer-wide">Motivo *<textarea required maxLength={250} value={reason} onChange={event => { setReason(event.target.value); setConfirmed(false) }} /></label>}
        {action === 'receive' && current.items.map(item => <label key={item.product_id}>{item.product_name} — esperadas: {item.quantity}
          <input type="number" required min={0} step={1} max={1000000} placeholder="Cantidad contada" value={counts[item.product_id] ?? ''} onChange={event => { setCounts({ ...counts, [item.product_id]: event.target.value }); setConfirmed(false) }} />
        </label>)}
        <label className="users-checkbox transfer-wide"><input type="checkbox" required checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> {action === 'dispatch' ? 'Confirmo que los productos ya salieron físicamente y coinciden con las cantidades indicadas.' : 'Confirmo la operación y las cantidades indicadas.'}</label>
      </fieldset>}
      {error && <p className="users-error" role="alert">{error}</p>}
      {error && action === 'receive' && !loading && current.actions.includes('receive') && <div className="transfer-actions">
        <button type="button" className="users-button" disabled={busy} onClick={() => setReviewOpen(true)}>Revisar lote</button>
      </div>}
      {reviewOpen && <ReceiptReviewDialog key={current.id} transferId={current.id} onClose={() => setReviewOpen(false)} />}
      <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={() => { setLoading(true); setAttempt(a => a + 1) }}>Actualizar detalle</button>
        <button type="button" className="users-button" disabled={busy} onClick={onClose}>Cerrar</button>
        {action && current.actions.includes(action) && <button className={`users-button ${action === 'reject' ? 'danger' : 'primary'}`} type="submit" disabled={busy || loading || !confirmed}>{busy ? 'Procesando…' : confirmationLabels[action]}</button>}
      </footer>
    </form>
  </dialog>
}
