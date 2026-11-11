import { useEffect, useId, useRef, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { apiRequest } from '../../../services/http'
import { orderAccess } from '../services/orders.api'
import './order-pickup-code.css'

interface Credential { available: boolean; status: string; qr?: string; manual_code?: string }
export default function OrderPickupCode({ orderId, status }: { orderId: string; status: string }) {
  if (status !== 'LISTO_PARA_RETIRO') return null
  return <PickupCode key={orderId} orderId={orderId} status={status} />
}

function PickupCode({ orderId, status }: { orderId: string; status: string }) {
  const [open, setOpen] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    if (!open) return
    const element = dialog.current
    element?.showModal()
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { element?.close(); document.body.style.overflow = previous }
  }, [open])
  const [value, setValue] = useState<Credential | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!open || status !== 'LISTO_PARA_RETIRO') return
    let active = true, busy = false
    const load = async () => {
      if (busy) return
      busy = true
      try {
        const access = orderAccess(orderId)
        const response = await apiRequest(`/api/customers/orders/${orderId}/pickup-code`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(access ? { request_token: access.request_token } : {}), cache: 'no-store',
        }, {}, true)
        const data: Credential = await response.json()
        if (active) { setValue(data); setError('') }
      } catch {
        if (active) { setValue(null); setError('No pudimos consultar tu código de retiro. Intenta nuevamente.') }
      } finally { busy = false }
    }
    void load()
    const timer = window.setInterval(() => { void load() }, 15000)
    return () => { active = false; window.clearInterval(timer) }
  }, [orderId, status, retry, open])
  if (status !== 'LISTO_PARA_RETIRO') return null
  return <>
    <button className="pickup-launch" type="button" aria-haspopup="dialog" onClick={() => { setValue(null); setError(''); setOpen(true) }}>
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM15 15h2v2h-2zM21 14v7h-7M18 11v2M11 3v3M11 11h3M3 11h3M11 18v3" /></svg>
      Ver código de retiro <span aria-hidden="true">↗</span>
    </button>
    {open && <dialog ref={dialog} className="pickup-dialog" aria-labelledby={titleId} onCancel={() => setOpen(false)} onClose={() => setOpen(false)}>
    <button type="button" className="pickup-close" aria-label="Cerrar código de retiro" onClick={() => setOpen(false)}>×</button>
    <section className="customer-pickup-code" aria-label="Código de retiro">
    <span className="pickup-badge">RETIRO EN FARMACIA</span>
    <div><h3 id={titleId}>{value?.status === 'RETIRADO' ? '¡Pedido entregado!' : 'Tu pedido te espera'}</h3>
      <p>{value?.status === 'RETIRADO' ? 'La entrega ya fue registrada. Este código dejó de estar disponible.' : 'Muestra este QR al personal cuando recibas tus productos.'}</p></div>
    {value?.available && value.qr && value.manual_code && <>
      <div className="customer-pickup-qr"><QRCodeSVG value={value.qr} size={192} marginSize={4} title="QR de retiro del pedido" /></div>
      <div className="customer-pickup-manual"><span>O indica este código de retiro</span><strong>{value.manual_code.match(/.{1,4}/g)?.join(' ')}</strong><small>Tu código se mantiene hasta retirar el pedido. Compártelo solo con el personal al recibir tu compra.</small></div>
    </>}
    {!value && !error && <p role="status">Consultando código…</p>}
    {value && !value.available && value.status !== 'RETIRADO' && <p role="status">El código no está disponible para este pedido en este momento.</p>}
    {error && <div role="alert"><p>{error}</p><button type="button" onClick={() => { setValue(null); setError(''); setRetry(n => n + 1) }}>Reintentar</button></div>}
    <button type="button" className="pickup-done" onClick={() => setOpen(false)}>Entendido</button>
  </section></dialog>}
  </>
}
