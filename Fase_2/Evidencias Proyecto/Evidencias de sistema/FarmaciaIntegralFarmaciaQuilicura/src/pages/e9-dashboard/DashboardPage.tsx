import { useEffect, useState } from 'react'
import Notification from '../../components/Notification'
import { Bars, PaymentChart, SalesChart } from './DashboardCharts'
import { currency, getDashboard, number, type DashboardData } from './dashboard.api'
import { displayDate, initialDashboardFilters, type OperationalFilters as Filters } from './filters'
import MetricIcon from './MetricIcon'
import OperationalFilters from './OperationalFilters'
import './dashboard.css'

export default function DashboardPage() {
  const [filters, setFilters] = useState(initialDashboardFilters)
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [alertTab, setAlertTab] = useState<'stock' | 'expiry'>('stock')
  useEffect(() => {
    let active = true
    getDashboard(filters).then(result => {
      if (active) { setData(result); setError('') }
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : 'No se pudieron cargar los indicadores.')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [filters, attempt])
  const changeFilters = (next: Filters) => { setLoading(true); setError(''); setFilters(next) }
  const refresh = () => { setLoading(true); setError(''); setAttempt(value => value + 1) }
  const branchName = data?.branches.find(branch => branch.id === filters.branch_id)?.name ?? 'Todas las sucursales'
  return <section className="dashboard-page">
    <header className="dashboard-heading app-page-heading">
      <div><span className="dashboard-eyebrow">PANORAMA OPERATIVO</span><h1>Resumen</h1><p>Lo esencial de tu farmacia, en un vistazo.</p></div>
      <button type="button" className="dashboard-refresh" aria-label="Actualizar indicadores" title="Actualizar indicadores" disabled={loading} onClick={refresh}><MetricIcon name="refresh" /></button>
    </header>
    <OperationalFilters branches={data?.branches ?? []} value={filters} onChange={changeFilters} />
    {error && <Notification kind="error" message={error} />}
    <div aria-busy={loading} aria-label="Indicadores operativos">
      {loading ? <div className="dashboard-loading" role="status"><div className="dashboard-skeleton-cards">{[1, 2, 3, 4].map(key => <div key={key} />)}</div><div className="dashboard-skeleton-chart" /><span>Cargando indicadores…</span></div>
        : error ? <div className="dashboard-error"><h2>No pudimos cargar el dashboard</h2><p>Vuelve a intentarlo para consultar los datos de este período.</p><button onClick={refresh}>Reintentar</button></div>
          : data && <>
            <div className="dashboard-kpis">
              <article className="dashboard-kpi"><span className="dashboard-kpi-icon"><MetricIcon name="chart" /></span><span>Ventas registradas</span><strong>{currency(data.sales.total)}</strong><small>{number(data.sales.count)} ventas · POS y online</small></article>
              <article className="dashboard-kpi"><span className="dashboard-kpi-icon blue"><MetricIcon name="receipt" /></span><span>Ticket promedio</span><strong>{currency(data.sales.average)}</strong><small>Importe promedio por venta</small></article>
              <article className="dashboard-kpi"><span className="dashboard-kpi-icon amber"><MetricIcon name="box" /></span><span>Stock bajo <em>Ahora</em></span><strong>{number(data.inventory.low_count)}</strong><small>Productos por sucursal en o bajo el mínimo</small></article>
              <article className="dashboard-kpi"><span className="dashboard-kpi-icon green"><MetricIcon name="clock" /></span><span>Próximos a vencer <em>Ahora</em></span><strong>{number(data.inventory.expiring_count)}</strong><small>Lotes con existencias · Próximos 30 días</small></article>
            </div>
            <div className="dashboard-main-grid">
              <article className="dashboard-panel"><header><div><h2>Evolución de ventas</h2><p>Importes diarios en pesos chilenos</p></div><span className="dashboard-tag">{number(data.daily.length)} días</span></header><SalesChart rows={data.daily} />
                <footer className="dashboard-sales-summary"><span>Reversas registradas<strong>{currency(data.sales.returns)}</strong></span><span>Balance del período<strong>{currency(data.sales.net)}</strong></span><details><summary>¿Cómo se calcula?</summary><p>Ventas registradas menos anulaciones y devoluciones registradas en este período. Una reversa puede corresponder a una venta anterior. El ticket promedio y los gráficos usan ventas antes de reversas. Los pagos online en revisión requieren conciliación y no descuentan una reversa automáticamente.</p></details></footer>
              </article>
              <article className="dashboard-panel"><header><div><h2>Medios de pago</h2><p>Distribución del importe vendido</p></div></header><PaymentChart rows={data.payments} /></article>
            </div>
            <div className="dashboard-secondary-grid">
              <article className="dashboard-panel"><header><div><h2>Ventas por sucursal</h2><p>Selecciona una barra para filtrar</p></div><MetricIcon name="branch" /></header><Bars rows={data.by_branch.map(branch => ({ ...branch, value: Number(branch.total) }))} money onSelect={branch_id => changeFilters({ ...filters, branch_id })} /></article>
              <article className="dashboard-panel"><header><div><h2>Productos más vendidos</h2><p>Unidades vendidas · Antes de devoluciones</p></div><span className="dashboard-tag">Top 5</span></header><Bars rows={data.top_products.map(product => ({ ...product, value: product.quantity }))} /></article>
            </div>
            <section className="dashboard-panel dashboard-alerts"><header><div><h2>Atención al inventario</h2><p>Situación actual · {displayDate(data.inventory.as_of)} · {branchName}</p></div>{data.inventory.expired_count > 0 && <span className="dashboard-expired">{number(data.inventory.expired_count)} lotes vencidos con existencias</span>}</header>
              <div className="dashboard-alert-tabs" role="group" aria-label="Alertas de inventario"><button type="button" aria-pressed={alertTab === 'stock'} onClick={() => setAlertTab('stock')}>Stock bajo <span>{number(data.inventory.low_count)}</span></button><button type="button" aria-pressed={alertTab === 'expiry'} onClick={() => setAlertTab('expiry')}>Por vencer <span>{number(data.inventory.expiring_count)}</span></button></div>
              <div className="dashboard-table-wrap">{alertTab === 'stock' ? <table><caption className="sr-only">Hasta cinco productos con menor disponibilidad</caption><thead><tr><th>Producto</th><th>Sucursal</th><th>Disponible</th><th>Mínimo</th></tr></thead><tbody>{data.inventory.low_stock.length ? data.inventory.low_stock.map(item => <tr key={item.id}><td>{item.name}</td><td>{item.branch}</td><td><span className={item.available === 0 ? 'dashboard-status danger' : 'dashboard-status'}>{item.available === 0 ? 'Agotado' : `${number(item.available)} un.`}</span></td><td>{number(item.minimum)} un.</td></tr>) : <tr><td colSpan={4} className="dashboard-table-empty">Sin alertas de stock bajo.</td></tr>}</tbody></table>
                : <table><caption className="sr-only">Hasta cinco lotes más próximos a vencer</caption><thead><tr><th>Producto / lote</th><th>Sucursal</th><th>Vencimiento</th><th>Unidades</th></tr></thead><tbody>{data.inventory.expiring.length ? data.inventory.expiring.map(item => <tr key={item.id}><td>{item.name}<small>Lote {item.lot}</small></td><td>{item.branch}</td><td><span className={item.days <= 15 ? 'dashboard-status danger' : 'dashboard-status'}>{item.days} días</span> <small>{displayDate(item.date)}</small></td><td>{number(item.quantity)}</td></tr>) : <tr><td colSpan={4} className="dashboard-table-empty">Sin lotes por vencer en los próximos 30 días.</td></tr>}</tbody></table>}</div>
              <footer className="dashboard-inventory-note">Se muestran hasta 5 alertas prioritarias. El stock y los vencimientos reflejan el estado actual; el período se aplica a ventas y movimientos.</footer>
            </section>
            <details className="dashboard-panel dashboard-movements"><summary>Movimientos de inventario del período <span>{number(data.movements.reduce((sum, item) => sum + item.count, 0))} registros</span></summary><div className="dashboard-table-wrap"><table><thead><tr><th>Movimiento</th><th>Registros</th><th>Cambio físico</th><th>Cambio reservado</th></tr></thead><tbody>{data.movements.length ? data.movements.map(item => <tr key={item.type}><td>{item.type.replaceAll('_', ' ').toLocaleLowerCase('es-CL')}</td><td>{number(item.count)}</td><td>{number(item.physical)}</td><td>{number(item.reserved)}</td></tr>) : <tr><td colSpan={4} className="dashboard-table-empty">No hay movimientos para estos filtros.</td></tr>}</tbody></table></div></details>
          </>}
    </div>
  </section>
}
