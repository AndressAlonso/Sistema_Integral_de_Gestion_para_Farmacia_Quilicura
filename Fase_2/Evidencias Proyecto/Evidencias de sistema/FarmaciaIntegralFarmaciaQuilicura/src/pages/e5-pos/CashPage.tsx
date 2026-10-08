import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import type { AuthSession } from '../e1-access-users-branches/auth/login.api'
import { currency, errorMessage, paymentNames, posApi, type Cash, type Summary } from './pos.api'
import './pos.css'

export default function CashPage() {
  const { user } = useOutletContext<AuthSession>()
  const [cash, setCash] = useState<Cash | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [initial, setInitial] = useState('0')
  const [counted, setCounted] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [closed, setClosed] = useState(false)
  const requestId = useRef(crypto.randomUUID())
  const locked = useRef(false)
  const dialog = useRef<HTMLDialogElement>(null)

  async function load() {
    const current = await posApi.cash(); setCash(current)
    setSummary(current ? await posApi.summary(current.id) : null)
  }
  useEffect(() => {
    let active = true
    async function init() {
      try {
        const current = await posApi.cash()
        const result = current ? await posApi.summary(current.id) : null
        if (active) { setCash(current); setSummary(result) }
      } catch (cause) { if (active) setError(errorMessage(cause)) }
      finally { if (active) setLoading(false) }
    }
    void init()
    return () => { active = false }
  }, [])
  async function open(event: FormEvent) {
    event.preventDefault()
    if (locked.current) return
    locked.current = true; setBusy(true); setError('')
    try { await posApi.open(requestId.current, initial); requestId.current = crypto.randomUUID(); setClosed(false); await load() }
    catch (cause) { setError(errorMessage(cause)) }
    finally { locked.current = false; setBusy(false) }
  }
  async function review() {
    if (!cash || locked.current) return
    locked.current = true; setBusy(true); setError('')
    try { setSummary(await posApi.summary(cash.id)); dialog.current?.showModal() }
    catch (cause) { setError(errorMessage(cause)) }
    finally { locked.current = false; setBusy(false) }
  }
  async function close(event: FormEvent) {
    event.preventDefault()
    if (!cash || !summary || locked.current) return
    locked.current = true; setBusy(true); setError('')
    try {
      const result = await posApi.close(cash.id, counted, summary.version)
      setCash(result); setSummary(result.summary); setClosed(true); dialog.current?.close()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { locked.current = false; setBusy(false) }
  }
  return <section className="pos-page"><header className="pos-heading"><div><p className="pos-eyebrow">CONTROL DEL TURNO</p><h1>Mi caja</h1><p>{user.branch_name} · {user.name}</p></div><Link className="pos-secondary" to="/admin/pos">Ir al punto de venta →</Link></header>
    {error && <p className="pos-error" role="alert">{error}</p>}{loading ? <p role="status">Consultando caja…</p> : <>
      {closed && <p className="pos-notice" role="status">Caja cerrada. El resumen quedó registrado.</p>}
      {!cash || closed ? <section className="pos-panel"><h2>Abrir un nuevo turno</h2><p>Registra el efectivo inicial. Puedes comenzar con $0.</p><form className="pos-inline-form" onSubmit={event => void open(event)}><label>Monto inicial<input type="number" min="0" max="999999999999.99" step="0.01" required value={initial} disabled={busy} onChange={event => { setInitial(event.target.value); requestId.current = crypto.randomUUID() }} /></label><button disabled={busy}>{busy ? 'Abriendo…' : 'Abrir caja'}</button></form></section> : <section className="pos-panel pos-section-title"><div><h2>Caja abierta</h2><p>Desde {new Date(cash.opened_at).toLocaleString('es-CL')} · Inicial: {currency(cash.initial_amount)}</p></div><button disabled={busy} onClick={() => void review()}>Revisar y cerrar caja</button></section>}
      {summary && <section className="pos-panel"><h2>{closed ? 'Resumen de cierre' : 'Indicadores del turno'}</h2><div className="pos-metrics"><div><span>Ventas</span><strong>{summary.sales_count}</strong></div><div><span>Total vendido</span><strong>{currency(summary.total)}</strong></div><div><span>Ticket promedio</span><strong>{currency(summary.average_ticket)}</strong></div><div><span>Efectivo esperado</span><strong>{currency(summary.expected_cash)}</strong></div></div><table><thead><tr><th>Medio de pago</th><th>Total</th></tr></thead><tbody>{Object.entries(summary.payments).map(([key, value]) => <tr key={key}><td>{paymentNames[key as keyof typeof paymentNames]}</td><td>{currency(value)}</td></tr>)}</tbody></table>{summary.difference !== undefined && <p>Diferencia registrada: <strong>{currency(summary.difference)}</strong></p>}</section>}
      {summary && <section className="pos-panel"><h2>Reembolsos registrados en esta caja</h2><table><thead><tr><th>Medio</th><th>Reembolsado</th></tr></thead><tbody>{Object.entries(summary.refunds).map(([key, value]) => <tr key={key}><td>{paymentNames[key as keyof typeof paymentNames]}</td><td>{currency(value)}</td></tr>)}</tbody></table><p className="pos-muted">El efectivo esperado descuenta los reembolsos en efectivo, incluso cuando la venta pertenece a un turno anterior.</p></section>}
    </>}
    <dialog className="pos-dialog" ref={dialog} onCancel={event => { if (busy) event.preventDefault() }}><div className="pos-dialog-body"><div className="pos-section-title"><h2>Cierre de caja</h2><button disabled={busy} onClick={() => dialog.current?.close()}>Volver</button></div><p>Cuenta el efectivo físico antes de confirmar. El cierre conserva los indicadores de este turno.</p>{summary && <form className="pos-payment" onSubmit={event => void close(event)}><p>Efectivo esperado: <strong>{currency(summary.expected_cash)}</strong></p><label>Efectivo contado<input required type="number" min="0" max="999999999999.99" step="0.01" value={counted} onChange={event => setCounted(event.target.value)} disabled={busy} /></label>{counted !== '' && <p>Diferencia: {currency(Number(counted) - Number(summary.expected_cash))}</p>}<button disabled={busy}>{busy ? 'Cerrando…' : 'Confirmar cierre'}</button></form>}{error && <p role="alert" className="pos-error">{error}</p>}</div></dialog>
  </section>
}
