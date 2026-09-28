import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { ApiError } from '../../services/http'
import {
  type AlertLevel,
  type ExpirationAlert,
  type InventoryMovement,
  type InventoryRecord,
  listExpirationAlerts,
  listInventoryMovements,
} from './inventory.api'

interface InventoryMonitoringPanelProps {
  inventoryRecords: InventoryRecord[]
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
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

function alertLabel(level: AlertLevel): string {
  if (level === 'VENCIDO') {
    return 'Vencido'
  }

  if (level === 'CRITICO') {
    return 'Crítico'
  }

  if (level === 'PROXIMO') {
    return 'Próximo'
  }

  return 'Seguimiento'
}

function alertClass(level: AlertLevel): string {
  return (
    `expiration-status expiration-status-${level.toLowerCase()}`
  )
}

function daysRemainingLabel(days: number): string {
  if (days < 0) {
    const expiredDays = Math.abs(days)

    return (
      `Vencido hace ${expiredDays} `
      + `${expiredDays === 1 ? 'día' : 'días'}`
    )
  }

  if (days === 0) {
    return 'Vence hoy'
  }

  return (
    `${days} ${days === 1 ? 'día' : 'días'}`
  )
}

function signedQuantity(value: number): string {
  if (value > 0) {
    return `+${value}`
  }

  return String(value)
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
        + 'movimientos y alertas.'
      )
    }

    if (error.status === 422) {
      return (
        'Revisa el rango de fechas o '
        + 'el horizonte seleccionado.'
      )
    }

    return error.message
  }

  return 'No pudimos cargar la información de seguimiento.'
}

