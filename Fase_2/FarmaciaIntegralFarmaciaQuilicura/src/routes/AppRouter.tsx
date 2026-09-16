import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import InventoryPage from '../pages/e3-inventory/InventoryPage'
import LoginPage from '../pages/e1-access-users-branches/auth/LoginPage'
import BranchesPage from '../pages/e1-access-users-branches/branches/BranchesPage'
import RequireAuth from '../pages/e1-access-users-branches/auth/RequireAuth'
import SessionPage from '../pages/e1-access-users-branches/auth/SessionPage'

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/session" element={<SessionPage />} />
          <Route path="/admin/branches" element={<BranchesPage />} />
          <Route path="/admin/inventory" element={<InventoryPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
