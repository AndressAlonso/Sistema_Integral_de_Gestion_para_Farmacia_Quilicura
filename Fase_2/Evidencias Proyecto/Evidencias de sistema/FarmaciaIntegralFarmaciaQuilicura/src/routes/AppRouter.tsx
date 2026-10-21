import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import OrdersPage from '../pages/e7-orders/OrdersPage'
import AdminLayout from '../layouts/AdminLayout'
import { adminNavigation } from '../layouts/adminNavigation'
import LoginPage from '../pages/e1-access-users-branches/auth/LoginPage'
import RequireAuth from '../pages/e1-access-users-branches/auth/RequireAuth'
import BranchesPage from '../pages/e1-access-users-branches/branches/BranchesPage'
import UsersPage from '../pages/e1-access-users-branches/users/UsersPage'
import CatalogPage from '../pages/e2-catalog/CatalogPage'
import PromotionsPage from '../pages/e2-catalog/promotions/PromotionsPage'
import InventoryPage from '../pages/e3-inventory/InventoryPage'
import TransfersPage from '../pages/e4-transfers/TransfersPage'
import PosPage from '../pages/e5-pos/PosPage'
import CashPage from '../pages/e5-pos/CashPage'
import OnlineCatalogPage from '../pages/e6-ecommerce/pages/OnlineCatalogPage'
import ProductDetailPage from '../pages/e6-ecommerce/pages/ProductDetailPage'
import CustomerRegisterPage from '../pages/e6-ecommerce/pages/CustomerRegisterPage'
import CustomerLoginPage from '../pages/e6-ecommerce/pages/CustomerLoginPage'
import EcommerceLayout from '../pages/e6-ecommerce/layouts/EcommerceLayout'
import CartPage from '../pages/e6-ecommerce/pages/CartPage'
import OrderConfirmationPage from '../pages/e6-ecommerce/pages/OrderConfirmationPage'
import OrderHistoryPage from '../pages/e6-ecommerce/pages/OrderHistoryPage'

function getAdminPage(path: string) {
  if (path === '/admin/orders') return <OrdersPage />
  if (path === '/admin/promotions') return <PromotionsPage />
  if (path === '/admin/pos') return <PosPage />
  if (path === '/admin/cash') return <CashPage />
  if (path === '/admin/transfers') return <TransfersPage />
  if (path === '/admin/inventory') {
    return <InventoryPage />
  }

  if (path === '/admin/products') {
    return <CatalogPage />
  }

  if (path === '/admin/users') {
    return <UsersPage />
  }

  if (path === '/admin/branches') {
    return <BranchesPage />
  }

  return null
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={<Navigate to="/tienda" replace />}
        />
        <Route element={<EcommerceLayout />}>
        <Route path="/tienda" element={<OnlineCatalogPage />} />
        <Route path="/tienda/confirmar" element={<OrderConfirmationPage />} />
        <Route path="/tienda/productos/:productId" element={<ProductDetailPage />} />
        <Route path="/tienda/registro" element={<CustomerRegisterPage />} />
        <Route path="/tienda/iniciar-sesion" element={<CustomerLoginPage />} />
        <Route path="/tienda/carrito" element={<CartPage />} />
        <Route path="/tienda/invitado" element={<Navigate to="/tienda/confirmar" replace />} />
        <Route path="/tienda/mis-pedidos" element={<OrderHistoryPage />} />
        </Route>
        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route element={<RequireAuth />}>
          <Route element={<AdminLayout />}>
            {adminNavigation.map((item) => (
              <Route
                key={item.path}
                path={item.path}
                element={getAdminPage(item.path)}
              />
            ))}
          </Route>

          <Route
            path="/prototypes/inventory"
            element={<InventoryPage />}
          />
        </Route>

        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}
