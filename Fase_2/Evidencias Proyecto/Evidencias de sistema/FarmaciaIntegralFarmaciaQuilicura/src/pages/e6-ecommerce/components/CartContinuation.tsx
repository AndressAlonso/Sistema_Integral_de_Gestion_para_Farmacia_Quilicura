import { Link } from 'react-router-dom'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { useCart } from '../hooks/useCart'
import '../guest.css'

export default function CartContinuation() {
  const { customer, loading, error } = useCustomerSession()
  const { validation, loading: cartLoading } = useCart()
  if (loading) return <p role="status">Consultando cómo continuar…</p>
  if (error) return <p role="alert">{error}</p>
  if (customer) return <section className="guest-continuation"><h2>Cuenta de cliente</h2><p>Continuarás con tu cuenta. La creación de pedidos todavía no está habilitada.</p></section>
  return <section className="guest-continuation"><h2>Continuar sin cuenta</h2>
    <p>Solo necesitaremos tu nombre y correo para una revisión previa.</p>
    {!cartLoading && validation?.valid ? <Link className="guest-link" to="/tienda/invitado">Continuar como invitado</Link> : <p>Valida el carrito y selecciona una sucursal activa para continuar.</p>}
    <p>También puedes <Link to="/tienda/iniciar-sesion">iniciar sesión como cliente</Link>.</p>
  </section>
}
