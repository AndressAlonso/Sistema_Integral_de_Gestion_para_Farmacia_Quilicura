import { useEffect, useRef, useState } from 'react'
import Notification from '../../components/Notification'
import { apiRequest } from '../../services/http'
import '../e1-access-users-branches/users/users.css'
import './audit.css'

type Json = string | number | boolean | null | Json[] | { [key: string]: Json }
interface AuditEvent {
  id: string; at: string; action: string; reference: string
  actor: { id: string | null; name: string }
  branch: { id: string; name: string } | null
  data: Record<string, Json>
}
interface AuditList {
  events: AuditEvent[]; total: number; page: number; limit: number
  branches: { id: string; name: string }[]
}
const labels: Record<string, string> = {
  usuario_interno: 'Usuario', rol: 'Rol', sucursal: 'Sucursal', categoria: 'Categoría',
  producto: 'Producto', codigo_barra: 'Código de barras', inventario_sucursal: 'Inventario',
  movimiento_inventario: 'Movimiento de inventario', recepcion_mercaderia: 'Recepción',
  ajuste_inventario: 'Ajuste de inventario', transferencia: 'Transferencia', sesion_caja: 'Caja',
  venta: 'Venta', reversa_venta: 'Reversa de venta', E7_H4_ESTADO: 'Estado del pedido',
  'E7-H4_ESTADO': 'Estado del pedido', 'E7-H3_PAGO_SIMULADO': 'Pago de prueba',
}
const label = (key: string) => labels[key] ?? key.replaceAll('_', ' ')
const actionLabel = (action: string) => action.split('.').map(label).join(' · ')
const timestamp = (at: string) => new Date(at).toLocaleString('es-CL', { timeZone: 'America/Santiago' })
function DetailValue({ value }: { value: Json }) {
  if (value === null) return <span className="audit-muted">Sin valor</span>
  if (typeof value === 'boolean') return <>{value ? 'Sí' : 'No'}</>
  if (Array.isArray(value)) return <>{value.length ? value.map((item, index) => <div key={index}><DetailValue value={item} /></div>) : 'Sin elementos'}</>
  if (typeof value === 'object') return <dl className="audit-values">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{label(key)}</dt><dd><DetailValue value={item} /></dd></div>)}</dl>
  return <>{String(value)}</>
}
function AuditDetail({ event, onClose }: { event: AuditEvent; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className="audit-dialog" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose() }} aria-labelledby="audit-detail-title">
    <header><div><span className="audit-tag">Registro de auditoría</span><h2 id="audit-detail-title">{actionLabel(event.action)}</h2></div><button className="users-button" onClick={onClose} aria-label="Cerrar detalle">✕</button></header>
    <p>{event.reference}</p><dl className="audit-summary"><div><dt>Responsable</dt><dd>{event.actor.name}</dd></div><div><dt>Fecha y hora</dt><dd>{timestamp(event.at)}</dd></div><div><dt>Sucursal</dt><dd>{event.branch?.name ?? 'General'}</dd></div></dl>
    <h3>Detalle de la operación</h3><DetailValue value={event.data} />
    <footer className="audit-muted">Este registro es de solo lectura. ID: {event.id}</footer>
  </dialog>
}
export default function AuditPage() {
  const [data, setData] = useState<AuditList | null>(null)
  const [draft, setDraft] = useState({ branch_id: '', date_from: '', date_to: '' })
  const [filters, setFilters] = useState(draft)
  const [page, setPage] = useState(1)
  const [attempt, setAttempt] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<AuditEvent | null>(null)
  useEffect(() => {
    let active = true
    const query = new URLSearchParams({ page: String(page), limit: '20' })
    Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value) })
    apiRequest(`/api/audit?${query}`, {}, {}, true).then(response => response.json()).then((result: AuditList) => {
      if (active) { setData(result); setError('') }
    }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'No se pudo cargar la auditoría.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [filters, page, attempt])
  const refresh = () => { setLoading(true); setAttempt(n => n + 1) }
  return <section className="users-page audit-page">
    <header className="users-heading"><div><h1>Auditoría</h1><p>Consulta quién realizó cada operación y revisa sus cambios.</p></div><button className="users-button" onClick={refresh} disabled={loading} aria-label="Actualizar auditoría" title="Actualizar auditoría"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1" /></svg></button></header>
    {error && <Notification message={error} kind="error" />}
    <form className="users-panel audit-filters" onSubmit={e => { e.preventDefault(); if (draft.date_from && draft.date_to && draft.date_from > draft.date_to) { setError('La fecha inicial no puede ser posterior a la fecha final.'); return } setFilters({ ...draft }); setPage(1); setLoading(true) }}>
      <label>Sucursal<select value={draft.branch_id} onChange={e => setDraft({ ...draft, branch_id: e.target.value })}><option value="">Todas las sucursales</option>{data?.branches.map(branch => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>
      <label>Desde<input type="date" value={draft.date_from} onChange={e => setDraft({ ...draft, date_from: e.target.value })} /></label>
      <label>Hasta<input type="date" value={draft.date_to} onChange={e => setDraft({ ...draft, date_to: e.target.value })} /></label>
      <button className="users-button users-button-primary" type="submit" disabled={loading}>Aplicar filtros</button><button className="users-button" type="button" disabled={loading} onClick={() => { const empty = { branch_id: '', date_from: '', date_to: '' }; setDraft(empty); setFilters(empty); setPage(1); setLoading(true) }}>Limpiar</button>
      <small>Fechas y horas de Chile · Incluye ambos días del período.</small>
    </form>
    <section className="users-panel" aria-busy={loading}><div className="users-table-scroll"><table className="users-table"><thead><tr><th>Fecha y hora</th><th>Responsable</th><th>Operación</th><th>Sucursal</th><th>Detalle</th></tr></thead><tbody>
      {loading ? <tr><td colSpan={5} role="status">Cargando operaciones…</td></tr> : error ? <tr><td colSpan={5}>No se pudo mostrar el registro. <button className="users-button" onClick={refresh}>Reintentar</button></td></tr> : data?.events.length ? data.events.map(event => <tr key={event.id} className="audit-row" onClick={() => setSelected(event)}><td>{timestamp(event.at)}</td><td>{event.actor.name}</td><td><strong>{actionLabel(event.action)}</strong><small>{event.reference}</small></td><td>{event.branch?.name ?? 'General'}</td><td><button className="users-button" aria-label={`Ver detalle de ${event.reference}`} onClick={e => { e.stopPropagation(); setSelected(event) }}>Ver detalle →</button></td></tr>) : <tr><td colSpan={5} className="users-empty">No hay operaciones para estos filtros.</td></tr>}
    </tbody></table></div><footer className="audit-pagination"><span>{data?.total ?? 0} operaciones · Página {page}</span><button className="users-button" disabled={loading || !!error || page === 1} onClick={() => { setPage(n => n - 1); setLoading(true) }}>Anterior</button><button className="users-button" disabled={loading || !!error || page * 20 >= (data?.total ?? 0)} onClick={() => { setPage(n => n + 1); setLoading(true) }}>Siguiente</button></footer></section>
    {selected && <AuditDetail event={selected} onClose={() => setSelected(null)} />}
  </section>
}
