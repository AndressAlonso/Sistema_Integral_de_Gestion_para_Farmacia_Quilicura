import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { loginCustomer, registerCustomer } from '../services/customers.api'
import { useCustomerSession } from '../hooks/useCustomerSession'
import PublicHeader from './PublicHeader'
import '../customer-auth.css'

export default function CustomerAuthForm({ registration = false }: { registration?: boolean }) {
  const navigate = useNavigate()
  const { updateCustomer } = useCustomerSession()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [registered, setRegistered] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (registration && password !== confirmation) {
      setError('Las contraseñas no coinciden.')
      return
    }
    if (registration && !name.trim()) {
      setError('Ingresa tu nombre.')
      return
    }
    setBusy(true)
    try {
      const credentials = { email: email.trim().toLowerCase(), password }
      if (registration) {
        await registerCustomer({ ...credentials, name: name.trim() })
        setRegistered(true)
      } else {
        const session = await loginCustomer(credentials)
        updateCustomer(session.customer)
        navigate('/tienda')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No pudimos completar la solicitud.')
    } finally {
      setPassword('')
      setConfirmation('')
      setBusy(false)
    }
  }

  return (
    <main className="customer-auth">
      <PublicHeader />
      <section className="customer-auth-panel" aria-labelledby="customer-auth-title">
        <p className="customer-auth-eyebrow">Cuenta de cliente</p>
        <h1 id="customer-auth-title">{registration ? 'Crear cuenta' : 'Iniciar sesión'}</h1>
        {registered ? (
          <div role="status">
            <p>Tu cuenta fue creada. Ahora puedes iniciar sesión.</p>
            <Link className="customer-auth-action" to="/tienda/iniciar-sesion">Ir a iniciar sesión</Link>
          </div>
        ) : (
          <form onSubmit={submit} aria-busy={busy}>
            {registration && <label htmlFor="customer-name">Nombre
              <input id="customer-name" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required maxLength={150} disabled={busy} />
            </label>}
            <label htmlFor="customer-email">Correo electrónico
              <input id="customer-email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} disabled={busy} />
            </label>
            <label htmlFor="customer-password">Contraseña
              <input id="customer-password" type="password" autoComplete={registration ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} required minLength={12} maxLength={128} aria-describedby="customer-password-help" disabled={busy} />
            </label>
            <p id="customer-password-help" className="customer-auth-help">Entre 12 y 128 caracteres. Puedes usar una frase.</p>
            {registration && <label htmlFor="customer-confirmation">Confirmar contraseña
              <input id="customer-confirmation" type="password" autoComplete="new-password" value={confirmation} onChange={e => setConfirmation(e.target.value)} required minLength={12} maxLength={128} disabled={busy} />
            </label>}
            {error && <p className="customer-auth-error" role="alert">{error}</p>}
            <button type="submit" disabled={busy}>{busy ? 'Procesando…' : registration ? 'Crear cuenta' : 'Iniciar sesión'}</button>
          </form>
        )}
        <p className="customer-auth-footer"><Link to="/tienda">Volver al catálogo</Link></p>
        <p className="customer-auth-footer">Personal de la farmacia: <Link to="/login">acceso interno</Link></p>
      </section>
    </main>
  )
}
