import { useState } from 'react'
import { NavLink, Outlet, useLocation, useOutletContext } from 'react-router-dom'
import logo from '../assets/logo-farmacia-quilicura.jpg'
import LogoutButton from '../pages/e1-access-users-branches/auth/LogoutButton'
import type { AuthSession } from '../pages/e1-access-users-branches/auth/login.api'
import { adminNavigation } from './adminNavigation'
import './admin-layout.css'

export default function AdminLayout() {
  const session = useOutletContext<AuthSession>()
  const { pathname } = useLocation()
  const [expanded, setExpanded] = useState(false)
  const current = adminNavigation.find(item => item.path === pathname)

  return (
    <div className={`admin-shell${expanded ? ' admin-menu-open' : ''}`}>
      <a className="admin-skip" href="#admin-content">Saltar al contenido</a>
      <aside className="admin-sidebar" id="admin-sidebar" aria-label="Menú principal">
        <NavLink className="admin-brand" to="/session" onClick={() => setExpanded(false)} aria-label="Farmacia Quilicura, resumen">
          <img src={logo} alt="Farmacia Quilicura — Cuidando tu salud" />
        </NavLink>
        <nav aria-label="Secciones del sistema">
          {adminNavigation.filter(item => item.path !== '/admin/users' || session.user.permissions.includes('usuarios.gestionar')).map(item => (
            <NavLink key={item.path} to={item.path} end onClick={() => setExpanded(false)} className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={item.icon} /></svg>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-brand-note"><span aria-hidden="true">🌿</span><p>Cuidando<br />la salud de nuestra<br />comunidad</p><span className="admin-brand-line" /></div>
      </aside>
      <div className="admin-workspace">
        <header className="admin-topbar">
          <button className="admin-menu-toggle" type="button" aria-label={expanded ? 'Cerrar menú' : 'Abrir menú'} aria-expanded={expanded} aria-controls="admin-sidebar" onClick={() => setExpanded(value => !value)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <span className="admin-section-name">{current?.label}</span>
          <div className="admin-account"><span className="admin-avatar" aria-hidden="true">{session.user.email.slice(0, 2).toUpperCase()}</span><span className="admin-account-email">{session.user.email}</span></div>
          <LogoutButton />
        </header>
        <main id="admin-content" className="admin-content" tabIndex={-1} aria-label={current?.label ?? 'Contenido'}>
          <Outlet context={session} />
        </main>
      </div>
    </div>
  )
}
