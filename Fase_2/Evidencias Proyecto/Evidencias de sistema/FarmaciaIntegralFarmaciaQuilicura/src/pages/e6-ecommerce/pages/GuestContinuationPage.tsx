import { useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../components/PublicHeader'
import GuestForm from '../components/GuestForm'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { useCart } from '../hooks/useCart'
import { useGuest } from '../hooks/useGuest'
import { validateGuest } from '../services/guest.api'
import { ApiError } from '../../../services/http'
import type { GuestValidation } from '../types/guest'
import '../guest.css'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
export default function GuestContinuationPage() {
  const { customer, loading, error: sessionError, refreshCustomer } = useCustomerSession()
  const { draft } = useCart()
  const { guest } = useGuest()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<{ fingerprint: string; value: GuestValidation } | null>(null)
  const fingerprint = JSON.stringify({ items: draft.items, branch: draft.pickup_branch_id })
  const review = result?.fingerprint === fingerprint ? result.value : null
  async function submit() {
    if (!guest.name.trim()) { setError('Ingresa tu nombre.'); return }
    if (!draft.pickup_branch_id) { setError('Selecciona una sucursal activa en el carrito.'); return }
    setBusy(true); setError(''); setResult(null)
    try {
      try {
        if (await refreshCustomer()) return
      } catch (cause) {
        if (!(cause instanceof ApiError && cause.status === 401)) throw cause
      }
      const value = await validateGuest(guest, draft)
      setResult({ fingerprint, value })
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'No pudimos revisar los datos.') }
    finally { setBusy(false) }
  }
  return <main className="guest-page"><PublicHeader /><h1>Revisión como invitado</h1>
    <p className="guest-notice">Esta es una revisión previa. El pedido todavía no ha sido creado; no se reservan unidades ni se realiza ningún pago.</p>
    {loading ? <p role="status">Consultando sesión…</p> : sessionError ? <p role="alert">{sessionError}</p> : customer ? <p>Hay una sesión de cliente activa. Continúa con tu cuenta desde el carrito.</p> : <>
      <p>Solicitamos únicamente nombre y correo. No se creará una cuenta.</p>
      <p>Los datos del invitado se pierden al recargar esta página. El carrito y la sucursal se conservan.</p>
      <GuestForm busy={busy} onSubmit={submit} onEdit={() => { setResult(null); setError('') }} />
      {error && <p role="alert" className="guest-error">{error}</p>}
      {review && (!review.cart.valid ? <div role="alert" className="guest-error"><p>El carrito necesita correcciones. Conservamos tus datos mientras navegas dentro de la tienda.</p>{review.cart.issues.map(issue => <p key={issue}>{issue}</p>)}{review.cart.items.flatMap(line => line.issues.map(issue => <p key={`${line.product_id}:${issue}`}>{line.name ?? 'Producto'}: {issue}</p>))}</div> :
        <section className="guest-review" aria-labelledby="guest-review-title"><h2 id="guest-review-title">Revisión previa</h2>
          <p>Nombre: {review.guest.name}</p><p>Correo: {review.guest.email}</p>
          <p>Sucursal de retiro: {review.cart.pickup_branch?.name}</p>
          <ul>{review.cart.items.map(line => <li key={line.product_id}>{line.name} · {line.quantity} unidades · Subtotal: {money(line.subtotal!)}{line.requires_transfer && <p>Requiere transferencia. No confirma disponibilidad inmediata.</p>}</li>)}</ul>
          <p>Total actual: {money(review.cart.total!)}</p><p>Estos datos se volverán a validar cuando se habilite la creación de pedidos.</p>
        </section>)}
    </>}
    <Link className="guest-back" to="/tienda/carrito">Volver al carrito</Link>
  </main>
}
