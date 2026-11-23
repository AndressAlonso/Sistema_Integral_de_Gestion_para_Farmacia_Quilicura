import { useEffect, useId, useRef, useState } from 'react'
import type { DashboardData } from './dashboard.api'
import { currency, number } from './dashboard.api'
import { displayDate } from './filters'

const palette = ['#7b358e', '#70a946', '#448aaf', '#d89a37', '#9382c3']
const paymentNames: Record<string, string> = {
  EFECTIVO: 'Efectivo', DEBITO: 'Débito', CREDITO: 'Crédito',
  TRANSFERENCIA: 'Transferencia', MERCADOPAGO: 'Mercado Pago',
}
export function EmptyChart({ text = 'No hay ventas en este período.' }: { text?: string }) {
  return <div className="dashboard-empty"><span aria-hidden="true">—</span><p>{text}</p></div>
}

export function SalesChart({ rows }: { rows: DashboardData['daily'] }) {
  const gradient = useId()
  const container = useRef<HTMLDivElement>(null)
  const [chartWidth, setChartWidth] = useState(640)
  const [active, setActive] = useState<number | null>(null)
  useEffect(() => {
    if (!container.current || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(entries => {
      setChartWidth(Math.max(280, Math.min(640, entries[0].contentRect.width)))
    })
    observer.observe(container.current)
    return () => observer.disconnect()
  }, [rows])
  if (!rows.some(row => row.count)) return <EmptyChart />
  const width = chartWidth, height = 210, left = 48, right = 16, top = 16, bottom = 30
  const maximum = Math.max(...rows.map(row => Number(row.total)), 1) * 1.1
  const x = (index: number) => left + (rows.length === 1 ? .5 : index / (rows.length - 1)) * (width - left - right)
  const y = (total: string | number) => height - bottom - Number(total) / maximum * (height - top - bottom)
  const line = rows.map((row, index) => `${index ? 'L' : 'M'} ${x(index)} ${y(row.total)}`).join(' ')
  const selected = active === null ? null : rows[active]
  const shortMoney = (value: number) => new Intl.NumberFormat('es-CL', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
  return <div className="dashboard-line" ref={container}>
    <div className="dashboard-chart-reading" aria-live="polite">
      {selected ? <><span>{displayDate(selected.date)}</span><strong>{currency(selected.total)}</strong><span>{number(selected.count)} ventas</span></> : <span>Pasa por la curva o selecciona un día para ver el detalle.</span>}
    </div>
    <svg viewBox={`0 0 ${width} ${height}`} role="group" aria-label="Ventas registradas por día">
      <defs><linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#8d4ba0" stopOpacity=".18" /><stop offset="100%" stopColor="#8d4ba0" stopOpacity=".01" /></linearGradient></defs>
      {[0, .5, 1].map(tick => <g key={tick}><line x1={left} x2={width - right} y1={y(maximum * tick)} y2={y(maximum * tick)} stroke="#edf0f5" strokeDasharray="4 4" /><text x={left - 8} y={y(maximum * tick) + 4} textAnchor="end">{shortMoney(maximum * tick)}</text></g>)}
      <path d={`${line} L ${x(rows.length - 1)} ${height - bottom} L ${x(0)} ${height - bottom} Z`} fill={`url(#${gradient})`} />
      <path d={line} fill="none" stroke="#7b358e" strokeWidth="2.7" strokeLinejoin="round" strokeLinecap="round" />
      {rows.map((row, index) => <g key={row.date}>
        {(index === 0 || index === rows.length - 1 || (rows.length > 3 && index === Math.floor(rows.length / 2))) && <text x={x(index)} y={height - 7} textAnchor={index === 0 ? 'start' : index === rows.length - 1 ? 'end' : 'middle'}>{displayDate(row.date)}</text>}
        {active === index && <line x1={x(index)} x2={x(index)} y1={top} y2={height - bottom} stroke="#bca0c8" strokeDasharray="4 4" />}
        <circle cx={x(index)} cy={y(row.total)} r={active === index || rows.length === 1 ? 4 : 0} fill="#7b358e" />
        <circle cx={x(index)} cy={y(row.total)} r="10" fill="transparent" tabIndex={index === (active ?? 0) ? 0 : -1} role="button"
          aria-label={`${displayDate(row.date)}: ${currency(row.total)}, ${row.count} ventas`}
          onMouseEnter={() => setActive(index)} onFocus={() => setActive(index)} onClick={() => setActive(index)}
          onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setActive(index) }
            if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
              event.preventDefault()
              const next = Math.max(0, Math.min(rows.length - 1, index + (event.key === 'ArrowRight' ? 1 : -1)))
              const targets = event.currentTarget.closest('svg')?.querySelectorAll<SVGCircleElement>('[role=button]')
              targets?.[next]?.focus()
            }
          }}><title>{displayDate(row.date)} · {currency(row.total)}</title></circle>
      </g>)}
    </svg>
  </div>
}

export function PaymentChart({ rows }: { rows: DashboardData['payments'] }) {
  const [active, setActive] = useState<string | null>(null)
  const total = rows.reduce((sum, row) => sum + Number(row.total), 0)
  if (!total) return <EmptyChart text="Sin importes para distribuir." />
  const segments = rows.map((row, index) => {
    const start = rows.slice(0, index).reduce((sum, item) => sum + Number(item.total), 0) / total * 100
    const end = start + Number(row.total) / total * 100
    return `${palette[index % palette.length]} ${start}% ${end}%`
  })
  const selected = rows.find(row => row.method === active)
  return <div className="dashboard-payment">
    <div className="dashboard-donut" role="img" aria-label={`Distribución de ${currency(total)} entre ${rows.length} medios de pago`} style={{ background: `conic-gradient(${segments.join(',')})` }}>
      <div><strong>{selected ? `${Math.round(Number(selected.total) / total * 100)}%` : number(rows.reduce((sum, row) => sum + row.count, 0))}</strong><span>{selected ? paymentNames[selected.method] ?? selected.method : 'ventas'}</span></div>
    </div>
    <ul className="dashboard-payment-legend">{rows.map((row, index) => <li key={row.method}><button type="button" aria-pressed={active === row.method} onClick={() => setActive(active === row.method ? null : row.method)} onMouseEnter={() => setActive(row.method)} onFocus={() => setActive(row.method)}>
      <i style={{ background: palette[index % palette.length] }} /><span>{paymentNames[row.method] ?? row.method}<small>{number(row.count)} ventas · {(Number(row.total) / total * 100).toLocaleString('es-CL', { maximumFractionDigits: 1 })}%</small></span><strong>{currency(row.total)}</strong>
    </button></li>)}</ul>
  </div>
}

export function Bars({ rows, money = false, onSelect }: { rows: { id: string; name: string; value: number }[]; money?: boolean; onSelect?: (id: string) => void }) {
  const maximum = Math.max(...rows.map(row => row.value), 1)
  if (!rows.length) return <EmptyChart />
  return <ul className="dashboard-bars">{rows.map((row, index) => {
    const content = <><span className="dashboard-bar-label"><span>{row.name}</span><strong>{money ? currency(row.value) : `${number(row.value)} un.`}</strong></span><span className="dashboard-bar-track"><span style={{ width: `${row.value / maximum * 100}%`, background: palette[index % palette.length] }} /></span></>
    return <li key={row.id}>{onSelect ? <button type="button" onClick={() => onSelect(row.id)} aria-label={`Filtrar por ${row.name}`}>{content}</button> : <div>{content}</div>}</li>
  })}</ul>
}
