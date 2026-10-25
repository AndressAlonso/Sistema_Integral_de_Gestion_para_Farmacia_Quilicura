import StoreIcon from '../components/StoreIcon'
import Notification from '../../../components/Notification'
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
  return <main className="cart-page"><PublicHeader /><header className="store-page-heading"><div><p className="store-page-eyebrow">TU SELECCIÓN</p><h1>Tu carrito</h1><p>Revisa tus productos y elige dónde retirar tu pedido.</p></div><Link className="store-back-link" to="/tienda">← Seguir comprando</Link></header>
    <p className="cart-notice">Tus productos se reservan al confirmar el pedido. Antes de continuar, verificaremos los precios y las unidades disponibles.</p>

    {error && <Notification message={error} kind="error" />}
    
    <div className="cart-layout">
    <section aria-label="Productos del carrito">
    {!draft.items.length ? <div className="cart-empty"><h2>Tu carrito está esperando</h2><p>Explora la tienda y agrega los productos que necesitas.</p><Link className="store-back-link" to="/tienda">Explorar productos →</Link></div> : <ul className="cart-list">{draft.items.map(item => {
      const line = validation?.items.find(i => i.product_id === item.product_id) ?? { ...item, name: 'Producto pendiente de validar', unit_price: null, subtotal: null, local_available: null, global_available: 0, requires_transfer: false, valid: false, issues: [] }
      return <CartItem key={item.product_id} line={line} />
    })}</ul>}
    </section>
    <section className="cart-summary" aria-label="Resumen del carrito">
    <h2 className="store-label-icon"><StoreIcon name="receipt" />Resumen de tu pedido</h2>
    <fieldset className="cart-pickup"><legend><span className="store-label-icon"><StoreIcon name="location" />¿Dónde quieres retirar?</span></legend>
      {branches.length <= 4 ? <div className="cart-pickup-options">{branches.map(branch => <label key={branch.id} className={draft.pickup_branch_id === branch.id ? 'is-selected' : ''}><input type="radio" name="pickup-branch" value={branch.id} checked={draft.pickup_branch_id === branch.id} onChange={() => selectBranch(branch.id)} /><span><strong>{branch.name}</strong><small>{branch.address}</small></span></label>)}</div> : <select aria-label="Sucursal de retiro" value={draft.pickup_branch_id ?? ''} onChange={event => selectBranch(event.target.value)}><option value="">Selecciona una sucursal</option>{branches.map(branch => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select>}
      {missingBranch && <p className="cart-error">La sucursal guardada ya no está disponible. Elige otra.</p>}
      {branchError && <p role="alert" className="cart-error">{branchError}</p>}
    </fieldset>
    <p className="cart-total">Total: {validation?.total != null ? new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(validation.total)) : loading ? 'Actualizando…' : !draft.pickup_branch_id ? 'Elige una sucursal' : 'Revisa tus productos'}</p>
    <div className="cart-check-status" aria-live="polite">{loading ? <p>Actualizando tu pedido…</p> : validation?.valid ? <p>✓ Precios y disponibilidad comprobados</p> : validation?.issues.map(issue => <p key={issue}>{issue}</p>)}</div>{error && <button className="cart-refresh" type="button" disabled={loading} onClick={refresh}>Reintentar conexión</button>}
    <CartContinuation />
    </section>
    </div>
  </main>
}
