import { useState, type CSSProperties } from 'react'
import { Navigate, NavLink, Outlet, useLocation, useOutletContext } from 'react-router-dom'
import logo from '../assets/logo-farmacia-quilicura.jpg'
import LogoutButton from '../pages/e1-access-users-branches/auth/LogoutButton'
import type { AuthSession } from '../pages/e1-access-users-branches/auth/login.api'
import { adminNavigation, canAccessAdminPage } from './adminNavigation'
import './admin-layout.css'

export default function AdminLayout() {
  const session = useOutletContext<AuthSession>()
  const { pathname } = useLocation()
  const [expanded, setExpanded] = useState(() => {
    try {
      const preference = localStorage.getItem('sigfq-menu-expanded')
      if (preference !== null) return preference === 'true'
    } catch { /* El menú funciona también sin almacenamiento disponible. */ }
    return !window.matchMedia('(max-width: 800px)').matches
  })
  const navigation = adminNavigation.filter(item => canAccessAdminPage(item.path, session.user.permissions, session.user.roles))
  function toggleMenu() {
    const next = !expanded
    setExpanded(next)
    try { localStorage.setItem('sigfq-menu-expanded', String(next)) } catch { /* Preferencia opcional. */ }
  }
  function closeMobileMenu() {
    if (window.matchMedia('(max-width: 800px)').matches) setExpanded(false)
  }
  const current = adminNavigation.find(item => item.path === pathname)

  if (!canAccessAdminPage(pathname, session.user.permissions, session.user.roles)) {
    return <Navigate to="/session" replace />
  }

  return (
    <div className={`admin-shell${expanded ? ' admin-menu-open' : ' admin-menu-compact'}`}>
      <a className="admin-skip" href="#admin-content">Saltar al contenido</a>
      <aside className="admin-sidebar" id="admin-sidebar" aria-label="Menú principal">
        <NavLink className="admin-brand" to="/session" onClick={closeMobileMenu} aria-label="Farmacia Quilicura, resumen">
          {expanded ? <img src={logo} alt="Farmacia Quilicura — Cuidando tu salud" /> : <span className="admin-brand-short" aria-hidden="true">FQ</span>}
        </NavLink>
        <nav aria-label="Secciones del sistema" style={{ '--nav-count': navigation.length } as CSSProperties}>
          {navigation.map(item => (
            <NavLink key={item.path} to={item.path} end onClick={closeMobileMenu} aria-label={item.label} title={!expanded ? item.label : undefined} className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={item.icon} /></svg>
              <span className="admin-nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-brand-note"><span aria-hidden="true">🌿</span><p>Cuidando<br />la salud de nuestra<br />comunidad</p><span className="admin-brand-line" /></div>
      </aside>
      <div className="admin-workspace">
        <header className="admin-topbar">
          <button className="admin-menu-toggle" type="button" title={expanded ? 'Mostrar solo iconos' : 'Mostrar iconos y nombres'} aria-label={expanded ? 'Contraer menú a iconos' : 'Expandir menú'} aria-expanded={expanded} aria-controls="admin-sidebar" onClick={toggleMenu}>
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
