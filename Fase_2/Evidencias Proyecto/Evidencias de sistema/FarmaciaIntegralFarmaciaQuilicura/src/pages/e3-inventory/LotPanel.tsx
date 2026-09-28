import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { ApiError } from '../../services/http'
import {
  createInventoryLot,
  listInventoryLots,
  type InventoryLot,
  type InventoryRecord,
} from './inventory.api'

interface LotPanelProps {
  inventoryRecords: InventoryRecord[]
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
}

function minimumExpirationDate(): string {
  const tomorrow = new Date()

  tomorrow.setDate(tomorrow.getDate() + 1)

  return tomorrow.toISOString().slice(0, 10)
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Tu sesión no es válida. Inicia sesión nuevamente.'
    }

    if (error.status === 403) {
      return 'No tienes permiso para gestionar lotes.'
    }

    if (error.status === 404) {
      return 'No existe el registro de inventario seleccionado.'
    }

    if (error.status === 409) {
      return (
        'Ya existe un lote con ese número para el producto '
        + 'y la sucursal seleccionados.'
      )
    }

    if (error.status === 422) {
      return 'Revisa el número, vencimiento y cantidad del lote.'
    }

    return error.message
  }

  return 'No pudimos completar la operación.'
}

export default function LotPanel({
  inventoryRecords,
}: LotPanelProps) {
  const [lots, setLots] = useState<InventoryLot[]>([])

  const [inventoryId, setInventoryId] = useState(
    inventoryRecords[0]?.id ?? '',
  )

  const [lotNumber, setLotNumber] = useState('')
  const [expirationDate, setExpirationDate] = useState('')
  const [quantity, setQuantity] = useState('')

  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadLots(): Promise<void> {
    setLoading(true)
    setError('')

    try {
      const records = await listInventoryLots()
      setLots(records)
    } catch (cause: unknown) {
      setError(getErrorMessage(cause))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadLots()
  }, [])

  useEffect(() => {
    if (!inventoryId && inventoryRecords.length > 0) {
      setInventoryId(inventoryRecords[0].id)
    }
  }, [inventoryId, inventoryRecords])

  const selectedInventory = useMemo(
    () => inventoryRecords.find(
      (record) => record.id === inventoryId,
    ),
    [inventoryId, inventoryRecords],
  )

  const totalLotQuantity = useMemo(
    () => lots
      .filter((lot) => lot.inventory_id === inventoryId)
      .reduce(
        (total, lot) => total + lot.quantity,
        0,
      ),
    [inventoryId, lots],
  )

  const firstFefoLotIds = useMemo(() => {
    const firstLotByInventory = new Map<string, string>()

    lots.forEach((lot) => {
      if (
        lot.is_active
        && lot.quantity > 0
        && !firstLotByInventory.has(lot.inventory_id)
      ) {
        firstLotByInventory.set(
          lot.inventory_id,
          lot.id,
        )
      }
    })

    return new Set(firstLotByInventory.values())
  }, [lots])

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()

    const numericQuantity = Number(quantity)

    if (!inventoryId) {
      setError('Selecciona un producto y una sucursal.')
      return
    }

    if (!lotNumber.trim()) {
      setError('Ingresa el número de lote.')
      return
    }

    if (!expirationDate) {
      setError('Selecciona la fecha de vencimiento.')
      return
    }

    if (
      !Number.isInteger(numericQuantity)
      || numericQuantity <= 0
    ) {
      setError(
        'La cantidad debe ser un número entero mayor que cero.',
      )
      return
    }

    setSubmitting(true)
    setError('')
    setSuccess('')

    try {
      await createInventoryLot({
        inventory_id: inventoryId,
        lot_number: lotNumber.trim(),
        expiration_date: expirationDate,
        quantity: numericQuantity,
      })

      setLotNumber('')
      setExpirationDate('')
      setQuantity('')

      await loadLots()

      setSuccess('Lote registrado correctamente.')
    } catch (cause: unknown) {
      setError(getErrorMessage(cause))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section
      className="lot-panel"
      aria-labelledby="lot-panel-title"
    >
      <div className="lot-panel-heading">
        <div>
          <p className="eyebrow">
            LOTES / TRAZABILIDAD
          </p>

          <h2 id="lot-panel-title">
            Lotes y fechas de vencimiento
          </h2>

          <p>
            Los registros se presentan según FEFO:
            primero en vencer, primero en salir.
          </p>
        </div>

        <span className="inventory-result-count">
          {lots.length}{' '}
          {lots.length === 1 ? 'lote' : 'lotes'}
        </span>
      </div>

      <form
        className="lot-form"
        onSubmit={(event) => {
          void handleSubmit(event)
        }}
      >
        <div className="lot-field lot-inventory-field">
          <label htmlFor="lot-inventory">
            Producto y sucursal
          </label>

          <select
            id="lot-inventory"
            value={inventoryId}
            onChange={(event) => {
              setInventoryId(event.target.value)
              setError('')
              setSuccess('')
            }}
            required
          >
            {inventoryRecords.length === 0 && (
              <option value="">
                No hay inventario disponible
              </option>
            )}

            {inventoryRecords.map((record) => (
              <option
                key={record.id}
                value={record.id}
              >
                {record.product_name} · {record.branch_name}
              </option>
            ))}
          </select>
        </div>

        <div className="lot-field">
          <label htmlFor="lot-number">
            Número de lote
          </label>

          <input
            id="lot-number"
            type="text"
            maxLength={80}
            placeholder="Ej.: PAR-2028-001"
            value={lotNumber}
            onChange={(event) => {
              setLotNumber(event.target.value)
            }}
            required
          />
        </div>

        <div className="lot-field">
          <label htmlFor="expiration-date">
            Fecha de vencimiento
          </label>

          <input
            id="expiration-date"
            type="date"
            min={minimumExpirationDate()}
            value={expirationDate}
            onChange={(event) => {
              setExpirationDate(event.target.value)
            }}
            required
          />
        </div>

        <div className="lot-field lot-quantity-field">
          <label htmlFor="lot-quantity">
            Cantidad
          </label>

          <input
            id="lot-quantity"
            type="number"
            min={1}
            step={1}
            placeholder="0"
            value={quantity}
            onChange={(event) => {
              setQuantity(event.target.value)
            }}
            required
          />
        </div>

        <button
          type="submit"
          className="lot-submit-button"
          disabled={
            submitting
            || inventoryRecords.length === 0
          }
        >
          {submitting
            ? 'Registrando…'
            : 'Registrar lote'}
        </button>
      </form>

      {error && (
        <p
          className="lot-message lot-error"
          role="alert"
        >
          {error}
        </p>
      )}

      {success && (
        <p
          className="lot-message lot-success"
          role="status"
        >
          {success}
        </p>
      )}

      {selectedInventory && (
        <div className="lot-consistency">
          <span>
            Stock físico: {selectedInventory.physical}
          </span>

          <span>
            Cantidad registrada en lotes: {totalLotQuantity}
          </span>

          <span
            className={
              selectedInventory.physical === totalLotQuantity
                ? 'lot-consistent'
                : 'lot-warning'
            }
          >
            Diferencia:{' '}
            {selectedInventory.physical - totalLotQuantity}
          </span>
        </div>
      )}

      {loading ? (
        <p
          className="lot-loading"
          role="status"
        >
          Cargando lotes…
        </p>
      ) : (
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Lotes ordenados por vencimiento"
        >
          <table className="lot-table">
            <caption className="sr-only">
              Lotes de inventario ordenados mediante FEFO
            </caption>

            <thead>
              <tr>
                <th scope="col">Producto</th>
                <th scope="col">Sucursal</th>
                <th scope="col">Lote</th>
                <th scope="col">Vencimiento</th>

                <th
                  scope="col"
                  className="numeric"
                >
                  Cantidad
                </th>

                <th scope="col">Estado</th>
              </tr>
            </thead>

            <tbody>
              {lots.map((lot) => {
                const isNextFefo = (
                  firstFefoLotIds.has(lot.id)
                )

                return (
                  <tr key={lot.id}>
                    <th scope="row">
                      <span className="product-name">
                        {lot.product_name}
                      </span>

                      <span className="product-detail">
                        SKU: {lot.product_sku}
                      </span>
                    </th>

                    <td>
                      <span className="branch-label">
                        {lot.branch_name}{' '}
                        ({lot.branch_code})
                      </span>
                    </td>

                    <td>
                      <span className="lot-number">
                        {lot.lot_number}
                      </span>
                    </td>

                    <td>
                      {formatDate(lot.expiration_date)}
                    </td>

                    <td className="numeric">
                      {lot.quantity}
                    </td>

                    <td>
                      {isNextFefo ? (
                        <span className="lot-status lot-fefo">
                          Próximo por FEFO
                        </span>
                      ) : (
                        <span className="lot-status">
                          {lot.is_active
                            ? 'Activo'
                            : 'Inactivo'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}

              {lots.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="empty-state"
                  >
                    No hay lotes registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}