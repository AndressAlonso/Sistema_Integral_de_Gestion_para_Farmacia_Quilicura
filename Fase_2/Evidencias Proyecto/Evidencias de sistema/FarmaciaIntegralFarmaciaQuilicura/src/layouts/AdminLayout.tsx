import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react'
import { Navigate, NavLink, Outlet, useLocation, useOutletContext } from 'react-router-dom'
import logo from '../assets/logo-farmacia-quilicura.jpg'
import LogoutButton from '../pages/e1-access-users-branches/auth/LogoutButton'
import type { AuthSession } from '../pages/e1-access-users-branches/auth/login.api'
import { adminNavigation, canAccessAdminPage } from './adminNavigation'
import './admin-layout.css'

export default function AdminLayout() {
  const session = useOutletContext<AuthSession>()
  const { pathname } = useLocation()
  const drawer = useRef<HTMLDialogElement>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 800px)').matches)
  useEffect(() => {
    const media = window.matchMedia('(max-width: 800px)')
    const closeOnDesktop = () => { setMobile(media.matches); if (!media.matches) drawer.current?.close() }
    media.addEventListener('change', closeOnDesktop)
    return () => media.removeEventListener('change', closeOnDesktop)
  }, [])
  const [expanded, setExpanded] = useState(() => {
    try {
      const preference = localStorage.getItem('sigfq-menu-expanded')
      if (preference !== null) return preference === 'true'
    } catch { /* El menú funciona también sin almacenamiento disponible. */ }
    return !window.matchMedia('(max-width: 800px)').matches
  })
  const hasSummary = canAccessAdminPage('/admin/dashboard', session.user.permissions, session.user.roles)
  const navigation = adminNavigation.filter(item =>
    !(item.path === '/session' && hasSummary)
    && canAccessAdminPage(item.path, session.user.permissions, session.user.roles))
  function toggleMenu() {
    if (window.matchMedia('(max-width: 800px)').matches) {
      drawer.current?.showModal()
      setMobileOpen(true)
      return
    }
    const next = !expanded
    setExpanded(next)
    try { localStorage.setItem('sigfq-menu-expanded', String(next)) } catch { /* Preferencia opcional. */ }
  }
  function closeMobileMenu() {
    drawer.current?.close()
  }
  function keepMenuFocus(event: KeyboardEvent<HTMLDialogElement>) {
    if (event.key !== 'Tab') return
    const controls = event.currentTarget.querySelectorAll<HTMLElement>('button, a[href]')
    const first = controls[0]
    const last = controls[controls.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
  const current = adminNavigation.find(item => item.path === pathname)

  if (!canAccessAdminPage(pathname, session.user.permissions, session.user.roles)) {
    return <Navigate to="/session" replace />
  }

  return (
    <div className={`admin-shell${expanded ? ' admin-menu-open' : ' admin-menu-compact'}`}>
      <a className="admin-skip" href="#admin-content">Saltar al contenido</a>
      <dialog id="admin-mobile-menu" ref={drawer} className="admin-mobile-drawer" aria-label="Menú principal" onKeyDown={keepMenuFocus} onClose={() => setMobileOpen(false)} onClick={event => { if (event.target === event.currentTarget) closeMobileMenu() }}>
        <div className="admin-drawer-content">
          <header><strong>Farmacia Quilicura</strong><button type="button" className="admin-menu-toggle" onClick={closeMobileMenu} aria-label="Cerrar menú">✕</button></header>
          <nav aria-label="Secciones del sistema">
            {navigation.map(item => <NavLink key={item.path} to={item.path} end onClick={closeMobileMenu} className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d={item.icon} /></svg>{item.label}
            </NavLink>)}
          </nav>
        </div>
      </dialog>
      <aside className="admin-sidebar" id="admin-sidebar" aria-label="Menú principal">
        <NavLink className="admin-brand" to="/tienda" onClick={closeMobileMenu} aria-label="Farmacia Quilicura, ir a la tienda">
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
          <button className="admin-menu-toggle" type="button" title="Menú de navegación" aria-label="Menú de navegación" aria-expanded={mobile ? mobileOpen : expanded} aria-controls={mobile ? 'admin-mobile-menu' : 'admin-sidebar'} onClick={toggleMenu}>
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
