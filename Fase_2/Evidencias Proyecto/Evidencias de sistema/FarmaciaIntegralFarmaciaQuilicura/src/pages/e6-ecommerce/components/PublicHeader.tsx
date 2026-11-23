import StoreIcon from './StoreIcon'
import { guestOrderAccess } from '../services/orders.api'
import { useState } from 'react'
import Notification from '../../../components/Notification'
import { Link, useLocation } from 'react-router-dom'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { useCart } from '../hooks/useCart'
import logo from '../../../assets/logo-farmacia-quilicura.jpg'
import '../public-header.css'
import '../store-experience.css'

export default function PublicHeader({ onCatalogHome }: { onCatalogHome?: () => void }) {
  const { pathname } = useLocation()
  const { customer, loading, closing, error, logout } = useCustomerSession()
  const { draft } = useCart()
  const [menuPath, setMenuPath] = useState<string | null>(null)
  const menuOpen = menuPath === pathname
  const guestOrder = customer ? null : guestOrderAccess()

  return (
    <header className="public-header">
      <div className="public-header-row">
        <Link className="public-header-brand" to="/tienda" onClick={onCatalogHome}><img src={logo} alt="Farmacia Quilicura" width="718" height="718" /></Link>
        <button className="public-menu-toggle" type="button" aria-label="Menú de la tienda" aria-expanded={menuOpen} aria-controls="store-navigation" onClick={() => setMenuPath(menuOpen ? null : pathname)}>☰ <span>Menú</span></button>
        <nav id="store-navigation" className={`public-header-nav${menuOpen ? ' is-open' : ''}`} aria-label="Navegación pública" onClick={event => { if ((event.target as HTMLElement).closest('a')) setMenuPath(null) }}>
          <Link to="/tienda" onClick={onCatalogHome} aria-current={pathname === '/tienda' ? 'page' : undefined}><StoreIcon name="orders" />Catálogo</Link>
          <Link className="public-header-cart" to="/tienda/carrito" aria-current={pathname === '/tienda/carrito' ? 'page' : undefined}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M3 3h2l3 12h10l3-9H6" /><circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" /></svg>Carrito ({draft.items.reduce((sum, item) => sum + item.quantity, 0)})</Link>
          <div className="public-header-customer" aria-live="polite" aria-busy={loading || closing}>
            {loading ? <span>Consultando sesión…</span> : customer ? <>
              <span className="public-header-name">{customer.name}</span>
              <Link to="/tienda/mis-pedidos" aria-current={pathname === '/tienda/mis-pedidos' ? 'page' : undefined}><StoreIcon name="receipt" />Mis pedidos</Link>
              <button className="public-header-logout" type="button" disabled={closing} aria-label={closing ? 'Cerrando sesión…' : 'Cerrar sesión'} title={closing ? 'Cerrando sesión…' : 'Cerrar sesión'} aria-busy={closing} onClick={() => { void logout() }}><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 4H4v16h5M14 8l4 4-4 4M8 12h10" /></svg></button>
            </> : <>
              {guestOrder && <Link to={`/tienda/confirmar?order_id=${guestOrder.request_id}`}><StoreIcon name="receipt" />Mi pedido</Link>}
              <Link to="/tienda/registro" aria-current={pathname === '/tienda/registro' ? 'page' : undefined}><StoreIcon name="user" />Crear cuenta</Link>
              <Link to="/tienda/iniciar-sesion" aria-current={pathname === '/tienda/iniciar-sesion' ? 'page' : undefined}><StoreIcon name="user" />Iniciar sesión</Link>
            </>}
          </div>
          <Link className="public-header-internal" to="/login" aria-label="Acceso del personal" title="Acceso del personal"><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="4" y="5" width="16" height="16" rx="3" /><path d="M9 5V3h6v2M8 17c0-3 8-3 8 0" /><circle cx="12" cy="10" r="2" /></svg></Link>
        </nav>
      </div>
      {error && <Notification message={error} kind="error" />}
    </header>
  )
}

