import { Link } from 'react-router-dom'

type HistoryState =
  | { state: 'loading' }
  | { state: 'session-required' }
  | { state: 'blocked' }
  | { state: 'empty' }
  | { state: 'error'; message: string }

export default function OrderHistoryState(props: HistoryState) {
  switch (props.state) {
    case 'loading': return <p className="order-history-state" role="status">Consultando sesión de cliente…</p>
    case 'session-required': return <section className="order-history-state"><h1>Acceso requerido</h1><p>Inicia sesión como cliente para acceder a esta página.</p><Link to="/tienda/iniciar-sesion">Iniciar sesión</Link></section>
    case 'blocked': return <p className="order-history-state">El historial estará disponible cuando se habilite la creación de pedidos online</p>
    // Preparado para una consulta real; este estado no se utiliza en la página actual.
    case 'empty': return <p className="order-history-state" role="status">No se encontraron pedidos en la consulta realizada.</p>
    case 'error': return <p className="order-history-state order-history-error" role="alert">{props.message}</p>
  }
}
