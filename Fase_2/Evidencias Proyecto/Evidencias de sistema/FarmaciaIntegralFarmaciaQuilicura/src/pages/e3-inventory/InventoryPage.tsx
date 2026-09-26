import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '../../services/http'
import {
  listInventory,
  type InventoryRecord,
} from './inventory.api'
import InventoryTable from './InventoryTable'
import './InventoryPage.css'

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es')
}

export default function InventoryPage() {
  const navigate = useNavigate()

  const [inventoryRecords, setInventoryRecords] = useState<
    InventoryRecord[]
  >([])
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

        if (cause instanceof ApiError && cause.status === 401) {
          navigate('/login', { replace: true })
          return
        }

        if (cause instanceof ApiError && cause.status === 403) {
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

    return [...unique.values()].sort((first, second) =>
      first.name.localeCompare(second.name, 'es'),
    )
  }, [inventoryRecords])

  const records = useMemo(() => {
    const search = normalize(query.trim())

    return inventoryRecords.filter((record) => {
      const matchesBranch = (
        !branchId || record.branch_id === branchId
      )

      const searchable = normalize(
        [
          record.product_name,
          record.product_sku,
          record.branch_name,
          record.branch_code,
        ].join(' '),
      )

      const matchesSearch = (
        !search || searchable.includes(search)
      )

      return matchesBranch && matchesSearch
    })
  }, [branchId, inventoryRecords, query])

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
        <p className="users-error" role="alert">
          {error}
        </p>

        <button
          type="button"
          className="clear-button"
          onClick={() => window.location.reload()}
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
              INVENTARIO / CONSULTA DE STOCK
            </p>

            <h1>Stock por sucursal</h1>

            <p className="inventory-description">
              Consulta las existencias y su disponibilidad en cada
              sucursal.
            </p>
          </div>

          <div className="inventory-statuses">
            <span className="read-only">
              Solo consulta
            </span>

            <span className="inventory-updated">
              Datos actualizados
            </span>
          </div>
        </div>

        <div className="inventory-notice">
          <span aria-hidden="true">ⓘ</span>

          <p>
            Las cantidades mostradas corresponden al inventario
            registrado en el sistema.
          </p>
        </div>

        <section
          className="stock-guide"
          aria-label="Cómo se interpreta el stock"
        >
          <div>
            <span className="guide-number">01</span>
            <h2>Stock físico</h2>

            <p>
              Unidades presentes en la sucursal.
            </p>
          </div>

          <div>
            <span className="guide-number">02</span>
            <h2>Stock reservado</h2>

            <p>
              Unidades comprometidas que aún no han salido.
            </p>
          </div>

          <div className="available-guide">
            <span className="guide-number">03</span>
            <h2>Stock disponible</h2>

            <p>
              Stock físico menos stock reservado.
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
                Existencias por producto
              </h2>

              <p>
                Las cantidades se expresan en unidades.
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
                Buscar producto
              </label>

              <input
                id="product-search"
                type="search"
                placeholder="Nombre, SKU, sucursal o código"
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

          <InventoryTable records={records} />

          <div className="table-footer">
            <span role="status">
              {records.length} de {inventoryRecords.length}{' '}
              {inventoryRecords.length === 1
                ? 'registro'
                : 'registros'}
            </span>

            <span>
              Disponible = físico − reservado
            </span>
          </div>
        </section>

        <footer className="inventory-footer">
          <span>
            Sistema Integral de Gestión para Farmacia Quilicura
          </span>

          <span>
            Consulta de inventario multisucursal
          </span>
        </footer>
      </main>
    </div>
  )
}
