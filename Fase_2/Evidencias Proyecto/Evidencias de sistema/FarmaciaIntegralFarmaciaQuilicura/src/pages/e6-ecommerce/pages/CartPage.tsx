import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../components/PublicHeader'
import CartItem from '../components/CartItem'
import CartContinuation from '../components/CartContinuation'
import { useCart } from '../hooks/useCart'
import { listBranches } from '../services/catalog.api'
import type { PublicBranch } from '../types/catalog'
import '../cart.css'

export default function CartPage() {
  const { draft, validation, loading, error, selectBranch, refresh } = useCart()
  const [branches, setBranches] = useState<PublicBranch[]>([])
  const [branchError, setBranchError] = useState('')
  useEffect(() => {
    let active = true
    void listBranches().then(value => { if (active) setBranches(value) }).catch(() => { if (active) setBranchError('No pudimos consultar las sucursales. Recarga la página para intentar nuevamente.') })
    return () => { active = false }
  }, [])
  const missingBranch = draft.pickup_branch_id && !branches.some(b => b.id === draft.pickup_branch_id)
  return <main className="cart-page"><PublicHeader /><h1>Tu carrito</h1><Link to="/tienda">Seguir consultando el catálogo</Link>
    <p className="cart-notice">La validación no reserva unidades. Los precios y la disponibilidad pueden cambiar. Todavía no se crean pedidos.</p>
    <label className="cart-branch" htmlFor="cart-branch">Sucursal de retiro<select id="cart-branch" value={draft.pickup_branch_id ?? ''} onChange={e => selectBranch(e.target.value)}>
      <option value="">Selecciona una sucursal</option>
      {missingBranch && <option value={draft.pickup_branch_id ?? ''} disabled>Sucursal guardada no disponible: elige otra</option>}
      {branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
    </select></label>
    {branchError && <p role="alert" className="cart-error">{branchError}</p>}
    {error && <p role="alert" className="cart-error">{error}</p>}
    <div aria-live="polite">{loading && <p>Validando precios y disponibilidad…</p>}{validation?.issues.map(issue => <p key={issue}>{issue}</p>)}</div>
    <div className="cart-layout">
    <section aria-label="Productos del carrito">
    {!draft.items.length ? <p className="cart-empty">El carrito está vacío.</p> : <ul className="cart-list">{draft.items.map(item => {
      const line = validation?.items.find(i => i.product_id === item.product_id) ?? { ...item, name: 'Producto pendiente de validar', unit_price: null, subtotal: null, local_available: null, global_available: 0, requires_transfer: false, valid: false, issues: [] }
      return <CartItem key={item.product_id} line={line} />
    })}</ul>}
    </section>
    <section className="cart-summary" aria-label="Resumen del carrito">
    <p className="cart-total">Total: {validation?.total != null ? new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(validation.total)) : 'Pendiente de validación'}</p>
    <button className="cart-refresh" type="button" disabled={loading} onClick={refresh}>Validar nuevamente</button>
    <CartContinuation />
    </section>
    </div>
  </main>
}
