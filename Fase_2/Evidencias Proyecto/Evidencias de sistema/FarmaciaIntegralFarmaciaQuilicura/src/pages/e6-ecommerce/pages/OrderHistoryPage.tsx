import { useCustomerSession } from '../hooks/useCustomerSession'
import OrderHistoryState from '../components/OrderHistoryState'
import PublicHeader from '../components/PublicHeader'
import '../order-history.css'

/** E6-H5 Bloqueada por E7-H1. No consulta pedidos ni muestra listas vacías ficticias. */
export default function OrderHistoryPage() {
  const { customer, loading, error } = useCustomerSession()
  return <main className="order-history-page">
    <PublicHeader />
    {loading ? <OrderHistoryState state="loading" />
      : error ? <OrderHistoryState state="error" message={error} />
        : customer ? <OrderHistoryState state="blocked" />
          : <OrderHistoryState state="session-required" />}
  </main>
}
