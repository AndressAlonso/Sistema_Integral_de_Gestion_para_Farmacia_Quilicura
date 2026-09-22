import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import InventoryPage from '../pages/e3-inventory/InventoryPage'
import LoginPage from '../pages/e1-access-users-branches/auth/LoginPage'
import BranchesPage from '../pages/e1-access-users-branches/branches/BranchesPage'
import RequireAuth from '../pages/e1-access-users-branches/auth/RequireAuth'
import AdminLayout from '../layouts/AdminLayout'
import { adminNavigation } from '../layouts/adminNavigation'
import UsersPage from '../pages/e1-access-users-branches/users/UsersPage'

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<AdminLayout />}>
            {adminNavigation.map(item => <Route key={item.path} path={item.path} element={item.path === '/admin/users' ? <UsersPage /> : null} />)}
          </Route>
          <Route path="/admin/branches" element={<BranchesPage />} />
          <Route path="/prototypes/inventory" element={<InventoryPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
