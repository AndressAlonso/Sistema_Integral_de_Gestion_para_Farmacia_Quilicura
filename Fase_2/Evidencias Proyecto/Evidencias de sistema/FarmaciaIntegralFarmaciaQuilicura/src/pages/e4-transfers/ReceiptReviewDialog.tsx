import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import ReceiptReviewPanel from './ReceiptReviewPanel'

export default function ReceiptReviewDialog({ transferId, onClose }: { transferId: string; onClose: () => void }) {
  const titleId = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { if (element?.open) element.close() }
  }, [])
  return createPortal(<dialog ref={dialog} className="users-dialog transfers-dialog receipt-review-dialog"
    aria-labelledby={titleId} aria-busy={busy} onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
    <header className="users-dialog-heading"><h2 id={titleId}>Revisar lote destino</h2>
      <button type="button" className="users-close" disabled={busy} onClick={onClose} aria-label="Cerrar revisión de lote">×</button></header>
    <ReceiptReviewPanel transferId={transferId} disabled={false} autoReview
      onBusyChange={setBusy} />
    <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={onClose}>Volver a la recepción</button></footer>
  </dialog>, document.body)
}
