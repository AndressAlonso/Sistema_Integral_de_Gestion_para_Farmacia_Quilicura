import SessionDuration from './SessionDuration'
import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react'
import { Navigate, NavLink, Outlet, useLocation, useOutletContext } from 'react-router-dom'
import logo from '../assets/logo-farmacia-quilicura.jpg'
import LogoutButton from '../pages/e1-access-users-branches/auth/LogoutButton'
import type { AuthSession } from '../pages/e1-access-users-branches/auth/login.api'
import { adminNavigation, canAccessAdminPage } from './adminNavigation'
import './admin-layout.css'

export default function AdminLayout() {
  const session = useOutletContext<AuthSession>()
  const roleLabel = session.user.roles.map(role => {
    const label = role.replaceAll('_', ' ').toLocaleLowerCase('es')
    return label.charAt(0).toLocaleUpperCase('es') + label.slice(1)
  }).join(' · ') || 'Sin rol asignado'
  const { pathname } = useLocation()
  const [posFullscreen, setPosFullscreen] = useState(false)
  const fullscreenPos = posFullscreen && pathname === '/admin/pos'
  const ownsFullscreen = useRef(false)
  async function togglePosFullscreen() {
    if (posFullscreen) {
      if (ownsFullscreen.current && document.fullscreenElement) await document.exitFullscreen().catch(() => {})
      ownsFullscreen.current = false
      setPosFullscreen(false)
    } else {
      setPosFullscreen(true)
      if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
        try { await document.documentElement.requestFullscreen(); ownsFullscreen.current = true }
        catch { /* Keep the distraction-free POS when browser fullscreen is unavailable. */ }
      }
    }
  }
  useEffect(() => {
    function changed() {
      if (!document.fullscreenElement) { ownsFullscreen.current = false; setPosFullscreen(false) }
    }
    function escape(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape' && !document.fullscreenElement) setPosFullscreen(false)
    }
    document.addEventListener('fullscreenchange', changed)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('fullscreenchange', changed)
      document.removeEventListener('keydown', escape)
    }
  }, [])
  useEffect(() => {
    if (pathname !== '/admin/pos' && ownsFullscreen.current && document.fullscreenElement) {
      void document.exitFullscreen().catch(() => {})
    }
  }, [pathname])
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
  const navigation = adminNavigation.filter(item =>
    canAccessAdminPage(item.path, session.user.permissions, session.user.roles))
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
    <div className={`admin-shell${expanded ? ' admin-menu-open' : ' admin-menu-compact'}${fullscreenPos ? ' admin-pos-fullscreen' : ''}`}>
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
          <button className="admin-menu-toggle" type="button" title={mobile ? 'Abrir menú' : expanded ? 'Contraer menú' : 'Expandir menú'} aria-label={mobile ? 'Abrir menú' : expanded ? 'Contraer menú' : 'Expandir menú'} aria-expanded={mobile ? mobileOpen : expanded} aria-controls={mobile ? 'admin-mobile-menu' : 'admin-sidebar'} onClick={toggleMenu}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d={mobile ? 'M9 5l7 7-7 7' : expanded ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7'} strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>

          <NavLink className="admin-topbar-brand" to="/tienda" aria-label="Farmacia Quilicura, ir a la tienda"><img src={logo} alt="Farmacia Quilicura" /></NavLink>
          <h1 className="admin-page-title">{pathname === '/admin/pos' ? 'Punto de venta' : current?.label ?? 'Administración'}</h1>
          <div className="admin-topbar-user"><div className="admin-account"><span className="admin-avatar" aria-hidden="true">{(session.user.name?.trim() || roleLabel).slice(0, 2).toLocaleUpperCase('es')}</span><span className="admin-account-details"><span className="admin-account-name">{session.user.name?.trim() || 'Usuario'}</span><span className="admin-account-role">{roleLabel}</span><SessionDuration startedAt={session.started_at} expiresAt={session.expires_at} /></span></div>
          {pathname === '/admin/pos' && <button type="button" className="admin-pos-fullscreen-toggle" onClick={() => void togglePosFullscreen()} aria-pressed={fullscreenPos} aria-label={fullscreenPos ? 'Salir de pantalla completa' : 'Pantalla completa del POS'} title={fullscreenPos ? 'Salir de pantalla completa (Esc)' : 'Pantalla completa del POS'}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={fullscreenPos ? 'M3 8h5V3M16 3v5h5M21 16h-5v5M8 21v-5H3' : 'M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5'} /></svg></button>}
          <LogoutButton /></div>
        </header>
        <main id="admin-content" className="admin-content" tabIndex={-1} aria-label={current?.label ?? 'Contenido'}>
          <Outlet context={session} />
        </main>
      </div>
    </div>
  )
}




