import { useCallback, useEffect, useId, useRef, useState, useSyncExternalStore } from 'react'
import './notification.css'

type Kind = 'success' | 'error' | 'info'
type Entry = { id: string; message: string; height: number }
let entries: Entry[] = []
const listeners = new Set<() => void>()
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
const snapshot = () => entries
function publish(next: Entry[]) {
  entries = next
  listeners.forEach(listener => listener())
}

/** Mensajes de operaciones; las validaciones y decisiones permanecen en su formulario. */
export default function Notification({ message, kind = 'error' }: { message: string; kind?: Kind }) {
  return message ? <NotificationItem key={`${kind}:${message}`} message={message} kind={kind} /> : null
}

function NotificationItem({ message, kind }: { message: string; kind: Kind }) {
  const id = useId()
  const ref = useRef<HTMLDivElement>(null)
  const anchor = useRef<HTMLSpanElement>(null)
  const [dismissed, setDismissed] = useState(false)
  const [closing, setClosing] = useState(false)
  const [paused, setPaused] = useState(false)
  const current = useSyncExternalStore(subscribe, snapshot, snapshot)
  // Si el mismo error aparece en la página y su modal, mostrar solo el último.
  const visible = current.filter((entry, index) => !current.slice(index + 1).some(other => other.message === entry.message)).slice(-3)
  const index = visible.findIndex(entry => entry.id === id)
  const isVisible = index >= 0
  const offset = visible.slice(0, Math.max(0, index)).reduce((total, entry) => total + entry.height + 12, 20)
  const close = useCallback(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) setDismissed(true)
    else setClosing(true)
  }, [])

  useEffect(() => {
    if (!closing) return
    const timer = window.setTimeout(() => setDismissed(true), 200)
    return () => window.clearTimeout(timer)
  }, [closing])

  useEffect(() => {
    if (dismissed) return
    const dialog = anchor.current?.closest('dialog')
    const sync = () => {
      const registered = entries.some(entry => entry.id === id)
      if ((!dialog || dialog.open) && !registered) publish([...entries, { id, message, height: 110 }])
      else if (dialog && !dialog.open && registered) publish(entries.filter(entry => entry.id !== id))
    }
    sync()
    const observer = dialog ? new MutationObserver(sync) : null
    if (dialog) observer?.observe(dialog, { attributes: true, attributeFilter: ['open'] })
    return () => { observer?.disconnect(); publish(entries.filter(entry => entry.id !== id)) }
  }, [id, message, dismissed])

  useEffect(() => {
    const node = ref.current
    if (!node || dismissed || !isVisible) return
    // Popover entra en la capa superior, incluso dentro de un dialog modal.
    node.showPopover?.()
    const measure = () => {
      const height = node.getBoundingClientRect().height
      if (height > 0 && entries.find(entry => entry.id === id)?.height !== height) {
        publish(entries.map(entry => entry.id === id ? { ...entry, height } : entry))
      }
    }
    measure()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure)
    observer?.observe(node)
    return () => { observer?.disconnect(); node.hidePopover?.() }
  }, [id, dismissed, isVisible])

  useEffect(() => {
    if (kind === 'error' || dismissed || closing || paused || !isVisible) return
    const timer = window.setTimeout(close, 8000)
    return () => window.clearTimeout(timer)
  }, [kind, dismissed, closing, paused, isVisible, close])

  const supportsPopover = typeof HTMLElement !== 'undefined' && typeof HTMLElement.prototype.showPopover === 'function'
  return <><span hidden ref={anchor} />{!dismissed && isVisible && <div ref={ref} popover={supportsPopover ? 'manual' : undefined} className={`app-notification app-notification-${kind}${closing ? ' is-closing' : ''}`}
    style={{ top: offset }} role={kind === 'error' ? 'alert' : 'status'} aria-atomic="true"
    onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
    onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
    <span className="app-notification-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {kind === 'error' ? <><path d="m8 3-5 5v8l5 5h8l5-5V8l-5-5H8Z" /><path d="m9 9 6 6m0-6-6 6" /></> : <><circle cx="12" cy="12" r="9" /><path d={kind === 'success' ? 'm8 12 3 3 5-6' : 'M12 11v6m0-10h.01'} /></>}
      </svg>
    </span>
    <div className="app-notification-copy"><p className="app-notification-message">{message}</p></div>
    <button className="app-notification-close" type="button" aria-label="Cerrar notificación" onClick={close}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
    </button>
  </div>}</>
}
