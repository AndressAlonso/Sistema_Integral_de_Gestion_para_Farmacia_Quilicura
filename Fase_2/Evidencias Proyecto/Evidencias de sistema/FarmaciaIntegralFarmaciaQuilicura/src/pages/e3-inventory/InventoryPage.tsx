import Notification from '../../components/Notification'
import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'

import { ApiError } from '../../services/http'
import ExpirationAlertsPanel from './ExpirationAlertsPanel'
import InventoryMovementHistory from './InventoryMovementHistory'
import {
  listInventory,
  type InventoryRecord,
} from './inventory.api'
import InventoryTable from './InventoryTable'
import LotPanel from './LotPanel'
import type { AuthSession } from '../e1-access-users-branches/auth/login.api'
import StockOperationDialog from '../e4-transfers/StockOperationDialog'
import '../e1-access-users-branches/users/users.css'
import '../e4-transfers/transfers.css'
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
  const [searchParams] = useSearchParams()
  const session = useOutletContext<AuthSession>()
  const [operation, setOperation] = useState<'receipt' | 'adjustment' | null>(null)
  const [revision, setRevision] = useState(0)
  const [message, setMessage] = useState('')
  const canReceive = session.user.permissions.includes('inventario.registrar_entrada')
  const canAdjust = session.user.permissions.includes('inventario.ajustar')
    && session.user.roles.some(role => ['ADMINISTRADOR', 'ENCARGADO_INVENTARIO'].includes(role))

  const [activeTab, setActiveTab] = useState<
    InventoryTab
  >(() => searchParams.get('tab') === 'lots' ? 'lots' : 'availability')

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
  }, [navigate, revision])

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
        <Notification message={error} kind="error" />

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
        <header className="inventory-title-row inventory-heading">
          <div>
            <p className="eyebrow">CONTROL DE EXISTENCIAS</p>
            <h1>Inventario</h1>
            <p className="inventory-description">Consulta cantidades por sucursal, revisa lotes y registra entradas o ajustes.</p>
          </div>
          <div className="inventory-heading-actions">
            {canAdjust && <button type="button" className="users-button" onClick={() => setOperation('adjustment')}>Ajustar inventario</button>}
            {canReceive && <button type="button" className="users-button primary" onClick={() => setOperation('receipt')}>+ Crear lotes / recibir mercadería</button>}
          </div>
        </header>
        {message && <Notification message={message} kind="success" />}

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
            <details className="inventory-stock-help">
              <summary>Disponible = físico − reservado <span>Ver explicación</span></summary>
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
                  Stock físico menos unidades reservadas.
                  Antes de una salida también se comprueba
                  que los lotes estén habilitados y no vencidos.
                </p>
              </div>
            </section>
            </details>

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

              <InventoryTable
                records={records}
                productFilter={<input type="search" aria-label="Buscar producto por nombre o SKU" placeholder="Nombre o SKU…" value={query} onChange={event => setQuery(event.target.value)} />}
                branchFilter={<div className="lot-branch-options" aria-label="Filtrar disponibilidad por sucursal">
                  <button type="button" aria-pressed={!branchId} onClick={() => setBranchId('')}>Todas</button>
                  {branches.map(branch => <button type="button" key={branch.id} aria-pressed={branchId === branch.id} onClick={() => setBranchId(branch.id)}>{branch.name}</button>)}
                </div>}
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
              targetLotId={searchParams.get('lot_id') ?? undefined}
              returnTransferId={searchParams.get('transfer_id') ?? undefined}
              key={revision}
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
              key={revision}
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
              key={revision}
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
        {operation && <StockOperationDialog userId={session.user.id} canReceive={canReceive}
          initialOperation={operation} onClose={() => setOperation(null)}
          onSaved={text => { setOperation(null); setMessage(text); setLoading(true); setError(''); setRevision(value => value + 1) }} />}
      </main>
    </div>
  )
}