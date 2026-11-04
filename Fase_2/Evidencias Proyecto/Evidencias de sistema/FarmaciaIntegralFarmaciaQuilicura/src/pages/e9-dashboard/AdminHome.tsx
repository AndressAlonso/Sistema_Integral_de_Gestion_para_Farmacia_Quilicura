import { Link, Navigate, useOutletContext } from 'react-router-dom'
import type { AuthSession } from '../e1-access-users-branches/auth/login.api'
import { adminNavigation, canAccessAdminPage } from '../../layouts/adminNavigation'

export default function AdminHome() {
  const { user } = useOutletContext<AuthSession>()
  if (canAccessAdminPage('/admin/dashboard', user.permissions, user.roles)) return <Navigate to="/admin/dashboard" replace />
  return <section><h1>Bienvenido, {user.name}</h1><p>Selecciona una sección para comenzar.</p><ul>{adminNavigation.filter(item => item.path !== '/session' && canAccessAdminPage(item.path, user.permissions, user.roles)).map(item => <li key={item.path}><Link to={item.path}>{item.label}</Link></li>)}</ul></section>
}
