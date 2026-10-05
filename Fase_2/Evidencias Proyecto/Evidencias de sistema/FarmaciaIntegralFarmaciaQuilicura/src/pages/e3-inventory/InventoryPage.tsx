import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '../../services/http'
import ExpirationAlertsPanel from './ExpirationAlertsPanel'
import InventoryMovementHistory from './InventoryMovementHistory'
import {
  listInventory,
  type InventoryRecord,
} from './inventory.api'
import InventoryTable from './InventoryTable'
import LotPanel from './LotPanel'
import './InventoryPage.css'

type InventoryTab =
  | 'availability'
  | 'lots'
  | 'expiration'
  | 'history'

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es')
}

export default function InventoryPage() {
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<
    InventoryTab
  >('availability')

  const [inventoryRecords, setInventoryRecords] =
    useState<InventoryRecord[]>([])

  const [branchId, setBranchId] = useState('')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    listInventory()
      .then((records) => {
        if (!active) {
          return
        }

        setInventoryRecords(records)
        setLoading(false)
      })
      .catch((cause: unknown) => {
        if (!active) {
          return
        }

        if (
          cause instanceof ApiError
          && cause.status === 401
        ) {
          navigate('/login', {
            replace: true,
          })
          return
        }

        if (
          cause instanceof ApiError
          && cause.status === 403
        ) {
          setError(
            'No tienes permiso para consultar el inventario.',
          )
          setLoading(false)
          return
        }

        setError(
          cause instanceof ApiError
            ? cause.message
            : 'No pudimos cargar el inventario.',
        )

        setLoading(false)
      })

    return () => {
      active = false
    }
  }, [navigate])

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

  const records = useMemo(() => {
    const search = normalize(query.trim())

    return inventoryRecords.filter((record) => {
      const matchesBranch = (
        !branchId
        || record.branch_id === branchId
      )

      const searchable = normalize(
        [
          record.product_name,
          record.product_sku,
          record.branch_name,
          record.branch_code,
          record.stock_status,
        ].join(' '),
      )

      const matchesSearch = (
        !search
        || searchable.includes(search)
      )

      return matchesBranch && matchesSearch
    })
  }, [
    branchId,
    inventoryRecords,
    query,
  ])

  function handleRecordUpdated(
    updatedRecord: InventoryRecord,
  ): void {
    setInventoryRecords((currentRecords) =>
      currentRecords.map((record) =>
        record.id === updatedRecord.id
          ? updatedRecord
          : record,
      ),
    )
  }

  function tabClass(tab: InventoryTab): string {
    return activeTab === tab
      ? 'inventory-tab inventory-tab-active'
      : 'inventory-tab'
  }

  if (loading) {
    return (
      <main className="inventory-main inventory-loading">
        <p role="status">
          Cargando inventario…
        </p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="inventory-main inventory-error">
        <p
          className="users-error"
          role="alert"
        >
          {error}
        </p>

        <button
          type="button"
          className="clear-button"
          onClick={() => {
            window.location.reload()
          }}
        >
          Reintentar
        </button>
      </main>
    )
  }

  return (
    <div className="inventory-app">
      <main className="inventory-main">
        <div className="inventory-title-row">
          <div>
            <p className="eyebrow">
              INVENTARIO
            </p>

            <h1>
              Control de productos por sucursal
            </h1>

            <p className="inventory-description">
              Consulta las unidades disponibles, administra
              los lotes y revisa próximos vencimientos e
              historial de stock.
            </p>
          </div>

          <div className="inventory-statuses">
            <span className="read-only">
              Consulta y trazabilidad
            </span>

            <span className="inventory-updated">
              Datos actualizados
            </span>
          </div>
        </div>

        <div className="inventory-notice">
          <span aria-hidden="true">
            ⓘ
          </span>

          <p>
            Selecciona una sección para revisar la
            disponibilidad, administrar lotes, consultar
            vencimientos o ver el historial del inventario.
          </p>
        </div>

        <nav
          className="inventory-tabs"
          aria-label="Secciones del inventario"
          role="tablist"
        >
          <button
            id="inventory-tab-availability"
            type="button"
            role="tab"
            className={tabClass('availability')}
            aria-selected={
              activeTab === 'availability'
            }
            aria-controls="inventory-panel-availability"
            onClick={() => {
              setActiveTab('availability')
            }}
          >
            Disponibilidad
          </button>

          <button
            id="inventory-tab-lots"
            type="button"
            role="tab"
            className={tabClass('lots')}
            aria-selected={activeTab === 'lots'}
            aria-controls="inventory-panel-lots"
            onClick={() => {
              setActiveTab('lots')
            }}
          >
            Lotes
          </button>

          <button
            id="inventory-tab-expiration"
            type="button"
            role="tab"
            className={tabClass('expiration')}
            aria-selected={
              activeTab === 'expiration'
            }
            aria-controls="inventory-panel-expiration"
            onClick={() => {
              setActiveTab('expiration')
            }}
          >
            Vencimientos
          </button>

          <button
            id="inventory-tab-history"
            type="button"
            role="tab"
            className={tabClass('history')}
            aria-selected={activeTab === 'history'}
            aria-controls="inventory-panel-history"
            onClick={() => {
              setActiveTab('history')
            }}
          >
            Historial
          </button>
        </nav>

        {activeTab === 'availability' && (
          <div
            id="inventory-panel-availability"
            className="inventory-tab-content"
            role="tabpanel"
            aria-labelledby="inventory-tab-availability"
          >
            <section
              className="stock-guide"
              aria-label="Cómo se interpreta el stock"
            >
              <div>
                <span className="guide-number">
                  01
                </span>

                <h2>
                  Stock físico
                </h2>

                <p>
                  Unidades que se encuentran físicamente
                  en la sucursal, incluidas las que ya
                  están reservadas.
                </p>
              </div>

              <div>
                <span className="guide-number">
                  02
                </span>

                <h2>
                  Stock reservado
                </h2>

                <p>
                  Unidades que aún están en la sucursal,
                  pero ya fueron apartadas para otras
                  operaciones.
                </p>
              </div>

              <div className="available-guide">
                <span className="guide-number">
                  03
                </span>

                <h2>
                  Stock disponible
                </h2>

                <p>
                  Unidades que pueden utilizarse en nuevas
                  operaciones. Se calcula restando las
                  unidades reservadas.
                </p>
              </div>
            </section>

            <section
              className="inventory-panel"
              aria-labelledby="results-title"
            >
              <div className="panel-heading">
                <div>
                  <h2 id="results-title">
                    Disponibilidad de productos
                  </h2>

                  <p>
                    Revisa las unidades físicas, reservadas
                    y disponibles de cada producto.
                  </p>
                </div>

                <span className="inventory-result-count">
                  {inventoryRecords.length}{' '}
                  {inventoryRecords.length === 1
                    ? 'registro'
                    : 'registros'}
                </span>
              </div>

              <div className="inventory-filters">
                <div className="search-field">
                  <label htmlFor="product-search">
                    Buscar en el inventario
                  </label>

                  <input
                    id="product-search"
                    type="search"
                    placeholder={
                      'Nombre, SKU, sucursal, '
                      + 'código o estado'
                    }
                    value={query}
                    onChange={(event) => {
                      setQuery(event.target.value)
                    }}
                  />
                </div>

                <div className="branch-field">
                  <label htmlFor="branch">
                    Sucursal
                  </label>

                  <select
                    id="branch"
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

                <button
                  type="button"
                  className="clear-button"
                  disabled={!branchId && !query}
                  onClick={() => {
                    setBranchId('')
                    setQuery('')
                  }}
                >
                  Limpiar filtros
                </button>
              </div>

              <InventoryTable
                records={records}
                onRecordUpdated={
                  handleRecordUpdated
                }
              />

              <div className="table-footer">
                <span role="status">
                  {records.length} de{' '}
                  {inventoryRecords.length}{' '}
                  {inventoryRecords.length === 1
                    ? 'registro'
                    : 'registros'}
                </span>

                <span>
                  Disponible = físico − reservado
                </span>
              </div>
            </section>
          </div>
        )}

        {activeTab === 'lots' && (
          <div
            id="inventory-panel-lots"
            className="inventory-tab-content"
            role="tabpanel"
            aria-labelledby="inventory-tab-lots"
          >
            <LotPanel
              inventoryRecords={inventoryRecords}
            />
          </div>
        )}

        {activeTab === 'expiration' && (
          <div
            id="inventory-panel-expiration"
            className="inventory-tab-content"
            role="tabpanel"
            aria-labelledby="inventory-tab-expiration"
          >
            <ExpirationAlertsPanel
              inventoryRecords={inventoryRecords}
            />
          </div>
        )}

        {activeTab === 'history' && (
          <div
            id="inventory-panel-history"
            className="inventory-tab-content"
            role="tabpanel"
            aria-labelledby="inventory-tab-history"
          >
            <InventoryMovementHistory
              inventoryRecords={inventoryRecords}
            />
          </div>
        )}

        <footer className="inventory-footer">
          <span>
            Sistema Integral de Gestión para Farmacia
            Quilicura
          </span>

          <span>
            Inventario multisucursal y trazabilidad
          </span>
        </footer>
      </main>
    </div>
  )
}