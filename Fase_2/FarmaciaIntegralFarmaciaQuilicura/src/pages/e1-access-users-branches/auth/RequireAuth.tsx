import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { AuthError, getSession, type AuthSession } from './login.api'
import '../sprint-one.css'

export default function RequireAuth() {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [invalid, setInvalid] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    let checking = false
    let expiry: ReturnType<typeof setTimeout>

    async function validate() {
      if (checking) return
      checking = true
      try {
        const current = await getSession()
        if (!active) return
        const remaining = Date.parse(current.expires_at) - Date.now()
        if (remaining <= 0) {
          setInvalid(true)
          setSession(null)
          return
        }
        setSession(current)
        setError('')
        clearTimeout(expiry)
        expiry = setTimeout(() => { setInvalid(true); setSession(null) }, remaining)
      } catch (cause) {
        if (!active) return
        setSession(null)
        if (cause instanceof AuthError && [401, 403].includes(cause.status)) {
          setInvalid(true)
        } else {
          setError(cause instanceof AuthError ? cause.message : 'No pudimos verificar tu sesión.')
        }
      } finally {
        checking = false
      }
    }

    void validate()
    const interval = setInterval(() => void validate(), 60_000)
    const onFocus = () => void validate()
    window.addEventListener('focus', onFocus)
    return () => {
      active = false
      clearTimeout(expiry)
      clearInterval(interval)
      window.removeEventListener('focus', onFocus)
    }
  }, [attempt])

  if (invalid) return <Navigate to="/login" replace state={{ sessionExpired: true }} />
  if (error) return <main className="s1 s1-content"><p className="s1-error" role="alert">{error}</p><button className="s1-button" onClick={() => { setError(''); setAttempt(value => value + 1) }}>Reintentar</button></main>
  if (!session) return <main className="s1 s1-content"><p role="status">Verificando sesión…</p></main>
  return <><p className="sr-only" role="status">Sesión iniciada como {session.user.email}.</p><Outlet /></>
}
