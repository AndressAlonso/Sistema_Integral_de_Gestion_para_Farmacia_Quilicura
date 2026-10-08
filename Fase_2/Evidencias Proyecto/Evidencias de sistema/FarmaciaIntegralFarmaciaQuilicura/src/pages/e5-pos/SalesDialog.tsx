import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../../services/http'
import { currency, errorMessage, paymentNames, posApi, type Receipt, type ReversalRequest, type SaleSummary } from './pos.api'

type ReturnRow = { product_id: string; sale_lot_id: string; name: string; lot: string; available: number; quantity: number; restock: boolean; condition: string }

export default function SalesDialog({ userId, canReverse, onClose, onReceipt }: { userId: string; canReverse: boolean; onClose: () => void; onReceipt: (receipt: Receipt) => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const locked = useRef(false)
  const [sales, setSales] = useState<SaleSummary[]>([])
  const [saleId, setSaleId] = useState('')
  const [receipt, setReceipt] = useState<Receipt | null>(null)
  const [rows, setRows] = useState<ReturnRow[]>([])
  const [reason, setReason] = useState('')
  const [kind, setKind] = useState<'DEVOLUCION' | 'ANULACION'>('DEVOLUCION')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const refundTotal = rows.reduce((total, row) => total + row.quantity * Number(receipt?.items.find(item => item.product_id === row.product_id)?.price ?? 0), 0)
  const [pending, setPending] = useState<{ saleId: string; data: ReversalRequest } | null>(() => {
    try { return JSON.parse(sessionStorage.getItem(`pos-return:${userId}`) ?? 'null') as { saleId: string; data: ReversalRequest } | null } catch { return null }
  })
  useEffect(() => {
    dialog.current?.showModal()
    let active = true
    posApi.sales().then(result => { if (active) setSales(result.sales) }).catch(cause => { if (active) setError(errorMessage(cause)) })
    return () => { active = false }
  }, [])
  async function select(id: string) {
    if (locked.current || pending) return
    locked.current = true; setBusy(true); setError(''); setSuccess('')
    try {
      const result = await posApi.receipt(id); setReceipt(result); setSaleId(id); setConfirmed(false); setReason('')
      setRows(result.items.flatMap(item => (item.lots ?? []).map(lot => ({ product_id: item.product_id, sale_lot_id: lot.sale_lot_id, name: item.name, lot: `${lot.number} · vence ${lot.expires_at}`, available: lot.returnable, quantity: 0, restock: false, condition: '' }))))
    } catch (cause) { setError(errorMessage(cause)) }
    finally { locked.current = false; setBusy(false) }
  }
  async function reverse(event?: FormEvent) {
    event?.preventDefault()
    if (locked.current || (!pending && (!receipt || !confirmed))) return
    const operation = pending ?? { saleId: receipt!.id, data: { request_id: crypto.randomUUID(), kind, reason, items: rows.filter(row => row.quantity > 0).map(({ product_id, sale_lot_id, quantity, restock, condition }) => ({ product_id, sale_lot_id, quantity, restock, condition })) } }
    if (!operation.data.items.length) { setError('Selecciona al menos una unidad para devolver.'); return }
    locked.current = true; setBusy(true); setError('')
    try {
      sessionStorage.setItem(`pos-return:${userId}`, JSON.stringify(operation)); setPending(operation)
      const result = await posApi.reverse(operation.saleId, operation.data)
      setSuccess(`Operación registrada por ${currency(result.amount)}. Referencia: ${result.id}`)
      setPending(null); sessionStorage.removeItem(`pos-return:${userId}`); setReceipt(null); setRows([])
    } catch (cause) {
      if (cause instanceof ApiError && [403, 404, 409, 422].includes(cause.status)) {
        setPending(null); sessionStorage.removeItem(`pos-return:${userId}`)
      }
      setError(errorMessage(cause))
    } finally { locked.current = false; setBusy(false) }
  }
  return <dialog ref={dialog} className="pos-dialog" onCancel={event => { event.preventDefault(); if (!busy) onClose() }}><div className="pos-dialog-body"><div className="pos-section-title"><div><h2>Ventas y comprobantes</h2><p>Consulta las últimas 50 ventas o busca por ID exacto.</p></div><button disabled={busy} onClick={onClose}>Cerrar</button></div>
    {error && <p className="pos-error" role="alert">{error}</p>}{success && <p className="pos-notice" role="status">{success}</p>}
    {receipt && canReverse && <p className="pos-notice">Reembolso de las unidades seleccionadas: <strong>{currency(refundTotal)}</strong> · {paymentNames[receipt.payment]}. El backend verificará el importe antes de registrarlo.</p>}
    {pending ? <div className="pos-notice">Hay una devolución pendiente de confirmar.<button disabled={busy} onClick={() => void reverse()}>Recuperar resultado / reintentar</button></div> : <form className="pos-search" onSubmit={event => { event.preventDefault(); void select(saleId) }}><input aria-label="ID de venta" value={saleId} onChange={event => setSaleId(event.target.value)} placeholder="ID de venta" required /><button disabled={busy}>Buscar venta</button></form>}
    {!receipt && !pending && <table><thead><tr><th>Venta</th><th>Fecha</th><th>Total</th><th>Consulta</th></tr></thead><tbody>{sales.map(sale => <tr key={sale.id}><td>{sale.id.slice(0, 8)}</td><td>{new Date(sale.date).toLocaleString('es-CL')}</td><td>{currency(sale.total)}</td><td><button disabled={busy} onClick={() => void select(sale.id)}>Ver venta</button></td></tr>)}</tbody></table>}
    {receipt && <><div className="pos-section-title"><p>{receipt.branch} · {paymentNames[receipt.payment]} · Total {currency(receipt.total)}</p><button disabled={busy || !!pending} onClick={() => { onReceipt(receipt); onClose() }}>Ver comprobante</button></div>{canReverse && <form onSubmit={event => void reverse(event)}><fieldset disabled={busy || !!pending} className="pos-return-fields"><legend>Registrar anulación o devolución</legend><p>El reembolso utiliza el medio de pago original y se registra en tu caja abierta. Las unidades aptas regresan al lote y sucursal de la venta original.</p><label>Tipo de operación<select value={kind} onChange={event => setKind(event.target.value as typeof kind)}><option value="DEVOLUCION">Devolución de unidades</option><option value="ANULACION">Anulación completa (sin devoluciones anteriores)</option></select></label><table><thead><tr><th>Producto / lote</th><th>Pendientes</th><th>Devolver</th><th>Condición</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.sale_lot_id}><td>{row.name}<small>{row.lot}</small></td><td>{row.available}</td><td><input aria-label={`Devolver ${row.name} lote ${row.lot}`} type="number" min="0" max={row.available} step="1" value={row.quantity} onChange={event => { const quantity = Number(event.target.value); if (Number.isInteger(quantity) && quantity >= 0 && quantity <= row.available) setRows(rows.map((value, i) => i === index ? { ...value, quantity } : value)) }} /></td><td><label><span><input type="checkbox" checked={row.restock} onChange={event => setRows(rows.map((value, i) => i === index ? { ...value, restock: event.target.checked } : value))} /> Confirmo que está apto para venta</span></label><input aria-label={`Condición de ${row.name}`} placeholder="Describe la condición revisada" maxLength={250} required={row.quantity > 0} value={row.condition} onChange={event => setRows(rows.map((value, i) => i === index ? { ...value, condition: event.target.value } : value))} /></td></tr>)}</tbody></table><label>Motivo obligatorio<textarea required maxLength={250} value={reason} onChange={event => setReason(event.target.value)} /></label><label><span><input type="checkbox" required checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> Confirmo las cantidades, la condición y el reembolso. Esta operación quedará registrada.</span></label><button>{busy ? 'Registrando…' : 'Confirmar operación'}</button></fieldset></form>}</>}
  </div></dialog>
}
