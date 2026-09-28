import {
  type FormEvent,
  useEffect,
  useState,
} from 'react'

import { ApiError } from '../../services/http'
import {
  type InventoryMovement,
  type InventoryRecord,
  listInventoryMovements,
} from './inventory.api'

interface InventoryMovementHistoryProps {
  inventoryRecords: InventoryRecord[]
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function signedQuantity(value: number): string {
  if (value > 0) {
    return `+${value}`
  }

  return String(value)
}

function movementTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    SALDO_INICIAL: 'Registro inicial',
    ENTRADA: 'Entrada de unidades',
    SALIDA: 'Salida de unidades',
    RESERVA: 'Reserva de unidades',
    LIBERACION_RESERVA: 'Liberación de reserva',
    AJUSTE: 'Ajuste de inventario',
    TRANSFERENCIA_SALIDA: 'Transferencia enviada',
    TRANSFERENCIA_ENTRADA: 'Transferencia recibida',
    VENTA: 'Venta',
    RECEPCION: 'Recepción de productos',
  }

  return (
    labels[value]
    ?? value
      .replaceAll('_', ' ')
      .toLocaleLowerCase('es')
  )
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return (
        'Tu sesión no es válida. '
        + 'Inicia sesión nuevamente.'
      )
    }

    if (error.status === 403) {
      return (
        'No tienes permiso para consultar '
        + 'el historial de stock.'
      )
    }

    if (error.status === 422) {
      return (
        'Revisa el periodo de fechas '
        + 'e intenta nuevamente.'
      )
    }

    return error.message
  }

  return (
    'No pudimos consultar el historial de stock. '
    + 'Intenta nuevamente.'
  )
}

