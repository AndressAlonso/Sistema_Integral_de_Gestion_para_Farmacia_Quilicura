import { useEffect, useState } from 'react'
import OrderPreparationDialog from './OrderPreparationDialog'
import OrderColumnFilter from './OrderColumnFilter'
import { listOrders, orderStateLabel, orderStates, type OrderList, type OrderSort } from './orders.api'
import '../e1-access-users-branches/users/users.css'
import '../e4-transfers/transfers.css'
import './orders.css'

export default function OrdersPage() {
  const [data, setData] = useState<OrderList | null>(null)
  const [states, setStates] = useState(Object.keys(orderStates))
  const [sort, setSort] = useState<OrderSort>('newest')
  const [branches, setBranches] = useState<string[] | null>(null)
  const [page, setPage] = useState(1)
  const [attempt, setAttempt] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    listOrders(states, branches, page, sort).then(result => { if (active) { setData(result); setError('') } })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'No se pudieron cargar los pedidos.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [states, sort, branches, page, attempt])
  function refresh() { setLoading(true); setAttempt(n => n + 1) }
  return <section className="users-page orders-page">
    <header className="users-heading"><div><h1>Pedidos Online</h1><p>Prepara los productos y confirma cuándo están listos para retiro.</p></div><button type="button" className="users-button orders-refresh" disabled={loading} onClick={refresh} aria-label="Actualizar pedidos" title="Actualizar pedidos"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6.1 7a7 7 0 0 1 11.8-1L20 9M4 15l2.1 3A7 7 0 0 0 17.9 17" /></svg></button></header>
    {error && <p className="users-error" role="alert">{error}</p>}
    <section className="users-panel" aria-busy={loading}><><div className="users-table-scroll"><table className="users-table"><thead><tr><th>Pedido</th><th aria-sort={sort === 'branch_asc' ? 'ascending' : sort === 'branch_desc' ? 'descending' : 'none'}><OrderColumnFilter column="branch" options={Object.fromEntries((data?.branches ?? []).map(branch => [branch.id, branch.name]))} states={branches ?? data?.branches.map(branch => branch.id) ?? []} sort={sort} onApply={(nextBranches, nextSort) => { setBranches(nextBranches.length === data?.branches.length ? null : nextBranches); setSort(nextSort); setPage(1); setLoading(true); setAttempt(n => n + 1) }} /></th><th>Productos</th><th aria-sort={sort === 'state_asc' ? 'ascending' : sort === 'state_desc' ? 'descending' : 'none'}><OrderColumnFilter states={states} sort={sort} onApply={(nextStates, nextSort) => { setStates(nextStates); setSort(nextSort); setPage(1); setLoading(true) }} /></th></tr></thead><tbody>{loading ? <tr><td colSpan={4} role="status">Cargando pedidos…</td></tr> : !error && <>{data?.orders.map(order => <tr key={order.id} className="orders-clickable-row" onClick={() => setSelected(order.id)}><td><button className="orders-open" onClick={event => { event.stopPropagation(); setSelected(order.id) }} aria-label={`Abrir pedido ${order.number}`}>{order.number}<span className="orders-row-hint" aria-hidden="true">Ver detalle →</span></button><small>{new Date(order.created_at).toLocaleString('es-CL')}</small></td><td>{order.pickup_branch.name}</td><td>{order.items.reduce((sum, item) => sum + item.quantity, 0)} unidades · {order.items.length} productos</td><td><span className={`order-state order-state-${order.status}`}>{orderStateLabel(order.status)}</span></td></tr>)}{!data?.orders.length && <tr><td colSpan={4} className="users-empty">No hay pedidos con estos filtros.</td></tr>}</>}</tbody></table></div><footer className="orders-pagination"><span>{data?.total ?? 0} pedidos · Página {page}</span><button className="users-button" disabled={loading || !!error || page === 1} onClick={() => { setPage(n => n - 1); setLoading(true) }}>Anterior</button><button className="users-button" disabled={loading || !!error || page * 15 >= (data?.total ?? 0)} onClick={() => { setPage(n => n + 1); setLoading(true) }}>Siguiente</button></footer></></section>
    {selected && <OrderPreparationDialog id={selected} onClose={() => setSelected(null)} onChanged={refresh} />}
  </section>
}
