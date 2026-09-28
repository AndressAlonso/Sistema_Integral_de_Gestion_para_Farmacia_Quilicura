import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { ApiError } from '../../services/http'
import {
  type AlertLevel,
  type InventoryLot,
  type InventoryRecord,
  listInventoryLots,
} from './inventory.api'

interface ExpirationAlertsPanelProps {
  inventoryRecords: InventoryRecord[]
}

type ExpirationPeriod =
  | 'ALL'
  | '90'
  | '180'
  | '365'
  | '730'
  | 'EXPIRED'

type ExpirationStatusFilter =
  | 'ALL'
  | AlertLevel

interface LotExpirationView {
  lot: InventoryLot
  daysRemaining: number
  alertLevel: AlertLevel
}

function isExpirationPeriod(
  value: string,
): value is ExpirationPeriod {
  return [
    'ALL',
    '90',
    '180',
    '365',
    '730',
    'EXPIRED',
  ].includes(value)
}

function isExpirationStatusFilter(
  value: string,
): value is ExpirationStatusFilter {
  return [
    'ALL',
    'VENCIDO',
    'CRITICO',
    'PROXIMO',
    'SEGUIMIENTO',
  ].includes(value)
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
}

function todayAsUtc(): number {
  const today = new Date()

  return Date.UTC(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  )
}

function dateAsUtc(value: string): number {
  const parts = value
    .split('-')
    .map(Number)

  const year = parts[0]
  const month = parts[1]
  const day = parts[2]

  return Date.UTC(
    year,
    month - 1,
    day,
  )
}

function calculateDaysRemaining(
  expirationDate: string,
): number {
  const millisecondsPerDay = (
    24 * 60 * 60 * 1000
  )

  return Math.round(
    (
      dateAsUtc(expirationDate)
      - todayAsUtc()
    ) / millisecondsPerDay,
  )
}

function classifyExpiration(
  daysRemaining: number,
): AlertLevel {
  if (daysRemaining < 0) {
    return 'VENCIDO'
  }

  if (daysRemaining <= 30) {
    return 'CRITICO'
  }

  if (daysRemaining <= 60) {
    return 'PROXIMO'
  }

  return 'SEGUIMIENTO'
}

function alertLabel(level: AlertLevel): string {
  if (level === 'VENCIDO') {
    return 'Vencido'
  }

  if (level === 'CRITICO') {
    return 'Vence muy pronto'
  }

  if (level === 'PROXIMO') {
    return 'Próximo a vencer'
  }

  return 'Vencimiento lejano'
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
    `${days} `
    + `${days === 1 ? 'día restante' : 'días restantes'}`
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
        + 'las fechas de vencimiento.'
      )
    }

    if (error.status === 422) {
      return (
        'Revisa los filtros seleccionados '
        + 'e intenta nuevamente.'
      )
    }

    return error.message
  }

  return (
    'No pudimos consultar las fechas de vencimiento. '
    + 'Intenta nuevamente.'
  )
}

function matchesPeriod(
  daysRemaining: number,
  period: ExpirationPeriod,
): boolean {
  if (period === 'ALL') {
    return true
  }

  if (period === 'EXPIRED') {
    return daysRemaining < 0
  }

  const maximumDays = Number(period)

  return (
    daysRemaining >= 0
    && daysRemaining <= maximumDays
  )
}

