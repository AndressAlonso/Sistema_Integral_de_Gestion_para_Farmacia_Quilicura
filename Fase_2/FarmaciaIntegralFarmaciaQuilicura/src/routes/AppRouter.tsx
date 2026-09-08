import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import InventoryPage from '../pages/e3-inventory/InventoryPage'
import LoginPage from '../pages/e1-access-users-branches/auth/LoginPage'
import BranchesPage from '../pages/e1-access-users-branches/branches/BranchesPage'

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin/branches" element={<BranchesPage />} />
        <Route path="/admin/inventory" element={<InventoryPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
