// HU: E1-H1 — Iniciar sesión en la plataforma
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import logo from '../../../assets/logo-farmacia-quilicura.jpg'
import '../sprint-one.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const [visible, setVisible] = useState(false)
  const [scenario, setScenario] = useState('valid')
  const [error, setError] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (scenario !== 'valid') {
      setError('No pudimos iniciar sesión. Verifica tus credenciales o contacta al administrador.')
      return
    }
    navigate('/admin/branches')
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
          <form onSubmit={submit}>
            <div className="s1-field"><label htmlFor="login-email">Correo electrónico</label><input id="login-email" name="email" type="email" placeholder="nombre@farmacia.cl" autoComplete="username" required onChange={() => setError('')} /></div>
            <div className="s1-field"><label htmlFor="login-password">Contraseña</label><div className="s1-password"><input id="login-password" name="password" type={visible ? 'text' : 'password'} placeholder="Ingresa tu contraseña" autoComplete="current-password" required onChange={() => setError('')} /><button type="button" aria-pressed={visible} aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setVisible(!visible)}>{visible ? 'Ocultar' : 'Mostrar'}</button></div></div>
            <button className="s1-button primary" type="submit">Ingresar al sistema <span aria-hidden="true">→</span></button>
          </form>
          <details className="s1-demo-controls" open>
            <summary>Probar diseño · Sprint 1</summary>
            <p className="s1-notice">Prototipo sin autenticación real. Usa un correo ficticio y cualquier contraseña de ejemplo; no se envían ni se guardan.</p>
            <div className="s1-field"><label htmlFor="login-scenario">Escenario de demostración</label><select id="login-scenario" value={scenario} onChange={(event) => { setScenario(event.target.value); setError('') }}><option value="valid">Acceso válido · administrador de ejemplo</option><option value="invalid">Credenciales inválidas</option><option value="inactive">Cuenta inactiva</option></select></div>
          </details>
        </div>
      </main>
    </div>
  )
}