export default function ExpirationAlertsPanel({
  inventoryRecords,
}: ExpirationAlertsPanelProps) {
  const [lots, setLots] = useState<
    InventoryLot[]
  >([])

  const [productId, setProductId] = useState('')
  const [branchId, setBranchId] = useState('')

  const [period, setPeriod] =
    useState<ExpirationPeriod>('ALL')

  const [statusFilter, setStatusFilter] =
    useState<ExpirationStatusFilter>('ALL')

  const [appliedProductId, setAppliedProductId] =
    useState('')

  const [appliedBranchId, setAppliedBranchId] =
    useState('')

  const [appliedPeriod, setAppliedPeriod] =
    useState<ExpirationPeriod>('ALL')

  const [
    appliedStatusFilter,
    setAppliedStatusFilter,
  ] = useState<ExpirationStatusFilter>('ALL')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const branches = useMemo(() => {
    const uniqueBranches = new Map<
      string,
      {
        id: string
        name: string
        code: string
      }
    >()

    inventoryRecords.forEach((record) => {
      uniqueBranches.set(record.branch_id, {
        id: record.branch_id,
        name: record.branch_name,
        code: record.branch_code,
      })
    })

    return [...uniqueBranches.values()].sort(
      (first, second) =>
        first.name.localeCompare(
          second.name,
          'es',
        ),
    )
  }, [inventoryRecords])

  const products = useMemo(() => {
    const uniqueProducts = new Map<
      string,
      {
        id: string
        name: string
        sku: string
      }
    >()

    inventoryRecords.forEach((record) => {
      uniqueProducts.set(record.product_id, {
        id: record.product_id,
        name: record.product_name,
        sku: record.product_sku,
      })
    })

    return [...uniqueProducts.values()].sort(
      (first, second) =>
        first.name.localeCompare(
          second.name,
          'es',
        ),
    )
  }, [inventoryRecords])

  const lotsWithExpiration = useMemo<
    LotExpirationView[]
  >(
    () =>
      lots
        .filter(
          (lot) =>
            lot.is_active
            && lot.quantity > 0,
        )
        .map((lot) => {
          const daysRemaining =
            calculateDaysRemaining(
              lot.expiration_date,
            )

          return {
            lot,
            daysRemaining,
            alertLevel:
              classifyExpiration(daysRemaining),
          }
        })
        .sort(
          (first, second) =>
            first.lot.expiration_date.localeCompare(
              second.lot.expiration_date,
            ),
        ),
    [lots],
  )

  const filteredLots = useMemo(
    () =>
      lotsWithExpiration.filter((item) => {
        const matchesProduct = (
          !appliedProductId
          || item.lot.product_id
            === appliedProductId
        )

        const matchesBranch = (
          !appliedBranchId
          || item.lot.branch_id
            === appliedBranchId
        )

        const periodMatches = matchesPeriod(
          item.daysRemaining,
          appliedPeriod,
        )

        const statusMatches = (
          appliedStatusFilter === 'ALL'
          || item.alertLevel
            === appliedStatusFilter
        )

        return (
          matchesProduct
          && matchesBranch
          && periodMatches
          && statusMatches
        )
      }),
    [
      appliedBranchId,
      appliedPeriod,
      appliedProductId,
      appliedStatusFilter,
      lotsWithExpiration,
    ],
  )

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

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): void {
    event.preventDefault()

    setAppliedProductId(productId)
    setAppliedBranchId(branchId)
    setAppliedPeriod(period)
    setAppliedStatusFilter(statusFilter)
    setError('')
  }

  function handleClearFilters(): void {
    setProductId('')
    setBranchId('')
    setPeriod('ALL')
    setStatusFilter('ALL')

    setAppliedProductId('')
    setAppliedBranchId('')
    setAppliedPeriod('ALL')
    setAppliedStatusFilter('ALL')

    setError('')
  }

  const filtersChanged = (
    productId !== ''
    || branchId !== ''
    || period !== 'ALL'
    || statusFilter !== 'ALL'
  )

  const showingExpiredOnly = (
    appliedStatusFilter === 'VENCIDO'
    || appliedPeriod === 'EXPIRED'
  )

  return (
    <section
      className="expiration-panel"
      aria-labelledby="expiration-title"
    >
      <div className="monitoring-panel-heading">
        <div>
          <p className="eyebrow">
            CONTROL DE VENCIMIENTOS
          </p>

          <h2 id="expiration-title">
            Fechas de vencimiento de los lotes
          </h2>

          <p>
            Revisa todos los lotes registrados y utiliza
            los filtros para encontrar vencimientos
            específicos.
          </p>
        </div>

        <span className="inventory-result-count">
          {filteredLots.length === 0
            ? 'Sin resultados'
            : (
              `${filteredLots.length} ${
                filteredLots.length === 1
                  ? 'lote encontrado'
                  : 'lotes encontrados'
              }`
            )}
        </span>
      </div>

      <form
        className="expiration-filters"
        onSubmit={handleSubmit}
      >
        <div className="monitoring-field">
          <label htmlFor="expiration-product">
            Producto
          </label>

          <select
            id="expiration-product"
            value={productId}
            onChange={(event) => {
              setProductId(event.target.value)
              setError('')
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
          <label htmlFor="expiration-branch">
            Sucursal
          </label>

          <select
            id="expiration-branch"
            value={branchId}
            onChange={(event) => {
              setBranchId(event.target.value)
              setError('')
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
          <label htmlFor="expiration-period">
            Periodo de vencimiento
          </label>

          <select
            id="expiration-period"
            value={period}
            onChange={(event) => {
              const value = event.target.value

              if (isExpirationPeriod(value)) {
                setPeriod(value)
              }

              setError('')
            }}
          >
            <option value="ALL">
              Todos los vencimientos
            </option>

            <option value="90">
              Próximos 3 meses
            </option>

            <option value="180">
              Próximos 6 meses
            </option>

            <option value="365">
              Próximo año
            </option>

            <option value="730">
              Próximos 2 años
            </option>

            <option value="EXPIRED">
              Solo lotes vencidos
            </option>
          </select>
        </div>

        <div className="monitoring-field">
          <label htmlFor="expiration-status">
            Estado del vencimiento
          </label>

          <select
            id="expiration-status"
            value={statusFilter}
            onChange={(event) => {
              const value = event.target.value

              if (
                isExpirationStatusFilter(value)
              ) {
                setStatusFilter(value)
              }

              setError('')
            }}
          >
            <option value="ALL">
              Todos los estados
            </option>

            <option value="VENCIDO">
              Vencidos
            </option>

            <option value="CRITICO">
              Vencen muy pronto (0 a 30 días)
            </option>

            <option value="PROXIMO">
              Próximos a vencer (31 a 60 días)
            </option>

            <option value="SEGUIMIENTO">
              Vencimiento lejano (más de 60 días)
            </option>
          </select>
        </div>

        <button
          type="submit"
          className="monitoring-submit-button"
          disabled={loading}
        >
          Aplicar filtros
        </button>

        <button
          type="button"
          className="clear-button"
          disabled={loading || !filtersChanged}
          onClick={handleClearFilters}
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
          Cargando fechas de vencimiento…
        </p>
      ) : (
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label={
            'Fechas de vencimiento de los lotes'
          }
        >
          <table className="monitoring-table">
            <caption className="sr-only">
              Fechas de vencimiento de todos los lotes
            </caption>

            <thead>
              <tr>
                <th scope="col">
                  Producto
                </th>

                <th scope="col">
                  Sucursal
                </th>

                <th scope="col">
                  Lote
                </th>

                <th scope="col">
                  Fecha de vencimiento
                </th>

                <th scope="col">
                  Tiempo restante
                </th>

                <th
                  scope="col"
                  className="numeric"
                >
                  Unidades
                </th>

                <th scope="col">
                  Estado
                </th>
              </tr>
            </thead>

            <tbody>
              {filteredLots.map((item) => (
                <tr key={item.lot.id}>
                  <th scope="row">
                    <span className="product-name">
                      {item.lot.product_name}
                    </span>

                    <span className="product-detail">
                      SKU: {item.lot.product_sku}
                    </span>
                  </th>

                  <td>
                    <span className="branch-label">
                      {item.lot.branch_name}{' '}
                      ({item.lot.branch_code})
                    </span>
                  </td>

                  <td>
                    <span className="lot-number">
                      {item.lot.lot_number}
                    </span>
                  </td>

                  <td>
                    {formatDate(
                      item.lot.expiration_date,
                    )}
                  </td>

                  <td>
                    {daysRemainingLabel(
                      item.daysRemaining,
                    )}
                  </td>

                  <td className="numeric">
                    {item.lot.quantity}
                  </td>

                  <td>
                    <span
                      className={alertClass(
                        item.alertLevel,
                      )}
                    >
                      {alertLabel(
                        item.alertLevel,
                      )}
                    </span>
                  </td>
                </tr>
              ))}

              {filteredLots.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="empty-state"
                  >
                    <span
                      className="empty-state-icon"
                      aria-hidden="true"
                    >
                      ✓
                    </span>

                    <strong>
                      {showingExpiredOnly
                        ? 'No hay lotes vencidos.'
                        : (
                          'No encontramos lotes '
                          + 'con estos filtros.'
                        )}
                    </strong>

                    <span className="empty-state-detail">
                      {showingExpiredOnly
                        ? (
                          'Actualmente no existen lotes '
                          + 'que requieran revisión por '
                          + 'vencimiento.'
                        )
                        : (
                          'Puedes cambiar el producto, '
                          + 'la sucursal, el periodo o '
                          + 'el estado para ampliar '
                          + 'la búsqueda.'
                        )}
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