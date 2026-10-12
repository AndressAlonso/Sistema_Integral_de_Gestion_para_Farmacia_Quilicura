import { Link, useLocation } from 'react-router-dom'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { useCart } from '../hooks/useCart'
import logo from '../../../assets/logo-farmacia-quilicura.jpg'
import '../public-header.css'

export default function PublicHeader() {
  const { pathname } = useLocation()
  const { customer, loading, closing, error, logout } = useCustomerSession()
  const { draft } = useCart()

  return (
    <header className="public-header">
      <div className="public-header-row">
        <Link className="public-header-brand" to="/tienda"><img src={logo} alt="Farmacia Quilicura" width="718" height="718" /><span>Tienda online</span></Link>
        <nav className="public-header-nav" aria-label="Navegación pública">
          <Link to="/tienda" aria-current={pathname === '/tienda' ? 'page' : undefined}>Catálogo</Link>
          <Link to="/tienda/carrito" aria-current={pathname === '/tienda/carrito' ? 'page' : undefined}>Carrito ({draft.items.reduce((sum, item) => sum + item.quantity, 0)})</Link>
          <div className="public-header-customer" aria-live="polite" aria-busy={loading || closing}>
            {loading ? <span>Consultando sesión…</span> : customer ? <>
              <span className="public-header-name">{customer.name}</span>
              <Link to="/tienda/mis-pedidos" aria-current={pathname === '/tienda/mis-pedidos' ? 'page' : undefined}>Mis pedidos</Link>
              <button type="button" disabled={closing} onClick={() => { void logout() }}>{closing ? 'Cerrando sesión…' : 'Cerrar sesión'}</button>
            </> : <>
              <Link to="/tienda/registro" aria-current={pathname === '/tienda/registro' ? 'page' : undefined}>Crear cuenta</Link>
              <Link to="/tienda/iniciar-sesion" aria-current={pathname === '/tienda/iniciar-sesion' ? 'page' : undefined}>Iniciar sesión</Link>
            </>}
          </div>
          <Link className="public-header-internal" to="/login">Acceso interno</Link>
        </nav>
      </div>
      {error && <p className="public-header-error" role="alert">{error}</p>}
    </header>
  )
}
