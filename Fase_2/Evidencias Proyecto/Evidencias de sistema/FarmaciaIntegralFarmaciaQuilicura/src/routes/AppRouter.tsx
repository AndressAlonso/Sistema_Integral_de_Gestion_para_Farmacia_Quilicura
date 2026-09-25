import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from '../layouts/AdminLayout'
import { adminNavigation } from '../layouts/adminNavigation'
import LoginPage from '../pages/e1-access-users-branches/auth/LoginPage'
import RequireAuth from '../pages/e1-access-users-branches/auth/RequireAuth'
import BranchesPage from '../pages/e1-access-users-branches/branches/BranchesPage'
import UsersPage from '../pages/e1-access-users-branches/users/UsersPage'
import InventoryPage from '../pages/e3-inventory/InventoryPage'

import CatalogPage from '../pages/e2-catalog/CatalogPage'

function getAdminPage(path: string) {
  if (path === '/admin/products') return <CatalogPage />

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
        <Route path="/login" element={<LoginPage />} />

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

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}