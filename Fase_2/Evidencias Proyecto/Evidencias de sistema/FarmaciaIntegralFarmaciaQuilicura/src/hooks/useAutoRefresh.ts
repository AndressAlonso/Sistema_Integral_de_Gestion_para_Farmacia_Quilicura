import { useEffect, useRef } from 'react'

/** Refreshes data, never the document. Keeps forms, filters and scroll intact. */
export default function useAutoRefresh(refresh: () => void | Promise<void>, enabled = true, interval = 20_000, pauseInDialog = true) {
  const latest = useRef({ refresh, enabled })
  useEffect(() => { latest.current = { refresh, enabled } }, [refresh, enabled])
  useEffect(() => {
    let active = true, running = false, last = 0
    const update = async () => {
      const focused = document.activeElement
      if (!active || running || !latest.current.enabled || document.hidden || !navigator.onLine
        || (pauseInDialog && document.querySelector('dialog[open]'))
        || focused?.matches('input, textarea, select, [contenteditable="true"]')
        || Date.now() - last < 5_000) return
      last = Date.now(); running = true
      try { await latest.current.refresh() } finally { running = false }
    }
    const trigger = () => { void update().catch(() => { /* The caller owns its error state. */ }) }
    const timer = window.setInterval(trigger, interval)
    window.addEventListener('focus', trigger)
    window.addEventListener('online', trigger)
    document.addEventListener('visibilitychange', trigger)
    return () => {
      active = false; window.clearInterval(timer)
      window.removeEventListener('focus', trigger)
      window.removeEventListener('online', trigger)
      document.removeEventListener('visibilitychange', trigger)
    }
  }, [interval, pauseInDialog])
}