export default function InventoryMonitoringPanel({
  inventoryRecords,
}: InventoryMonitoringPanelProps) {
  const [movements, setMovements] = useState<
    InventoryMovement[]
  >([])

  const [alerts, setAlerts] = useState<
    ExpirationAlert[]
  >([])

  const [inventoryId, setInventoryId] = useState('')
  const [branchId, setBranchId] = useState('')
  const [productId, setProductId] = useState('')
  const [movementType, setMovementType] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const [alertDays, setAlertDays] = useState(90)
  const [includeExpired, setIncludeExpired] =
    useState(true)

  const [loadingMovements, setLoadingMovements] =
    useState(true)

  const [loadingAlerts, setLoadingAlerts] =
    useState(true)

  const [movementError, setMovementError] =
    useState('')

  const [alertError, setAlertError] = useState('')

  const branches = useMemo(() => {
    const unique = new Map<
      string,
      {
        id: string
        name: string
        code: string
      }
    >()

    inventoryRecords.forEach((record) => {
      unique.set(record.branch_id, {
        id: record.branch_id,
        name: record.branch_name,
        code: record.branch_code,
      })
    })

    return [...unique.values()].sort(
      (first, second) =>
        first.name.localeCompare(
          second.name,
          'es',
        ),
    )
  }, [inventoryRecords])

  const products = useMemo(() => {
    const unique = new Map<
      string,
      {
        id: string
        name: string
        sku: string
      }
    >()

    inventoryRecords.forEach((record) => {
      unique.set(record.product_id, {
        id: record.product_id,
        name: record.product_name,
        sku: record.product_sku,
      })
    })

    return [...unique.values()].sort(
      (first, second) =>
        first.name.localeCompare(
          second.name,
          'es',
        ),
    )
  }, [inventoryRecords])

  async function loadMovements(): Promise<void> {
    if (
      startDate
      && endDate
      && startDate > endDate
    ) {
      setMovementError(
        'La fecha inicial no puede ser posterior '
        + 'a la fecha final.',
      )
      return
    }

    setLoadingMovements(true)
    setMovementError('')

    try {
      const records = await listInventoryMovements({
        inventoryId: inventoryId || undefined,
        productId: productId || undefined,
        branchId: branchId || undefined,
        movementType: movementType || undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      })

      setMovements(records)
    } catch (cause: unknown) {
      setMovementError(
        getErrorMessage(cause),
      )
    } finally {
      setLoadingMovements(false)
    }
  }

  async function loadAlerts(): Promise<void> {
    setLoadingAlerts(true)
    setAlertError('')

    try {
      const response = await listExpirationAlerts({
        days: alertDays,
        includeExpired,
        productId: productId || undefined,
        branchId: branchId || undefined,
      })

      setAlerts(response.alerts)
    } catch (cause: unknown) {
      setAlertError(
        getErrorMessage(cause),
      )
    } finally {
      setLoadingAlerts(false)
    }
  }

  useEffect(() => {
    void loadMovements()
  }, [])

  useEffect(() => {
    void loadAlerts()
  }, [])

  async function handleMovementFilters(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()
    await loadMovements()
  }

  async function handleAlertFilters(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault()
    await loadAlerts()
  }

  function clearMovementFilters(): void {
    setInventoryId('')
    setMovementType('')
    setStartDate('')
    setEndDate('')
    setMovementError('')
  }

  return (
    <section
      className="monitoring-section"
      aria-labelledby="monitoring-title"
    >
      <div className="monitoring-heading">
        <div>
          <p className="eyebrow">
            INVENTARIO / SEGUIMIENTO
          </p>

          <h2 id="monitoring-title">
            Movimientos y alertas de vencimiento
          </h2>

          <p>
            Consulta el kardex de inventario y los lotes
            que requieren seguimiento por vencimiento.
          </p>
        </div>
      </div>

      <div className="monitoring-grid">
        <section
          className="expiration-panel"
          aria-labelledby="expiration-title"
        >
          <div className="monitoring-panel-heading">
            <div>
              <h3 id="expiration-title">
                Alertas de vencimiento
              </h3>

              <p>
                Lotes activos dentro del horizonte
                seleccionado.
              </p>
            </div>

            <span className="inventory-result-count">
              {alerts.length}{' '}
              {alerts.length === 1
                ? 'alerta'
                : 'alertas'}
            </span>
          </div>

          <form
            className="monitoring-filters"
            onSubmit={(event) => {
              void handleAlertFilters(event)
            }}
          >
            <div className="monitoring-field">
              <label htmlFor="alert-product">
                Producto
              </label>

              <select
                id="alert-product"
                value={productId}
                onChange={(event) => {
                  setProductId(event.target.value)
                }}
              >
                <option value="">
                  Todos los productos
                </option>

                {products.map((product) => (
                  <option
                    key={product.id}
                    value={product.id}
                  >
                    {product.name} ({product.sku})
                  </option>
                ))}
              </select>
            </div>

            <div className="monitoring-field">
              <label htmlFor="alert-branch">
                Sucursal
              </label>

              <select
                id="alert-branch"
                value={branchId}
                onChange={(event) => {
                  setBranchId(event.target.value)
                }}
              >
                <option value="">
                  Todas las sucursales
                </option>

                {branches.map((branch) => (
                  <option
                    key={branch.id}
                    value={branch.id}
                  >
                    {branch.name} ({branch.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="monitoring-field">
              <label htmlFor="alert-days">
                Horizonte
              </label>

              <select
                id="alert-days"
                value={alertDays}
                onChange={(event) => {
                  setAlertDays(
                    Number(event.target.value),
                  )
                }}
              >
                <option value={90}>
                  90 días
                </option>

                <option value={180}>
                  180 días
                </option>

                <option value={365}>
                  365 días
                </option>

                <option value={730}>
                  730 días
                </option>
              </select>
            </div>

            <label className="expired-checkbox">
              <input
                type="checkbox"
                checked={includeExpired}
                onChange={(event) => {
                  setIncludeExpired(
                    event.target.checked,
                  )
                }}
              />

              Incluir vencidos
            </label>

            <button
              type="submit"
              className="monitoring-submit-button"
              disabled={loadingAlerts}
            >
              {loadingAlerts
                ? 'Consultando…'
                : 'Consultar alertas'}
            </button>
          </form>

          {alertError && (
            <p
              className="lot-message lot-error"
              role="alert"
            >
              {alertError}
            </p>
          )}

          {loadingAlerts ? (
            <p
              className="monitoring-loading"
              role="status"
            >
              Cargando alertas…
            </p>
          ) : (
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Alertas de vencimiento"
            >
              <table className="monitoring-table">
                <caption className="sr-only">
                  Lotes próximos a vencer o vencidos
                </caption>

                <thead>
                  <tr>
                    <th scope="col">Producto</th>
                    <th scope="col">Sucursal</th>
                    <th scope="col">Lote</th>
                    <th scope="col">Vencimiento</th>
                    <th scope="col">Plazo</th>

                    <th
                      scope="col"
                      className="numeric"
                    >
                      Cantidad
                    </th>

                    <th scope="col">Nivel</th>
                  </tr>
                </thead>

                <tbody>
                  {alerts.map((alert) => (
                    <tr key={alert.lot_id}>
                      <th scope="row">
                        <span className="product-name">
                          {alert.product_name}
                        </span>

                        <span className="product-detail">
                          SKU: {alert.product_sku}
                        </span>
                      </th>

                      <td>
                        <span className="branch-label">
                          {alert.branch_name}{' '}
                          ({alert.branch_code})
                        </span>
                      </td>

                      <td>
                        <span className="lot-number">
                          {alert.lot_number}
                        </span>
                      </td>

                      <td>
                        {formatDate(
                          alert.expiration_date,
                        )}
                      </td>

                      <td>
                        {daysRemainingLabel(
                          alert.days_remaining,
                        )}
                      </td>

                      <td className="numeric">
                        {alert.quantity}
                      </td>

                      <td>
                        <span
                          className={alertClass(
                            alert.alert_level,
                          )}
                        >
                          {alertLabel(
                            alert.alert_level,
                          )}
                        </span>
                      </td>
                    </tr>
                  ))}

                  {alerts.length === 0 && (
                    <tr>
                      <td
                        colSpan={7}
                        className="empty-state"
                      >
                        No hay lotes dentro del horizonte
                        seleccionado.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section
          className="movement-panel"
          aria-labelledby="movement-title"
        >
          <div className="monitoring-panel-heading">
            <div>
              <h3 id="movement-title">
                Kardex de inventario
              </h3>

              <p>
                Historial cronológico de cambios físicos
                y reservas de stock.
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
              void handleMovementFilters(event)
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
                  setInventoryId(
                    event.target.value,
                  )
                }}
              >
                <option value="">
                  Todo el inventario
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
                Tipo
              </label>

              <input
                id="movement-type"
                type="text"
                maxLength={50}
                placeholder="Ej.: ENTRADA"
                value={movementType}
                onChange={(event) => {
                  setMovementType(
                    event.target.value,
                  )
                }}
              />
            </div>

            <div className="monitoring-field">
              <label htmlFor="movement-start-date">
                Desde
              </label>

              <input
                id="movement-start-date"
                type="date"
                value={startDate}
                onChange={(event) => {
                  setStartDate(event.target.value)
                  setMovementError('')
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
                onChange={(event) => {
                  setEndDate(event.target.value)
                  setMovementError('')
                }}
              />
            </div>

            <button
              type="submit"
              className="monitoring-submit-button"
              disabled={loadingMovements}
            >
              {loadingMovements
                ? 'Consultando…'
                : 'Consultar kardex'}
            </button>

            <button
              type="button"
              className="clear-button"
              onClick={clearMovementFilters}
              disabled={
                !inventoryId
                && !movementType
                && !startDate
                && !endDate
              }
            >
              Limpiar
            </button>
          </form>

          {movementError && (
            <p
              className="lot-message lot-error"
              role="alert"
            >
              {movementError}
            </p>
          )}

          {loadingMovements ? (
            <p
              className="monitoring-loading"
              role="status"
            >
              Cargando movimientos…
            </p>
          ) : (
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Kardex de inventario"
            >
              <table className="monitoring-table">
                <caption className="sr-only">
                  Movimientos cronológicos del inventario
                </caption>

                <thead>
                  <tr>
                    <th scope="col">Fecha</th>
                    <th scope="col">Producto</th>
                    <th scope="col">Sucursal</th>
                    <th scope="col">Tipo</th>

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
                      Disponible
                    </th>

                    <th scope="col">
                      Responsable
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
                          {movement.movement_type}
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
                          ?? 'Proceso del sistema'}
                      </td>
                    </tr>
                  ))}

                  {movements.length === 0 && (
                    <tr>
                      <td
                        colSpan={8}
                        className="empty-state"
                      >
                        No hay movimientos de inventario
                        registrados para esta consulta.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  )
}