import StoreIcon from './StoreIcon'
import Notification from '../../../components/Notification'
import { Link, useLocation } from 'react-router-dom'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { useCart } from '../hooks/useCart'
import logo from '../../../assets/logo-farmacia-quilicura.jpg'
import '../public-header.css'
import '../store-experience.css'

export default function PublicHeader() {
  const { pathname } = useLocation()
  const { customer, loading, closing, error, logout } = useCustomerSession()
  const { draft } = useCart()

  return (
    <header className="public-header">
      <div className="public-header-row">
        <Link className="public-header-brand" to="/tienda"><img src={logo} alt="Farmacia Quilicura" width="718" height="718" /><span>Tienda online</span></Link>
        <nav className="public-header-nav" aria-label="Navegación pública">
          <Link to="/tienda" aria-current={pathname === '/tienda' ? 'page' : undefined}><StoreIcon name="orders" />Catálogo</Link>
          <Link className="public-header-cart" to="/tienda/carrito" aria-current={pathname === '/tienda/carrito' ? 'page' : undefined}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M3 3h2l3 12h10l3-9H6" /><circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" /></svg>Carrito ({draft.items.reduce((sum, item) => sum + item.quantity, 0)})</Link>
          <div className="public-header-customer" aria-live="polite" aria-busy={loading || closing}>
            {loading ? <span>Consultando sesión…</span> : customer ? <>
              <span className="public-header-name">{customer.name}</span>
              <Link to="/tienda/mis-pedidos" aria-current={pathname === '/tienda/mis-pedidos' ? 'page' : undefined}><StoreIcon name="receipt" />Mis pedidos</Link>
              <button type="button" disabled={closing} onClick={() => { void logout() }}>{closing ? 'Cerrando sesión…' : 'Cerrar sesión'}</button>
            </> : <>
              <Link to="/tienda/registro" aria-current={pathname === '/tienda/registro' ? 'page' : undefined}><StoreIcon name="user" />Crear cuenta</Link>
              <Link to="/tienda/iniciar-sesion" aria-current={pathname === '/tienda/iniciar-sesion' ? 'page' : undefined}><StoreIcon name="user" />Iniciar sesión</Link>
            </>}
          </div>
          <Link className="public-header-internal" to="/login">Acceso interno</Link>
        </nav>
      </div>
      {error && <Notification message={error} kind="error" />}
    </header>
  )
}
