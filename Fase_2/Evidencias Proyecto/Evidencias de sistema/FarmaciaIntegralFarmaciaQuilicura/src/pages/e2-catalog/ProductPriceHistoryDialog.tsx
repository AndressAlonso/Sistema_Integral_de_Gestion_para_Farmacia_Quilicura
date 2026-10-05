import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../../services/http'
import {
  listProductPriceHistory,
  type Product,
  type ProductPriceHistoryEntry,
} from './catalog.api'

type Props = {
  product: Product
  onClose: () => void
}

const currency = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

const dateTime = new Intl.DateTimeFormat('es-CL', {
  dateStyle: 'medium',
  timeStyle: 'medium',
  timeZone: 'America/Santiago',
})

export default function ProductPriceHistoryDialog({
  product,
  onClose,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const navigate = useNavigate()
  const [entries, setEntries] = useState<ProductPriceHistoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const element = dialog.current
    element?.showModal()

    return () => {
      if (element?.open) element.close()
    }
  }, [])

  useEffect(() => {
    let active = true

    listProductPriceHistory(product.id)
      .then(history => {
        if (!active) return
        setEntries(history)
        setLoading(false)
      })
      .catch((cause: unknown) => {
        if (!active) return

        if (cause instanceof ApiError && cause.status === 401) {
          navigate('/login', { replace: true })
          return
        }

        setError(
          cause instanceof ApiError
            ? cause.message
            : 'No pudimos cargar el historial de precios.',
        )
        setLoading(false)
      })

    return () => { active = false }
  }, [product.id, attempt, navigate])

  function retry() {
    setError('')
    setLoading(true)
    setAttempt(value => value + 1)
  }

  return (
    <dialog
      ref={dialog}
      className="app-modal users-dialog catalog-dialog catalog-history-dialog"
      aria-labelledby="price-history-title"
      onCancel={event => {
        event.preventDefault()
        onClose()
      }}
    >
      <header className="users-dialog-heading">
        <div>
          <h2 id="price-history-title">Historial de precios</h2>
          <p className="catalog-help">
            {product.name} · SKU: {product.sku}
          </p>
        </div>
        <button
          type="button"
          className="users-close"
          aria-label="Cerrar historial"
          onClick={onClose}
        >
          ×
        </button>
      </header>

      <section aria-busy={loading} aria-label="Cambios de precio">
        {loading && <p role="status">Cargando historial…</p>}

        {error && (
          <div>
            <p className="users-error" role="alert">{error}</p>
            <button
              type="button"
              className="users-button"
              onClick={retry}
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            <p className="catalog-help" role="status">
              {entries.length} {entries.length === 1
                ? 'cambio registrado'
                : 'cambios registrados'}.
              {' '}Del más reciente al más antiguo.
              {' '}Fechas en horario de Santiago.
            </p>

            {entries.length === 0 ? (
              <p className="catalog-notice">
                Este producto todavía no tiene cambios de precio registrados.
              </p>
            ) : (
              <div
                className="users-table-scroll"
                role="region"
                aria-label="Historial de cambios de precio"
                tabIndex={0}
              >
                <table className="users-table">
                  <thead>
                    <tr>
                      <th scope="col">Fecha y hora</th>
                      <th scope="col">Precio anterior</th>
                      <th scope="col">Precio nuevo</th>
                      <th scope="col">Responsable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map(entry => (
                      <tr key={entry.id}>
                        <td>
                          <time dateTime={entry.changed_at}>
                            {dateTime.format(new Date(entry.changed_at))}
                          </time>
                        </td>
                        <td className="catalog-price">
                          {currency.format(Number(entry.previous_price))}
                        </td>
                        <td className="catalog-price">
                          {currency.format(Number(entry.new_price))}
                        </td>
                        <td>{entry.user_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <footer className="users-dialog-actions">
        <button
          type="button"
          className="users-button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </footer>
    </dialog>
  )
}