import { useEffect, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import type { AuthSession } from '../e1-access-users-branches/auth/login.api'
import { ApiError } from '../../services/http'
import TransferDetail from './TransferDetail'
import TransferForm from './TransferForm'
import StockOperationDialog from './StockOperationDialog'
import { actions, listTransfers, states, transferCode, transferOptions, units, type Transfer, type TransferAction, type TransferOptions } from './transfers.api'
import '../e1-access-users-branches/users/users.css'
import './transfers.css'

export default function TransfersPage() {
  const session = useOutletContext<AuthSession>()
  const navigate = useNavigate()
  const [transfers, setTransfers] = useState<Transfer[]>([])
  const [options, setOptions] = useState<TransferOptions | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [creating, setCreating] = useState(false)
  const [movementOpen, setMovementOpen] = useState(false)
  const [selected, setSelected] = useState<{ transfer: Transfer; action?: TransferAction } | null>(null)
  const [filters, setFilters] = useState({ query: '', state: '', origin: '', destination: '', date: '' })
  useEffect(() => {
    let active = true
    Promise.all([listTransfers(), transferOptions()]).then(([data, choices]) => {
      if (active) { setTransfers(data.transfers); setOptions(choices); setLoading(false); setError('') }
    }).catch((cause: unknown) => {
      if (!active) return
      if (cause instanceof ApiError && cause.status === 401) navigate('/login', { replace: true })
      setError(cause instanceof Error ? cause.message : 'No se pudieron cargar las transferencias.'); setLoading(false)
    })
    return () => { active = false }
  }, [attempt, navigate])

  function refresh() { setLoading(true); setAttempt(value => value + 1) }
  function saved(transfer: Transfer) {
    setCreating(false); setSelected(null)
    setMessage(`${transferCode(transfer.id)}: ${states[transfer.state]}. Operación confirmada.`)
    refresh()
  }
  const branches = new Map(options?.branches.map(branch => [branch.id, branch.name]))
  for (const transfer of transfers) {
    branches.set(transfer.origin_id, transfer.origin_name); branches.set(transfer.destination_id, transfer.destination_name)
  }
  const query = filters.query.trim().toLocaleLowerCase('es')
  const filtered = transfers.filter(transfer =>
    (!filters.state || transfer.state === filters.state) && (!filters.origin || transfer.origin_id === filters.origin) &&
    (!filters.destination || transfer.destination_id === filters.destination) &&
    (!filters.date || localDate(transfer.created_at) === filters.date) &&
    (!query || [transfer.id, transferCode(transfer.id), transfer.requested_by, ...transfer.items.map(item => `${item.product_name} ${item.sku}`)].join(' ').toLocaleLowerCase('es').includes(query)))
  const today = localDate(new Date().toISOString())
  const summaries = [
    ['Solicitadas', transfers.filter(t => t.state === 'SOLICITADA').length, 'Pendientes de autorización'],
    ['Autorizadas', transfers.filter(t => t.state === 'AUTORIZADA').length, 'Listas para despacho'],
    ['En tránsito', transfers.filter(t => t.state === 'EN_TRANSITO').length, 'Pendientes de recepción'],
    ['Recibidas hoy', transfers.filter(t => t.state === 'RECIBIDA' && t.timeline.some(event => event.event === 'Recibida' && localDate(event.at) === today)).length, 'Recepciones confirmadas'],
  ] as const

  return <div className="users-page transfers-page">
    <header className="users-heading transfer-heading"><div><h1>Transferencias</h1><p>Gestiona solicitudes, autorizaciones, despachos y recepciones entre sucursales.</p></div>
      <div className="transfer-actions">
        {(session.user.permissions.includes('inventario.registrar_entrada') || (
          session.user.permissions.includes('inventario.ajustar')
          && session.user.roles.some(role => ['ADMINISTRADOR', 'ENCARGADO_INVENTARIO'].includes(role))
        )) && <button type="button" className="users-button" onClick={() => { setMessage(''); setMovementOpen(true) }}>Registrar movimiento</button>}
        {options?.can_create && <button type="button" className="users-button primary" disabled={loading} onClick={() => { setMessage(''); setCreating(true) }}>+ Nueva transferencia</button>}
      </div></header>
    <section className="users-panel transfer-flow" aria-label="Flujo de transferencia"><div><strong>Flujo de transferencia</strong><p>Se reserva al solicitar; el stock físico sale al confirmar el despacho.</p></div>
      <div>{(['SOLICITADA', 'AUTORIZADA', 'EN_TRANSITO', 'RECIBIDA'] as const).map((state, index) => <span key={state}>{index > 0 && <span aria-hidden="true"> → </span>}<span className={`transfer-state ${state.toLowerCase()}`}>{states[state]}</span></span>)}</div></section>
    <div className="transfer-summaries" aria-label="Resumen de las transferencias visibles">{summaries.map(([label, count, help]) => <div key={label}><span>{label}</span><strong>{loading ? '—' : count}</strong><small>{help}</small></div>)}</div>
    {message && <p className="users-success" role="status">{message}</p>}
    {error && <p className="users-error" role="alert">{error}</p>}
    <section className="users-panel transfer-filter-panel" aria-label="Filtros de transferencias"><h2>Transferencias entre sucursales</h2><p>Filtra por producto, responsable, estado, ruta o fecha de solicitud.</p>
      <div className="transfer-filters">
        <label>Buscar<input type="search" placeholder="ID, producto o responsable…" value={filters.query} onChange={event => setFilters({ ...filters, query: event.target.value })} /></label>
        <label>Estado<select value={filters.state} onChange={event => setFilters({ ...filters, state: event.target.value })}><option value="">Todos</option>{Object.entries(states).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
        <label>Origen<select value={filters.origin} onChange={event => setFilters({ ...filters, origin: event.target.value })}><option value="">Todas</option>{[...branches].map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
        <label>Destino<select value={filters.destination} onChange={event => setFilters({ ...filters, destination: event.target.value })}><option value="">Todas</option>{[...branches].map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
        <label>Fecha<input type="date" value={filters.date} onChange={event => setFilters({ ...filters, date: event.target.value })} /></label>
      </div><div className="transfer-actions"><button type="button" className="users-button" disabled={!Object.values(filters).some(Boolean)} onClick={() => setFilters({ query: '', state: '', origin: '', destination: '', date: '' })}>Limpiar filtros</button><button type="button" className="users-button" disabled={loading} onClick={refresh}>{loading ? 'Actualizando…' : 'Actualizar listado'}</button></div>
    </section>
    <section className="users-panel" aria-busy={loading}><header className="users-panel-heading"><h2>Listado de transferencias</h2><p>{filtered.length} resultados · Las acciones dependen del estado, permisos y sucursal asignada.</p></header>
      <div className="users-table-scroll"><table className="users-table transfer-table"><thead><tr>{['ID', 'Fecha', 'Ruta', 'Productos', 'Unidades', 'Reserva', 'Responsable', 'Estado', 'Acciones'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
        <tbody>{!filtered.length && <tr><td colSpan={9} className="users-empty">{loading ? 'Cargando transferencias…' : error ? 'No se pudo actualizar el listado.' : 'No hay transferencias que coincidan con los filtros.'}</td></tr>}
          {filtered.map(transfer => <tr key={transfer.id}>
            <td><button type="button" className="transfer-link" onClick={() => setSelected({ transfer })}>{transferCode(transfer.id)}</button></td>
            <td>{new Date(transfer.created_at).toLocaleDateString('es-CL')}<small>{new Date(transfer.created_at).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })}</small></td>
            <td>{transfer.origin_name}<span className="transfer-route-arrow">→</span>{transfer.destination_name}</td><td>{transfer.items.length}</td><td>{units(transfer)}</td>
            <td>{['SOLICITADA', 'AUTORIZADA'].includes(transfer.state) ? `${units(transfer)} reservadas` : transfer.state === 'RECHAZADA' ? 'Liberada al rechazar' : 'Liberada al despachar'}</td>
            <td>{transfer.requested_by}</td><td><span className={`transfer-state ${transfer.state.toLowerCase()}`}>{states[transfer.state]}</span></td>
            <td><div className="users-row-actions">{transfer.actions.map(action => <button type="button" key={action} onClick={() => setSelected({ transfer, action })}>{actions[action]}</button>)}<button type="button" aria-label={`Ver detalle ${transferCode(transfer.id)}`} onClick={() => setSelected({ transfer })}>Ver detalle</button></div></td>
          </tr>)}</tbody></table></div></section>
    {creating && options && <TransferForm options={options} userId={session.user.id} onClose={() => { setCreating(false); refresh() }} onSaved={saved} />}
    {selected && <TransferDetail transfer={selected.transfer} initialAction={selected.action} onClose={() => { setSelected(null); refresh() }} onChanged={saved} />}
    {movementOpen && <StockOperationDialog userId={session.user.id} canReceive={session.user.permissions.includes('inventario.registrar_entrada')} onClose={() => setMovementOpen(false)} onSaved={text => { setMovementOpen(false); setMessage(text); refresh() }} />}
  </div>
}

function localDate(value: string) {
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
