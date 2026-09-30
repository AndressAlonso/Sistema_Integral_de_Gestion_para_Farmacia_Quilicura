import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../../services/http'
import { createReceipt, receiptProducts, type ReceiptProduct } from './receipts.api'
import { createAdjustment, operationOptions, type OperationOptions, type StockLot } from './stock-operations.api'
import './stock-operations.css'

type Operation = 'receipt' | 'adjustment'
interface Draft {
  kind: Operation; requestId: string; branchId: string; reason: string; supplier: string
  documentType: 'GUIA' | 'FACTURA'; documentNumber: string; documentDate: string
  rows: { lot: StockLot; quantity: string }[]
}
function initial(key: string, kind: Operation): { draft: Draft; pending: boolean } {
  try {
    const saved: Draft | null = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (saved && ['receipt', 'adjustment'].includes(saved.kind) && typeof saved.requestId === 'string'
      && Array.isArray(saved.rows) && saved.rows.every(row => row.lot?.id && typeof row.quantity === 'string')) return { draft: saved, pending: true }
  } catch { /* Un borrador ilegible no sustituye un formulario nuevo. */ }
  return { pending: false, draft: { kind, requestId: crypto.randomUUID(), branchId: '', reason: '', supplier: '',
    documentType: 'FACTURA', documentNumber: '', documentDate: new Date().toISOString().slice(0, 10), rows: [] } }
}

