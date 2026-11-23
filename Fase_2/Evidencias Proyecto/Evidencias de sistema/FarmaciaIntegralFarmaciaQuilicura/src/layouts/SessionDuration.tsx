import { useEffect, useState } from 'react'

export default function SessionDuration({ startedAt, expiresAt }: { startedAt?: string; expiresAt: string }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  if (!startedAt || !Number.isFinite(Date.parse(startedAt))) return null
  const seconds = Math.max(0, Math.floor((Math.min(now, Date.parse(expiresAt)) - Date.parse(startedAt)) / 1000))
  const time = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60].map(value => String(value).padStart(2, '0')).join(':')
  return <span className="admin-session-duration" title="Tiempo transcurrido desde el inicio de esta sesión">Conectado: {time}</span>
}
