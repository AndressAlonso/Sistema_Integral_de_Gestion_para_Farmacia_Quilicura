import Notification from '../../../components/Notification'
import { Link } from 'react-router-dom'
import { useCustomerSession } from '../hooks/useCustomerSession'
import { useCart } from '../hooks/useCart'
import '../guest.css'

export default function CartContinuation() {
  const { customer, loading, error } = useCustomerSession()
  const { validation, loading: cartLoading } = useCart()
  if (loading) return <p role="status">Consultando cómo continuar…</p>
  if (error) return <Notification message={error} kind="error" />
  if (customer) return <section className="guest-continuation"><h2>Cuenta de cliente</h2><p>Confirma los productos y reserva las unidades con tu cuenta.</p>{!cartLoading && validation?.valid && <Link className="guest-link" to="/tienda/confirmar">Revisar y confirmar pedido</Link>}</section>
  return <section className="guest-continuation"><h2>Continuar sin cuenta</h2>
    <p>Solo necesitaremos tu nombre y correo para crear tu pedido sin cuenta.</p>
    {!cartLoading && validation?.valid ? <Link className="guest-link" to="/tienda/confirmar">Continuar como invitado</Link> : <p>Elige la sucursal y revisa tus productos para continuar.</p>}
    <p>También puedes <Link to="/tienda/iniciar-sesion">iniciar sesión como cliente</Link>.</p>
  </section>
}