export default function StockOperationDialog({ userId, canReceive, onClose, onSaved }: {
  userId: string; canReceive: boolean; onClose: () => void; onSaved: (message: string) => void
}) {
  const key = `sigfq-stock-operation:${userId}`
  const [start] = useState(() => initial(key, canReceive ? 'receipt' : 'adjustment'))
  const [draft, setDraft] = useState(start.draft)
  const [pending, setPending] = useState(start.pending)
  const [options, setOptions] = useState<OperationOptions | null>(null)
  const [products, setProducts] = useState<ReceiptProduct[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [confirmed, setConfirmed] = useState(false)
  const [lotId, setLotId] = useState('')
  const [attempt, setAttempt] = useState(0)
  const sending = useRef(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const [today] = useState(() => new Date().toISOString().slice(0, 10))
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { if (element?.open) element.close() }
  }, [])
  useEffect(() => {
    let active = true
    operationOptions().then(async data => {
      const catalog = data.can_receive ? await receiptProducts() : []
      if (active) { setOptions(data); setProducts(catalog); setLoading(false); setError('') }
    })
      .catch((cause: unknown) => { if (active) { setError(cause instanceof Error ? cause.message : 'No se pudieron cargar los lotes.'); setLoading(false) } })
    return () => { active = false }
  }, [attempt])
  const receipt = draft.kind === 'receipt'
  const available = options?.lots.filter(lot => lot.branch_id === draft.branchId && (!receipt || lot.expiration_date > today)) ?? []
  const changed = draft.rows.filter(row => Number(row.quantity) !== row.lot.quantity)
  const count = receipt ? draft.rows.length : changed.length
  const permitted = receipt ? options?.can_receive : options?.can_adjust
  function update(changes: Partial<Draft>) { setDraft(current => ({ ...current, ...changes })); setConfirmed(false) }
  function updateReceiptLot(index: number, number: string) {
    update({ rows: draft.rows.map((row, i) => {
      if (i !== index) return row
      const existing = available.find(lot => lot.product_id === row.lot.product_id && lot.number === number.trim())
      return { ...row, lot: { ...row.lot, number, expiration_date: existing?.expiration_date ?? row.lot.expiration_date } }
    }) })
  }
  function reload() {
    if (sending.current || pending) return
    setLoading(true); setConfirmed(false)
    operationOptions().then(async data => {
      const catalog = data.can_receive ? await receiptProducts() : []
      setProducts(catalog)
      setOptions(data)
      if (receipt) { setError(''); return }
      const lots = new Map(data.lots.map(lot => [lot.id, lot]))
      if (draft.rows.some(row => !lots.has(row.lot.id))) {
        setError('Un lote ya no está disponible. Quítalo del formulario antes de continuar.')
      } else {
        setDraft(current => ({ ...current, rows: current.rows.map(row => ({ ...row, lot: lots.get(row.lot.id) ?? row.lot })) }))
        setError('')
      }
    }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'No se pudo actualizar.'))
      .finally(() => setLoading(false))
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (sending.current || !confirmed || !count) return
    if (receipt) {
      const keys = draft.rows.map(row => JSON.stringify([row.lot.product_id, row.lot.number.trim()]))
      if (new Set(keys).size !== keys.length) {
        setError('Repetiste el mismo producto y lote. Reúne sus unidades en una sola fila.'); return
      }
      if (draft.rows.some(row => !row.lot.number.trim() || !row.lot.expiration_date || row.lot.expiration_date <= today)) {
        setError('Completa el lote indicado en el envase y un vencimiento futuro en cada fila.'); return
      }
    }
    try { sessionStorage.setItem(key, JSON.stringify(draft)) }
    catch { setError('Habilita el almacenamiento del navegador para conservar los reintentos.'); return }
    sending.current = true; setBusy(true); setPending(true); setError('')
    try {
      let id: string
      if (receipt) {
        const result = await createReceipt({ request_id: draft.requestId, branch_id: draft.branchId,
          supplier: draft.supplier, document_type: draft.documentType, document_number: draft.documentNumber, document_date: draft.documentDate,
          items: draft.rows.map(row => ({ product_id: row.lot.product_id, lot_number: row.lot.number, expiration_date: row.lot.expiration_date, quantity: Number(row.quantity) })) })
        id = result.id
      } else {
        const result = await createAdjustment({ request_id: draft.requestId, branch_id: draft.branchId, reason: draft.reason,
          items: changed.map(row => ({ lot_id: row.lot.id, expected_quantity: row.lot.quantity, new_quantity: Number(row.quantity) })) })
        id = result.id
      }
      sessionStorage.removeItem(key)
      onSaved(`${receipt ? 'Recepción' : 'Ajuste'} confirmado: ${count} ${count === 1 ? 'fila' : 'filas'}. ID: ${id}. Puedes consultar los movimientos en Inventario.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No se pudo confirmar la operación.')
      if (cause instanceof ApiError && [400, 409, 422].includes(cause.status)) {
        sessionStorage.removeItem(key); setPending(false); setConfirmed(false)
        setDraft(current => ({ ...current, requestId: crypto.randomUUID() }))
      }
    } finally { sending.current = false; setBusy(false) }
  }
  return <dialog ref={dialog} className="app-modal users-dialog users-dialog-fullscreen stock-operation-dialog" aria-labelledby="stock-operation-title" aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!sending.current) onClose() }}>
    <form onSubmit={event => { void submit(event) }}>
      <header className="users-dialog-heading"><div><h2 id="stock-operation-title">Registrar movimiento</h2><p>Recepción de mercadería o ajuste de cantidades. Prepara varias filas y confirma todo junto.</p></div>
        <button type="button" className="users-close" disabled={busy} onClick={onClose} aria-label="Cerrar movimiento">×</button></header>
      {loading && <p role="status">Cargando productos, sucursales y lotes…</p>}
      {pending && <p className="transfer-notice" role="status">Hay una operación pendiente de confirmación. Conservamos sus datos para que puedas reintentar sin duplicarla.</p>}
      <fieldset className="users-fields" disabled={busy || pending || loading || !options}>
        <legend className="sr-only">Tipo de operación y respaldo</legend>
        <label>Tipo de operación<select value={draft.kind} onChange={event => { update({ kind: event.target.value as Operation, rows: [] }); setLotId('') }}>
          {(options?.can_receive || receipt) && <option value="receipt" disabled={!options?.can_receive}>Recepción de mercadería</option>}
          {(options?.can_adjust || !receipt) && <option value="adjustment" disabled={!options?.can_adjust}>Ajuste de inventario</option>}
        </select></label>
        <label>Sucursal *<select required value={draft.branchId} onChange={event => { update({ branchId: event.target.value, rows: [] }); setLotId('') }}>
          <option value="">Selecciona una sucursal</option>{options?.branches.map(branch => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
        </select></label>
        {receipt ? <>
          <label>Proveedor *<input required maxLength={150} value={draft.supplier} onChange={event => update({ supplier: event.target.value })} /></label>
          <label>Documento<select value={draft.documentType} onChange={event => update({ documentType: event.target.value as 'GUIA' | 'FACTURA' })}><option value="FACTURA">Factura</option><option value="GUIA">Guía de despacho</option></select></label>
          <label>Número de documento *<input required maxLength={80} value={draft.documentNumber} onChange={event => update({ documentNumber: event.target.value })} /></label>
          <label>Fecha del documento *<input type="date" required max={today} value={draft.documentDate} onChange={event => update({ documentDate: event.target.value })} /></label>
        </> : <label className="transfer-wide">Motivo del ajuste *<textarea required maxLength={250} placeholder="Explica la diferencia detectada en el inventario" value={draft.reason} onChange={event => update({ reason: event.target.value })} /></label>}
        <p className="transfer-wide">{receipt ? 'Selecciona productos del catálogo, aunque no tengan existencias. Ingresa las unidades recibidas y el lote y vencimiento del envase. Al confirmar se registrarán los lotes y se sumarán las cantidades; no necesitas crearlos antes en Inventario.' : 'Escribe la cantidad final de cada lote: se registrarán el valor anterior, el nuevo y su diferencia.'}</p>
        <label className="transfer-wide">{receipt ? 'Producto del catálogo' : 'Producto / lote existente'}<select disabled={!draft.branchId} value={lotId} onChange={event => setLotId(event.target.value)}>
          <option value="">Selecciona para agregar una fila</option>{receipt
            ? products.map(product => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)
            : available.filter(lot => !draft.rows.some(row => row.lot.id === lot.id)).map(lot => <option key={lot.id} value={lot.id}>{lot.product_name} · {lot.sku} · Lote {lot.number} · {lot.quantity} unidades</option>)}
        </select></label>
        <button type="button" className="users-button" disabled={!lotId || draft.rows.length >= 100} onClick={() => {
          if (receipt) {
            const product = products.find(item => item.id === lotId)
            if (product) update({ rows: [...draft.rows, { lot: { id: crypto.randomUUID(), product_id: product.id,
              product_name: product.name, sku: product.sku, branch_id: draft.branchId,
              number: '', expiration_date: '', quantity: 0 }, quantity: '1' }] })
            setLotId(''); return
          }
          const lot = available.find(item => item.id === lotId)
          if (lot) { update({ rows: [...draft.rows, { lot, quantity: receipt ? '1' : String(lot.quantity) }] }); setLotId('') }
        }}>{receipt ? '+ Agregar producto' : '+ Agregar producto / lote'}</button>
        {receipt && !products.length && <p className="transfer-notice transfer-wide">No hay productos activos en el catálogo.</p>}
        {!receipt && draft.branchId && !available.length && <p className="transfer-notice transfer-wide">No hay lotes disponibles para ajustar en esta sucursal.</p>}
        <div className="users-table-scroll transfer-wide"><table className="users-table stock-operation-table"><thead><tr><th>Producto</th><th>Lote / vencimiento</th><th>Cantidad actual del lote</th><th>{receipt ? 'Unidades recibidas' : 'Cantidad final'}</th><th>{receipt ? 'Quedarán en el lote' : 'Diferencia'}</th><th>Fila</th></tr></thead>
          <tbody>{!draft.rows.length && <tr><td className="users-empty" colSpan={6}>Agrega los productos que necesitas modificar.</td></tr>}{draft.rows.map((row, index) => <tr key={row.lot.id}>
            <td>{row.lot.product_name}<small>{row.lot.sku}</small></td><td>{receipt ? <>
              <label>Lote del envase<input required maxLength={80} list={`receipt-lots-${index}`} aria-label={`Lote de ${row.lot.product_name}, fila ${index + 1}`} value={row.lot.number}
                onChange={event => updateReceiptLot(index, event.target.value)} /></label>
              <datalist id={`receipt-lots-${index}`}>{available.filter(lot => lot.product_id === row.lot.product_id).map(lot => <option key={lot.id} value={lot.number}>{lot.expiration_date}</option>)}</datalist>
              <label>Vencimiento<input required type="date" min={new Date(new Date(`${today}T00:00:00Z`).getTime() + 86400000).toISOString().slice(0, 10)} aria-label={`Vencimiento de ${row.lot.product_name}, fila ${index + 1}`} value={row.lot.expiration_date}
                onChange={event => update({ rows: draft.rows.map((value, i) => i === index ? { ...value, lot: { ...value.lot, expiration_date: event.target.value } } : value) })} /></label>
            </> : <>{row.lot.number}<small>{row.lot.expiration_date}</small></>}</td><td>{receipt ? (available.find(lot => lot.product_id === row.lot.product_id && lot.number === row.lot.number.trim())?.quantity ?? 0) : row.lot.quantity}</td>
            <td><input aria-label={`${receipt ? 'Unidades recibidas' : 'Cantidad final'} de ${row.lot.product_name}, lote ${row.lot.number}`} type="number" required min={receipt ? 1 : 0} max={receipt ? 1000000 : 2147483647} step={1} value={row.quantity} onChange={event => update({ rows: draft.rows.map((value, i) => i === index ? { ...value, quantity: event.target.value } : value) })} /></td>
            <td>{row.quantity === '' ? '—' : receipt ? (available.find(lot => lot.product_id === row.lot.product_id && lot.number === row.lot.number.trim())?.quantity ?? 0) + Number(row.quantity) : Number(row.quantity) - row.lot.quantity}</td>
            <td><button type="button" className="users-button" aria-label={`Quitar ${row.lot.product_name}, lote ${row.lot.number}`} onClick={() => update({ rows: draft.rows.filter((_, i) => i !== index) })}>Quitar</button></td>
          </tr>)}</tbody></table></div>
        <button type="button" className="users-button" onClick={reload}>Actualizar cantidades actuales</button>
      </fieldset>
      {error && <p className="users-error" role="alert">{error}</p>}
      {!options && !loading && <button type="button" className="users-button" onClick={() => { setLoading(true); setAttempt(value => value + 1) }}>Reintentar carga</button>}
      <label className="stock-confirmation"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />Confirmo {count} {count === 1 ? 'fila' : 'filas'} y los datos de respaldo. Se guardarán juntos.</label>
      <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={onClose}>{pending ? 'Cerrar y conservar pendiente' : 'Cancelar'}</button>
        <button type="submit" className="users-button primary" disabled={busy || !confirmed || !count || (!pending && (loading || !permitted))}>{busy ? 'Guardando…' : pending ? 'Reintentar confirmación' : 'Guardar movimiento'}</button></footer>
    </form>
  </dialog>
}
