import Notification from '../../../components/Notification'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthError, logout } from './login.api'

export default function LogoutButton() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const sending = useRef(false)

  async function closeSession() {
    if (sending.current) return
    sending.current = true
    setLoading(true)
    setError('')
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch (cause) {
      setError(cause instanceof AuthError ? cause.message : 'No pudimos cerrar la sesión. Intenta nuevamente.')
    } finally {
      sending.current = false
      setLoading(false)
    }
  }

  return (
    <div className="auth-logout">
      <button type="button" className="auth-logout-button" disabled={loading} aria-busy={loading} aria-label={loading ? 'Cerrando sesión…' : 'Cerrar sesión'} title={loading ? 'Cerrando sesión…' : 'Cerrar sesión'} onClick={closeSession}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 5H4v14h5M10 12h11m-4-4 4 4-4 4" /></svg>
      </button>
      {error && <Notification message={error} kind="error" />}
    </div>
  )
}


