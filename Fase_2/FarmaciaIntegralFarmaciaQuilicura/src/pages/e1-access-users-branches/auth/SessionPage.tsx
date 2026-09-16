import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthError, logout } from './login.api'
import './auth.css'

export default function SessionPage() {
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
    <main className="s1 auth-session">
      <h1 className="sr-only">Sesión iniciada</h1>
      <button className="s1-button" disabled={loading} onClick={closeSession}>
        {loading ? 'Cerrando sesión…' : 'Cerrar sesión'}
      </button>
      {error && <p className="s1-error" role="alert">{error}</p>}
    </main>
  )
}
