import { useEffect, useRef, useState } from 'react'
import Notification from '../../components/Notification'
import { QRCodeSVG } from 'qrcode.react'

import { ApiError } from '../../services/http'
import { scannerApi, type ScannerLink } from './scanner.api'

type Props = {
  userName: string
  branchName: string
  onLinkChange: (link: ScannerLink | null) => void
}

const labels = {
  PENDING: 'Esperando al teléfono',
  LINKED: 'Teléfono vinculado',
  REVOKED: 'Vinculación cancelada',
  EXPIRED: 'El código o la conexión venció',
  DISCONNECTED: 'La conexión terminó',
}

function message(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : 'No pudimos completar la operación.'
}

export default function ScannerLinkDialog({
  userName,
  branchName,
  onLinkChange,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const locked = useRef(false)

  const [link, setLink] = useState<ScannerLink | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [connectionError, setConnectionError] = useState('')

  const linkId = link?.id
  const linkState = link?.state
  const active = linkState === 'PENDING' || linkState === 'LINKED'
    useEffect(() => {
    let disposed = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function restore() {
      try {
        const current = await scannerApi.current()
        if (disposed) return

        setLink(current)
        setConnectionError('')
        setBusy(false)
      } catch (cause) {
        if (disposed) return

        setConnectionError(message(cause))

        if (
          cause instanceof ApiError &&
          [401, 403, 404].includes(cause.status)
        ) {
          setBusy(false)
          return
        }

        timer = setTimeout(() => void restore(), 3000)
      }
    }

    void restore()

    return () => {
      disposed = true
      if (timer !== undefined) clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    onLinkChange(
      !busy && !connectionError && link?.state === 'LINKED'
        ? link
        : null,
    )
  }, [link, busy, connectionError, onLinkChange])

  useEffect(() => {
    if (!linkId || !active || busy) return

    let disposed = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      try {
        const result = await scannerApi.status(linkId!)

        if (disposed || locked.current) return

        setLink(result)
        setConnectionError('')

        if (result.state !== 'PENDING') {
          setCode('')
        }

        if (result.state !== 'PENDING' && result.state !== 'LINKED') {
          return
        }
      } catch (cause) {
        if (disposed || locked.current) return

        setConnectionError(message(cause))

        if (
          cause instanceof ApiError &&
          [401, 403, 404].includes(cause.status)
        ) {
          setCode('')
          return
        }
      }

      if (!disposed) {
        timer = setTimeout(() => void poll(), 2000)
      }
    }

    timer = setTimeout(() => void poll(), 1000)

    return () => {
      disposed = true
      if (timer !== undefined) clearTimeout(timer)
    }
  }, [linkId, active, busy])

  async function generate() {
    if (locked.current) return

    locked.current = true
    setBusy(true)
    setError('')

    try {
      // Antes de reemplazarlo, invalida el código o vínculo anterior.
      if (link && active) {
        const revoked = await scannerApi.revoke(link.id)
        setLink(revoked)
        setCode('')
      }

      const created = await scannerApi.create()
      const { pairing_code, ...status } = created

      setLink(status)
      setCode(pairing_code)
      setConnectionError('')
    } catch (cause) {
      setError(message(cause))
    } finally {
      locked.current = false
      setBusy(false)
    }
  }

  async function revoke() {
    if (!link || locked.current) return

    locked.current = true
    setBusy(true)
    setError('')

    try {
      const result = await scannerApi.revoke(link.id)
      setLink(result)
      setCode('')
      setConnectionError('')
    } catch (cause) {
      setError(message(cause))
    } finally {
      locked.current = false
      setBusy(false)
    }
  }

  const showQr =
    link?.state === 'PENDING' &&
    code !== '' &&
    !connectionError &&
    !busy

  return (
    <>
      <button
        className="pos-secondary"
        title={connectionError ? 'Revisar conexión' : link?.state === 'LINKED' ? 'Teléfono vinculado' : 'Vincular sesión'}
        type="button"
        onClick={() => dialog.current?.showModal()}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2ZM10 5h4M11 18h2" /></svg>
        <span className="sr-only">{connectionError
          ? 'Revisar conexión'
          : link?.state === 'LINKED'
            ? 'Teléfono vinculado'
            : 'Vincular sesión'}</span>
      </button>

      <dialog
        className="pos-dialog scanner-link-dialog"
        ref={dialog}
        aria-labelledby="scanner-link-title"
        onCancel={event => {
          if (busy) event.preventDefault()
        }}
      >
        <div className="pos-dialog-body">
          <div className="pos-section-title">
            <h2 id="scanner-link-title">Vincular teléfono</h2>
            <button
              type="button"
              className="pos-secondary"
              disabled={busy}
              onClick={() => dialog.current?.close()}
            >
              Cerrar
            </button>
          </div>

          <p className="pos-muted">
            {userName} · {branchName}
          </p>

          <p>
            Inicia sesión en la app con la misma cuenta y escanea
            el QR desde la opción de vinculación.
          </p>

          <p className="pos-notice" role="status">
            {connectionError
              ? 'No pudimos verificar el estado de la conexión.'
              : link
                ? labels[link.state]
                : 'Genera un código con tu caja abierta.'}
          </p>

          {showQr && (
            <div className="scanner-link-qr">
              <QRCodeSVG
                value={`sigfq:pair:v1:${code}`}
                size={240}
                level="M"
                marginSize={4}
                bgColor="#FFFFFF"
                fgColor="#172B22"
                title="Código QR para vincular el teléfono al POS"
              />
              <p className="pos-muted">
                Un solo uso. Válido hasta{' '}
                {new Date(link.qr_expires_at).toLocaleTimeString(
                  'es-CL',
                  { hour: '2-digit', minute: '2-digit', second: '2-digit' },
                )}.
              </p>
            </div>
          )}

          {link?.state === 'LINKED' && !connectionError && (
            <p>
              Teléfono conectado. Puedes escanear productos para
              agregarlos a esta venta.
            </p>
          )}

          {(error || connectionError) && (
            <Notification message={error || connectionError} kind="error" />
          )}

          <div className="scanner-link-actions">
            {link?.state !== 'LINKED' && (
              <button
                className="pos-primary"
                type="button"
                disabled={busy}
                onClick={() => void generate()}
              >
                {busy
                  ? 'Procesando…'
                  : link
                    ? 'Generar nuevo QR'
                    : 'Generar QR'}
              </button>
            )}

            {active && (
              <button
                className="pos-secondary"
                type="button"
                disabled={busy}
                onClick={() => void revoke()}
              >
                {link?.state === 'LINKED'
                  ? 'Desvincular teléfono'
                  : 'Cancelar vinculación'}
              </button>
            )}
          </div>

          <p className="pos-muted">
            Cerrar esta ventana no cancela la vinculación.
          </p>
        </div>
      </dialog>
    </>
  )
}