export default function InventoryMovementHistory({
  inventoryRecords,
}: InventoryMovementHistoryProps) {
  const [movements, setMovements] = useState<
    InventoryMovement[]
  >([])

  const [inventoryId, setInventoryId] = useState('')
  const [movementType, setMovementType] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadMovements(
    filters: {
      inventoryId: string
      movementType: string
      startDate: string
      endDate: string
    },
  ): Promise<void> {
    if (
      filters.startDate
      && filters.endDate
      && filters.startDate > filters.endDate
    ) {
      setError(
        'La fecha inicial no puede ser posterior '
        + 'a la fecha final.',
      )
      return
    }

    setLoading(true)
    setError('')

    try {
      const records = await listInventoryMovements({
        inventoryId:
          filters.inventoryId || undefined,
        movementType:
          filters.movementType || undefined,
        startDate:
          filters.startDate || undefined,
        endDate:
          filters.endDate || undefined,
      })

      setMovements(records)
    } catch (cause: unknown) {
      setError(getErrorMessage(cause))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadMovements({
      inventoryId: '',
      movementType: '',
      startDate: '',
      endDate: '',
    })
  }, [])

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()

    await loadMovements({
      inventoryId,
      movementType,
      startDate,
      endDate,
    })
  }

  async function handleClearFilters(): Promise<void> {
    setInventoryId('')
    setMovementType('')
    setStartDate('')
    setEndDate('')
    setError('')

    await loadMovements({
      inventoryId: '',
      movementType: '',
      startDate: '',
      endDate: '',
    })
  }

  const filtersChanged = (
    inventoryId !== ''
    || movementType !== ''
    || startDate !== ''
    || endDate !== ''
  )

  return (
    <section
      className="movement-panel"
      aria-labelledby="movement-title"
    >
      <div className="monitoring-panel-heading">
        <div>
          <p className="eyebrow">
            HISTORIAL DEL INVENTARIO
          </p>

          <h2 id="movement-title">
            Historial de movimientos de stock
          </h2>

          <p>
            Consulta cuándo aumentó, disminuyó o se reservó
            el stock de un producto.
          </p>
        </div>

        <span className="inventory-result-count">
          {movements.length}{' '}
          {movements.length === 1
            ? 'movimiento'
            : 'movimientos'}
        </span>
      </div>

      <form
        className="movement-filters"
        onSubmit={(event) => {
          void handleSubmit(event)
        }}
      >
        <div className="monitoring-field">
          <label htmlFor="movement-inventory">
            Producto y sucursal
          </label>

          <select
            id="movement-inventory"
            value={inventoryId}
            onChange={(event) => {
              setInventoryId(event.target.value)
              setError('')
            }}
          >
            <option value="">
              Todos los productos y sucursales
            </option>

            {inventoryRecords.map((record) => (
              <option
                key={record.id}
                value={record.id}
              >
                {record.product_name}
                {' · '}
                {record.branch_name}
              </option>
            ))}
          </select>
        </div>

        <div className="monitoring-field">
          <label htmlFor="movement-type">
            Tipo de cambio
          </label>

          <select
            id="movement-type"
            value={movementType}
            onChange={(event) => {
              setMovementType(event.target.value)
              setError('')
            }}
          >
            <option value="">
              Todos los cambios
            </option>

            <option value="SALDO_INICIAL">
              Registro inicial
            </option>

            <option value="ENTRADA">
              Entrada de unidades
            </option>

            <option value="SALIDA">
              Salida de unidades
            </option>

            <option value="RESERVA">
              Reserva de unidades
            </option>

            <option value="LIBERACION_RESERVA">
              Liberación de reserva
            </option>

            <option value="AJUSTE">
              Ajuste de inventario
            </option>

            <option value="TRANSFERENCIA_SALIDA">
              Transferencia enviada
            </option>

            <option value="TRANSFERENCIA_ENTRADA">
              Transferencia recibida
            </option>

            <option value="VENTA">
              Venta
            </option>

            <option value="RECEPCION">
              Recepción de productos
            </option>
          </select>
        </div>

        <div className="monitoring-field">
          <label htmlFor="movement-start-date">
            Desde
          </label>

          <input
            id="movement-start-date"
            type="date"
            value={startDate}
            max={endDate || undefined}
            onChange={(event) => {
              setStartDate(event.target.value)
              setError('')
            }}
          />
        </div>

        <div className="monitoring-field">
          <label htmlFor="movement-end-date">
            Hasta
          </label>

          <input
            id="movement-end-date"
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(event) => {
              setEndDate(event.target.value)
              setError('')
            }}
          />
        </div>

        <button
          type="submit"
          className="monitoring-submit-button"
          disabled={loading}
        >
          {loading
            ? 'Consultando…'
            : 'Consultar historial'}
        </button>

        <button
          type="button"
          className="clear-button"
          disabled={loading || !filtersChanged}
          onClick={() => {
            void handleClearFilters()
          }}
        >
          Limpiar filtros
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

      {loading ? (
        <p
          className="monitoring-loading"
          role="status"
        >
          Consultando el historial de stock…
        </p>
      ) : (
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Historial de movimientos de stock"
        >
          <table className="monitoring-table">
            <caption className="sr-only">
              Historial de movimientos del inventario
            </caption>

            <thead>
              <tr>
                <th scope="col">
                  Fecha y hora
                </th>

                <th scope="col">
                  Producto
                </th>

                <th scope="col">
                  Sucursal
                </th>

                <th scope="col">
                  Tipo de cambio
                </th>

                <th
                  scope="col"
                  className="numeric"
                >
                  Cambio físico
                </th>

                <th
                  scope="col"
                  className="numeric"
                >
                  Cambio reservado
                </th>

                <th scope="col">
                  Disponible antes y después
                </th>

                <th scope="col">
                  Realizado por
                </th>
              </tr>
            </thead>

            <tbody>
              {movements.map((movement) => (
                <tr key={movement.id}>
                  <td>
                    {formatDateTime(
                      movement.created_at,
                    )}
                  </td>

                  <th scope="row">
                    <span className="product-name">
                      {movement.product_name}
                    </span>

                    <span className="product-detail">
                      SKU: {movement.product_sku}
                    </span>
                  </th>

                  <td>
                    <span className="branch-label">
                      {movement.branch_name}{' '}
                      ({movement.branch_code})
                    </span>
                  </td>

                  <td>
                    <span className="movement-type">
                      {movementTypeLabel(
                        movement.movement_type,
                      )}
                    </span>
                  </td>

                  <td className="numeric">
                    {signedQuantity(
                      movement.physical_change,
                    )}
                  </td>

                  <td className="numeric">
                    {signedQuantity(
                      movement.reserved_change,
                    )}
                  </td>

                  <td>
                    {movement.available_before}
                    {' → '}
                    {movement.available_after}
                  </td>

                  <td>
                    {movement.user_name
                      ?? 'Actualización automática'}
                  </td>
                </tr>
              ))}

              {movements.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="empty-state"
                  >
                    <strong>
                      Todavía no hay movimientos de stock.
                    </strong>

                    <span className="empty-state-detail">
                      Los movimientos aparecerán cuando se
                      realicen recepciones, ventas, reservas,
                      transferencias o ajustes de inventario.
                    </span>
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