import { useEffect, useRef, useState, type FormEvent } from 'react'
import { actions, changeTransfer, getTransfer, states, transferCode, type Transfer, type TransferAction } from './transfers.api'

export default function TransferDetail({ transfer, initialAction, onClose, onChanged }: {
  transfer: Transfer; initialAction?: TransferAction; onClose: () => void; onChanged: (transfer: Transfer) => void
}) {
  const [current, setCurrent] = useState(transfer)
  const [action, setAction] = useState(initialAction)
  const [reason, setReason] = useState('')
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
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
    if (!action || sending.current || !confirmed) return
    sending.current = true; setBusy(true); setError('')
    const body = action === 'reject' ? { reason } : action === 'receive' ? {
      items: current.items.map(item => ({ product_id: item.product_id, quantity: Number(counts[item.product_id]) })),
    } : {}
    try { onChanged(await changeTransfer(current.id, action, body)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo confirmar la operación.') }
    finally { sending.current = false; setBusy(false) }
  }

  return <dialog ref={dialog} className="app-modal users-dialog users-dialog-fullscreen transfers-dialog" aria-labelledby="transfer-detail-title" aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!sending.current) onClose() }}>
    <form onSubmit={event => { void submit(event) }}>
      <header className="users-dialog-heading"><div><h2 id="transfer-detail-title">{transferCode(current.id)}</h2><p>{current.origin_name} → {current.destination_name}</p>
        <small>ID completo: {current.id}</small></div><button type="button" className="users-close" aria-label="Cerrar detalle" disabled={busy} onClick={onClose}>×</button></header>
      <p><span className={`transfer-state ${current.state.toLowerCase()}`}>{states[current.state]}</span> · Solicitada por {current.requested_by}</p>
      {loading && <p role="status">Comprobando estado y permisos actuales…</p>}
      <section className="users-panel"><h3>Productos y lotes</h3>
        {current.items.map(item => <div className="transfer-detail-item" key={item.product_id}>
          <strong>{item.product_name}</strong><span>{item.sku} · {item.quantity} unidades</span>
          <ul>{item.lots.map(lot => <li key={lot.number}>Lote {lot.number} · {lot.quantity} unidades · vence {lot.expiration_date}</li>)}</ul>
        </div>)}
      </section>
      <section className="users-panel transfer-timeline"><h3>Trazabilidad</h3><ol>{current.timeline.map(event => <li key={event.event}>
        <strong>{event.event}</strong> · {event.user} · {new Date(event.at).toLocaleString('es-CL')}
      </li>)}</ol>{current.rejection_reason && <p>Motivo de rechazo: {current.rejection_reason}</p>}</section>
      {!loading && <div className="transfer-actions">{current.actions.map(name => <button key={name} type="button" disabled={busy} className={`users-button ${action === name ? 'primary' : ''}`} onClick={() => { setAction(name); setConfirmed(false); setError('') }}>{actions[name]}</button>)}</div>}
      {action && !loading && current.actions.includes(action) && <fieldset className="users-fields" disabled={busy}>
        <legend className="sr-only">Confirmar {actions[action]}</legend>
        <p className="transfer-wide">{action === 'approve' ? 'La autorización habilita el despacho. Las unidades continúan reservadas en origen.'
          : action === 'reject' ? 'Se liberarán las unidades reservadas. La solicitud y su historial se conservarán.'
          : action === 'dispatch' ? 'Confirma solo cuando las unidades salgan físicamente del origen. Se descontarán del stock y quedarán en tránsito.'
          : 'Cuenta las unidades recibidas físicamente. Deben coincidir con todo el despacho; si difieren, la transferencia seguirá en tránsito.'}</p>
        {action === 'reject' && <label className="transfer-wide">Motivo *<textarea required maxLength={250} value={reason} onChange={event => setReason(event.target.value)} /></label>}
        {action === 'receive' && current.items.map(item => <label key={item.product_id}>{item.product_name} — esperadas: {item.quantity}
          <input type="number" required min={0} step={1} max={1000000} placeholder="Cantidad contada" value={counts[item.product_id] ?? ''} onChange={event => setCounts({ ...counts, [item.product_id]: event.target.value })} />
        </label>)}
        <label className="users-checkbox transfer-wide"><input type="checkbox" required checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />Confirmo la operación y las cantidades indicadas.</label>
      </fieldset>}
      {error && <p className="users-error" role="alert">{error}</p>}
      <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={() => { setLoading(true); setAttempt(a => a + 1) }}>Actualizar detalle</button>
        <button type="button" className="users-button" disabled={busy} onClick={onClose}>Cerrar</button>
        {action && current.actions.includes(action) && <button className={`users-button ${action === 'reject' ? 'danger' : 'primary'}`} type="submit" disabled={busy || loading || !confirmed}>{busy ? 'Procesando…' : actions[action]}</button>}
      </footer>
    </form>
  </dialog>
}
