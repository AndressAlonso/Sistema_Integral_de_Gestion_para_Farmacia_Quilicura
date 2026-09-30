import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../../services/http'
import { createTransfer, type Transfer, type TransferInput, type TransferOptions } from './transfers.api'

function initial(key: string): { data: TransferInput; pending: boolean } {
  try {
    const saved: TransferInput | null = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (saved?.request_id && typeof saved.origin_id === 'string' && typeof saved.destination_id === 'string' && Array.isArray(saved.items)
      && saved.items.every(item => typeof item.product_id === 'string' && Number.isInteger(item.quantity))) return { data: saved, pending: true }
  } catch { /* No usar borradores ilegibles. */ }
  return { data: { request_id: crypto.randomUUID(), origin_id: '', destination_id: '', items: [{ product_id: '', quantity: 1 }] }, pending: false }
}

export default function TransferForm({ options, userId, onClose, onSaved }: {
  options: TransferOptions; userId: string; onClose: () => void; onSaved: (transfer: Transfer) => void
}) {
  const key = `sigfq-transfer-pending:${userId}`
  const [saved] = useState(() => initial(key))
  const [data, setData] = useState(saved.data)
  const [pending, setPending] = useState(saved.pending)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const sending = useRef(false)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { if (element?.open) element.close() }
  }, [])
  const stock = options.stock.filter(item => item.branch_id === data.origin_id && item.available > 0)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (sending.current) return
    if (new Set(data.items.map(i => i.product_id)).size !== data.items.length) { setError('No repitas productos; reúne sus unidades en una fila.'); return }
    try { sessionStorage.setItem(key, JSON.stringify(data)) }
    catch { setError('Habilita el almacenamiento del navegador para conservar los reintentos.'); return }
    sending.current = true; setBusy(true); setError(''); setPending(true)
    try {
      const result = await createTransfer(data)
      sessionStorage.removeItem(key)
      onSaved(result)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo confirmar la solicitud.')
      if (cause instanceof ApiError && [400, 409, 422].includes(cause.status)) {
        sessionStorage.removeItem(key); setPending(false)
        setData(current => ({ ...current, request_id: crypto.randomUUID() }))
      }
    } finally { sending.current = false; setBusy(false) }
  }

  return <dialog ref={dialog} className="app-modal users-dialog users-dialog-fullscreen transfers-dialog" aria-labelledby="new-transfer-title" aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!sending.current) onClose() }}>
    <form onSubmit={event => { void submit(event) }}>
      <header className="users-dialog-heading"><div><h2 id="new-transfer-title">Nueva transferencia</h2><p>Solicita unidades de otra ubicación del sistema. La reserva se realiza en el origen; el stock físico aún no sale.</p></div>
        <button type="button" className="users-close" aria-label="Cerrar solicitud" disabled={busy} onClick={onClose}>×</button></header>
      {pending && <p className="transfer-notice" role="status">Solicitud pendiente de confirmación. Reintenta con los mismos datos para evitar una segunda reserva.</p>}
      <fieldset className="users-fields" disabled={busy || pending}>
        <legend className="sr-only">Datos de transferencia</legend>
        <label>Sucursal origen *<select required value={data.origin_id} onChange={event => setData({ ...data, origin_id: event.target.value, destination_id: '', items: [{ product_id: '', quantity: 1 }] })}>
          <option value="">Selecciona el origen</option>{options.branches.filter(b => options.origin_ids.includes(b.id)).map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select></label>
        <label>Sucursal destino *<select required value={data.destination_id} onChange={event => setData({ ...data, destination_id: event.target.value })}>
          <option value="">Selecciona el destino</option>{options.branches.filter(b => b.id !== data.origin_id).map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select></label>
        <h3 className="users-form-section">Productos y unidades</h3>
        <p className="transfer-wide">Solo se ofrece stock con lotes activos, no vencidos y sin reservar. Los lotes se asignan automáticamente por FEFO.</p>
        {data.origin_id && !stock.length && <p className="transfer-notice transfer-wide">No hay unidades transferibles en este origen. Revisa su inventario, lotes y reservas.</p>}
        {data.items.map((item, index) => <div className="transfer-item transfer-wide" key={index}>
          <label>Producto {index + 1} *<select required value={item.product_id} onChange={event => setData({ ...data, items: data.items.map((i, n) => n === index ? { ...i, product_id: event.target.value } : i) })}>
            <option value="">Selecciona un producto</option>{stock.map(p => <option key={p.product_id} value={p.product_id}>{p.product_name} · {p.sku} · {p.available} disponibles</option>)}
          </select></label>
          <label>Cantidad *<input required type="number" min={1} max={1000000} step={1} value={item.quantity || ''} onChange={event => setData({ ...data, items: data.items.map((i, n) => n === index ? { ...i, quantity: Number(event.target.value) } : i) })} /></label>
          {data.items.length > 1 && <button type="button" className="users-button" onClick={() => setData({ ...data, items: data.items.filter((_, n) => n !== index) })}>Quitar producto {index + 1}</button>}
        </div>)}
        <button type="button" className="users-button" disabled={!stock.length || data.items.length >= 100} onClick={() => setData({ ...data, items: [...data.items, { product_id: '', quantity: 1 }] })}>+ Agregar producto</button>
      </fieldset>
      {error && <p className="users-error" role="alert">{error}</p>}
      <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={onClose}>{pending ? 'Cerrar y conservar pendiente' : 'Cancelar'}</button>
        <button className="users-button primary" type="submit" disabled={busy || (!pending && !stock.length)}>{busy ? 'Solicitando…' : pending ? 'Reintentar confirmación' : 'Solicitar y reservar'}</button></footer>
    </form>
  </dialog>
}
