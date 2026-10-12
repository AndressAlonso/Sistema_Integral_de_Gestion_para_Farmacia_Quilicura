import {
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { ApiError } from '../../services/http'
import {
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

function creationLabel(value: string): string {
  const created = new Date(value)
  if (!Number.isFinite(created.getTime())) return 'Fecha no disponible'
  const now = new Date()
  const day = (date: Date) => Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
  const days = Math.max(0, Math.round((day(now) - day(created)) / 86_400_000))
  if (days === 0) return 'Creado hoy'
  if (days === 1) return 'Creado ayer'
  if (days < 7) return 'Creado recientemente'
  return 'Creado hace ' + days + ' días'
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

    return error.message
  }

  return 'No pudimos completar la operación.'
}

export default function LotPanel({
  inventoryRecords,
}: LotPanelProps) {
  const [lots, setLots] = useState<InventoryLot[]>([])

  const [branchId, setBranchId] = useState('')
  const [priorityFirst, setPriorityFirst] = useState(true)
  const [productSearch, setProductSearch] = useState('')
  const search = useDeferredValue(productSearch)
  const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
  const branches = useMemo(() => {
    const values = new Map<string, string>()
    inventoryRecords.forEach(row => values.set(row.branch_id, row.branch_name))
    lots.forEach(row => values.set(row.branch_id, row.branch_name))
    return [...values].sort((a, b) => a[1].localeCompare(b[1]))
  }, [inventoryRecords, lots])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    listInventoryLots()
      .then(records => { if (active) setLots(records) })
      .catch(cause => { if (active) setError(getErrorMessage(cause)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
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

  const visibleLots = useMemo(
    () => lots
      .filter(lot => (!branchId || lot.branch_id === branchId) && normalize(lot.product_name + ' ' + lot.product_sku).includes(normalize(search)))
      .sort((a, b) =>
        (Number(firstFefoLotIds.has(b.id)) - Number(firstFefoLotIds.has(a.id))) * (priorityFirst ? 1 : -1)
        || a.expiration_date.localeCompare(b.expiration_date)
        || a.lot_number.localeCompare(b.lot_number)
        || a.id.localeCompare(b.id)),
    [lots, branchId, search, firstFefoLotIds, priorityFirst],
  )
  const inventoryIds = new Set(visibleLots.map(lot => lot.inventory_id))
  const selectedInventory = inventoryIds.size === 1
    ? inventoryRecords.find(record => inventoryIds.has(record.id)) : undefined
  const totalLotQuantity = visibleLots.reduce((total, lot) => total + lot.quantity, 0)
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
            Pulsa Estado para invertir la prioridad del listado;
            dentro de cada grupo, se ordenan por fecha de vencimiento.
          </p>
        </div>

        <span className="inventory-result-count">
          {visibleLots.length}{' '}
          {visibleLots.length === 1 ? 'lote' : 'lotes'}
        </span>
      </div>

      <div className="lot-toolbar"><div className="lot-entry-note"><p>Registra los lotes al recibir mercadería, con proveedor y documento de respaldo.</p>
      <span className="lot-cell-detail">Usa «Crear lotes / recibir mercadería» en la cabecera de Inventario.</span></div>
      </div>
      {error && (
        <p
          className="lot-message lot-error"
          role="alert"
        >
          {error}
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
                <th scope="col"><span>Código de lote / sucursal</span><div className="lot-branch-options" role="group" aria-label="Filtrar por sucursal"><button type="button" aria-pressed={!branchId} onClick={() => setBranchId('')}>Todas</button>{branches.map(([id, name]) => <button type="button" key={id} aria-pressed={branchId === id} onClick={() => setBranchId(id)}>{name}</button>)}</div></th>
                <th scope="col"><span>Producto</span><div className="lot-column-filter"><label className="sr-only" htmlFor="lot-product-search">Buscar lotes por nombre o SKU de producto</label><input id="lot-product-search" type="search" value={productSearch} onChange={event => setProductSearch(event.target.value)} placeholder="Buscar nombre o SKU…" autoComplete="off" maxLength={150} /></div></th>
                <th scope="col">Vencimiento</th>

                <th
                  scope="col"
                  className="numeric"
                >
                  Cantidad
                </th>

                <th scope="col" aria-sort="other"><button type="button" className="lot-state-sort" onClick={() => setPriorityFirst(value => !value)} aria-label={priorityFirst ? 'Estado: Primero en salir arriba. Pulsa para colocarlos abajo.' : 'Estado: Primero en salir abajo. Pulsa para colocarlos arriba.'}>Estado <span className="lot-sort-indicator" aria-hidden="true">{priorityFirst ? '↑' : '↓'}</span></button><span className="lot-cell-detail">{priorityFirst ? 'Prioritarios arriba' : 'Prioritarios abajo'}</span></th>
              </tr>
            </thead>

            <tbody>
              {visibleLots.map((lot) => {
                const isNextFefo = (
                  firstFefoLotIds.has(lot.id)
                )

                return (
                  <tr key={lot.id}>
                    <th scope="row">
                      <span className="lot-code-primary">{lot.lot_number}</span>
                      <span className="lot-cell-detail">{lot.branch_name} · {lot.branch_code}</span>
                      <span className="lot-created">
                        <span className="lot-created-label">{creationLabel(lot.created_at)}</span>
                        {Number.isFinite(Date.parse(lot.created_at)) && <time dateTime={lot.created_at}>{new Date(lot.created_at).toLocaleString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</time>}
                      </span>
                    </th>
                    <td>
                      <span className="product-name">{lot.product_name}</span>
                      <span className="lot-cell-detail">SKU: {lot.product_sku}</span>
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
                          Primero en salir
                        </span>
                      ) : (
                        <span className="lot-status">
                          {lot.is_active
                            ? 'Habilitado'
                            : 'Deshabilitado'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}

              {visibleLots.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="empty-state"
                  >
                    {branchId || productSearch ? 'No hay lotes que coincidan con los filtros.' : 'No hay lotes registrados.'}
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