import Notification from '../../components/Notification'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { disableLot, getLotStatus, reactivateLot } from './lot-status.api'
import type { LotStatus } from './lot-status.api'
import './lot-status.css'

export default function LotStatusDialog({ lotId, onClose, onChanged }: { lotId: string; onClose: () => void; onChanged: (value: LotStatus) => void }) {
  const title = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const sending = useRef(false)
  const [lot, setLot] = useState<LotStatus | null>(null)
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => { if (element?.open) element.close() } }, [])
  useEffect(() => {
    let active = true
    void getLotStatus(lotId).then(value => { if (active) setLot(value) })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'No se pudo revisar el lote.') })
    return () => { active = false }
  }, [lotId])
  const today = new Date()
  const localToday = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, '0'), String(today.getDate()).padStart(2, '0')].join('-')
  const expired = !!lot && lot.expiration_date <= localToday
  const canChange = !!lot && !expired && (lot.is_active ? lot.can_disable : lot.can_reactivate)
  const action = lot?.is_active ? 'Deshabilitar lote' : 'Reactivar lote'
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!lot || !canChange || !confirmed || reason.trim().length < 3 || sending.current) return
    sending.current = true; setBusy(true); setError('')
    try {
      if (lot.is_active) await disableLot(lot, reason.trim())
      else await reactivateLot(lot, reason.trim())
      onChanged({ ...lot, is_active: !lot.is_active, can_reactivate: lot.is_active && !expired, can_disable: !lot.is_active })
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo cambiar el estado del lote.') }
    finally { sending.current = false; setBusy(false) }
  }
  return createPortal(<dialog className="lot-status-dialog" ref={dialog} aria-labelledby={title} aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!sending.current) onClose() }}>
    <form onSubmit={event => void submit(event)}>
      <header><h2 id={title}>Estado del lote</h2><button type="button" className="lot-status-close" disabled={busy} aria-label="Cerrar revisión del lote" onClick={onClose}>×</button></header>
      {error && <Notification message={error} kind="error" />}
      {!lot && !error && <p role="status">Consultando lote…</p>}
      {lot && <><h3>{lot.product_name}</h3><dl className="lot-status-summary">
        <div><dt>Lote</dt><dd>{lot.number}</dd></div><div><dt>Sucursal</dt><dd>{lot.branch_name}</dd></div>
        <div><dt>Vencimiento</dt><dd>{lot.expiration_date.split('-').reverse().join('/')}</dd></div>
        <div><dt>Cantidad</dt><dd>{lot.quantity} unidades</dd></div><div><dt>{expired ? 'Estado' : 'Habilitación'}</dt><dd>{expired ? 'Vencido' : lot.is_active ? 'Habilitado' : 'Deshabilitado'}</dd></div>
      </dl>
      {expired && <><p className="lot-status-error">Lote vencido. No puede venderse, transferirse ni reactivarse.</p>
        {lot.quantity > 0 && <p className="lot-status-note">Cuando retires físicamente estas unidades, registra el retiro en Inventario → Ajustar inventario, con la cantidad final y el motivo. El lote conservará su historial.</p>}</>}
      {lot.quantity === 0 && <p className="lot-status-note">Sin unidades. El lote conserva su historial.</p>}
      {canChange ? <div className="lot-status-form"><p>{lot.is_active
        ? 'Deshabilitar bloquea este lote para ventas y salidas. Conserva las unidades, el vencimiento y el historial. Las reservas pendientes no se cancelan; las operaciones afectadas deben revisarse.'
        : 'Reactivar quita el bloqueo del lote. Hazlo solo si resolviste el motivo de deshabilitación. No agrega unidades ni cambia el vencimiento.'}</p>
        <label>{lot.is_active ? 'Motivo de deshabilitación' : 'Motivo de reactivación'}<textarea required minLength={3} maxLength={250} disabled={busy} value={reason} onChange={event => { setReason(event.target.value); setConfirmed(false) }} /></label>
        <label className="lot-status-confirm"><input type="checkbox" required disabled={busy} checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{lot.is_active ? 'Revisé el lote y confirmo su deshabilitación.' : 'Revisé el lote y confirmo su reactivación.'}</label>
      </div> : !expired && <p className="lot-status-note">{lot.is_active ? 'No puedes deshabilitar este lote: revisa el permiso y la sucursal.' : 'No se puede reactivar: revisa el permiso, la sucursal y el vencimiento.'}</p>}</>}
      <footer><button type="button" disabled={busy} onClick={onClose}>Cerrar</button>{canChange && <button className="lot-status-primary" type="submit" disabled={busy || !confirmed || reason.trim().length < 3}>{busy ? 'Guardando…' : action}</button>}</footer>
    </form>
  </dialog>, document.body)
}
