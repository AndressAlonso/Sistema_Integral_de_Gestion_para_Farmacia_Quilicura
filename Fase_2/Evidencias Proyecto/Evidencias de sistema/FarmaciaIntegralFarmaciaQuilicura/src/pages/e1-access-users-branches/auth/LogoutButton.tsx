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
      <button type="button" className="auth-logout-button" disabled={loading} onClick={closeSession}>
        {loading ? 'Cerrando sesión…' : 'Cerrar sesión'}
      </button>
      {error && <p className="auth-logout-error" role="alert">{error}</p>}
    </div>
  )
}
