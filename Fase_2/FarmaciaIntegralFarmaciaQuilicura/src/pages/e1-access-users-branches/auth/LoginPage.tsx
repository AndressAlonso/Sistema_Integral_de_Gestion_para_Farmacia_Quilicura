// HU: E1-H1 — Iniciar sesión en la plataforma
import { useRef, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AuthError, login } from './login.api'
import logo from '../../../assets/logo-farmacia-quilicura.jpg'
import '../sprint-one.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [visible, setVisible] = useState(false)
  const [loading, setLoading] = useState(false)
  const sending = useRef(false)
  const [error, setError] = useState(location.state?.sessionExpired ? 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.' : '')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (sending.current) return
    const form = event.currentTarget
    if (!form.reportValidity()) return
    const data = new FormData(form)
    sending.current = true
    setLoading(true)
    setError('')
    try {
      await login(String(data.get('email') ?? '').trim(), String(data.get('password') ?? ''))
      form.reset()
      navigate('/session', { replace: true })
    } catch (cause) {
      setError(cause instanceof AuthError ? cause.message : 'Ocurrió un error inesperado. Intenta nuevamente.')
    } finally {
      sending.current = false
      setLoading(false)
    }
  }
  return (
    <div className="s1 s1-login">
      <aside className="s1-login-story">
        <img className="s1-logo" src={logo} alt="Farmacia Quilicura — Cuidando tu salud" />
        <div className="s1-story-copy">
          <p className="s1-kicker">Sistema integral de gestión</p>
          <h2>Cuidamos tu salud.<br /><span>Conectamos nuestra farmacia.</span></h2>
          <p>Un espacio de trabajo para el equipo de Farmacia Quilicura.</p>
          <div className="s1-story-note">Acceso interno<br />Gestión de sucursales y operaciones de la farmacia.</div>
        </div>
        <p className="s1-story-footer">SIGFQ · Farmacia Quilicura</p>
      </aside>
      <main className="s1-login-main">
        <div className="s1-login-card">
          <p className="s1-kicker">Bienvenido al equipo</p>
          <h1>Iniciar sesión</h1>
          <p className="s1-muted">Ingresa tus credenciales para acceder a tu espacio de trabajo.</p>
          {error && <p className="s1-error" role="alert">{error}</p>}
          <form onSubmit={submit} aria-busy={loading}>
            <div className="s1-field"><label htmlFor="login-email">Correo electrónico</label><input id="login-email" name="email" type="email" placeholder="nombre@farmacia.cl" autoComplete="username" required onChange={() => setError('')} /></div>
            <div className="s1-field"><label htmlFor="login-password">Contraseña</label><div className="s1-password"><input id="login-password" name="password" type={visible ? 'text' : 'password'} placeholder="Ingresa tu contraseña" autoComplete="current-password" required onChange={() => setError('')} /><button type="button" aria-pressed={visible} aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setVisible(!visible)}>{visible ? 'Ocultar' : 'Mostrar'}</button></div></div>
            <button className="s1-button primary" type="submit" disabled={loading}>{loading ? 'Iniciando sesión…' : 'Ingresar al sistema'} <span aria-hidden="true">→</span></button>
            <span className="sr-only" role="status">{loading ? 'Validando credenciales…' : ''}</span>
          </form>
        </div>
      </main>
    </div>
  )
}
