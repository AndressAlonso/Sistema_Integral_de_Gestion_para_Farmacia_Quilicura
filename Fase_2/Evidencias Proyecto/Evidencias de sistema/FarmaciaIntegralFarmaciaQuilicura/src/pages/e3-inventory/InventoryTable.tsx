import {
  type FormEvent,
  useState,
} from 'react'

import { ApiError } from '../../services/http'
import {
  type InventoryRecord,
  updateInventoryMinimum,
} from './inventory.api'

interface InventoryTableProps {
  records: InventoryRecord[]
  onRecordUpdated: (
    record: InventoryRecord,
  ) => void
}

function isConsistent(
  record: InventoryRecord,
): boolean {
  return (
    Number.isInteger(record.physical)
    && Number.isInteger(record.reserved)
    && Number.isInteger(record.available)
    && Number.isInteger(record.minimum)
    && record.physical >= 0
    && record.reserved >= 0
    && record.minimum >= 0
    && record.reserved <= record.physical
    && record.available
      === record.physical - record.reserved
  )
}

function stockStatusLabel(
  record: InventoryRecord,
): string {
  if (record.stock_status === 'SIN_STOCK') {
    return 'Sin stock'
  }

  if (record.stock_status === 'BAJO') {
    return 'Stock bajo'
  }

  if (record.minimum === 0) {
    return 'Sin configurar'
  }

  return 'Disponible'
}

function stockStatusClass(
  record: InventoryRecord,
): string {
  if (record.stock_status === 'SIN_STOCK') {
    return 'stock-status stock-status-empty'
  }

  if (record.stock_status === 'BAJO') {
    return 'stock-status stock-status-low'
  }

  if (record.minimum === 0) {
    return 'stock-status stock-status-unconfigured'
  }

  return 'stock-status stock-status-available'
}

function minimumErrorMessage(
  error: unknown,
): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'La sesión dejó de ser válida.'
    }

    if (error.status === 403) {
      return 'No tienes permiso para configurar el mínimo.'
    }

    if (error.status === 404) {
      return 'El inventario seleccionado no existe.'
    }

    if (error.status === 422) {
      return 'El mínimo debe estar entre 0 y 1.000.000.'
    }

    return error.message
  }

  return 'No pudimos actualizar el stock mínimo.'
}

export default function InventoryTable({
  records,
  onRecordUpdated,
}: InventoryTableProps) {
  const [editingId, setEditingId] = useState<
    string | null
  >(null)

  const [minimumValue, setMinimumValue] = useState('')
  const [submittingId, setSubmittingId] = useState<
    string | null
  >(null)

  const [errorId, setErrorId] = useState<
    string | null
  >(null)

  const [errorMessage, setErrorMessage] = useState('')

  function startEditing(
    record: InventoryRecord,
  ): void {
    setEditingId(record.id)
    setMinimumValue(String(record.minimum))
    setErrorId(null)
    setErrorMessage('')
  }

  function cancelEditing(): void {
    setEditingId(null)
    setMinimumValue('')
    setErrorId(null)
    setErrorMessage('')
  }

  async function handleMinimumSubmit(
    event: FormEvent<HTMLFormElement>,
    record: InventoryRecord,
  ): Promise<void> {
    event.preventDefault()

    const minimum = Number(minimumValue)

    if (
      !Number.isInteger(minimum)
      || minimum < 0
      || minimum > 1_000_000
    ) {
      setErrorId(record.id)
      setErrorMessage(
        'Ingresa un número entero entre 0 y 1.000.000.',
      )
      return
    }

    setSubmittingId(record.id)
    setErrorId(null)
    setErrorMessage('')

    try {
      const updated = await updateInventoryMinimum(
        record.id,
        minimum,
      )

      onRecordUpdated(updated)
      setEditingId(null)
      setMinimumValue('')
    } catch (cause: unknown) {
      setErrorId(record.id)
      setErrorMessage(
        minimumErrorMessage(cause),
      )
    } finally {
      setSubmittingId(null)
    }
  }

  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Stock por producto y sucursal"
    >
      <table className="inventory-stock-table">
        <caption className="sr-only">
          Stock físico, reservado, disponible y mínimo
          por producto y sucursal
        </caption>

        <thead>
          <tr>
            <th scope="col">Producto</th>
            <th scope="col">Sucursal</th>

            <th scope="col" className="numeric">
              Físico
            </th>

            <th scope="col" className="numeric">
              Reservado
            </th>

            <th scope="col" className="numeric">
              Disponible
            </th>

            <th scope="col" className="numeric">
              Mínimo
            </th>

            <th scope="col">Estado</th>
            <th scope="col">Acción</th>
          </tr>
        </thead>

        <tbody>
          {records.map((record) => {
            const consistent = isConsistent(record)
            const isEditing = editingId === record.id
            const isSubmitting = (
              submittingId === record.id
            )

            return (
              <tr key={record.id}>
                <th scope="row">
                  <span className="product-name">
                    {record.product_name}
                  </span>

                  <span className="product-detail">
                    SKU: {record.product_sku}
                  </span>
                </th>

                <td>
                  <span className="branch-label">
                    {record.branch_name}{' '}
                    ({record.branch_code})
                  </span>
                </td>

                {!consistent ? (
                  <td
                    colSpan={6}
                    className="stock-error"
                  >
                    Datos de stock inconsistentes
                  </td>
                ) : (
                  <>
                    <td className="numeric">
                      {record.physical}
                    </td>

                    <td className="numeric reserved">
                      {record.reserved}
                    </td>

                    <td className="numeric">
                      <span
                        className={
                          record.available === 0
                            ? 'stock-value stock-zero'
                            : 'stock-value'
                        }
                      >
                        {record.available}
                      </span>
                    </td>

                    <td className="numeric">
                      {record.minimum === 0
                        ? 'No configurado'
                        : record.minimum}
                    </td>

                    <td>
                      <span
                        className={
                          stockStatusClass(record)
                        }
                      >
                        {stockStatusLabel(record)}
                      </span>
                    </td>

                    <td className="minimum-action-cell">
                      {isEditing ? (
                        <form
                          className="minimum-form"
                          onSubmit={(event) => {
                            void handleMinimumSubmit(
                              event,
                              record,
                            )
                          }}
                        >
                          <label
                            className="sr-only"
                            htmlFor={`minimum-${record.id}`}
                          >
                            Stock mínimo para{' '}
                            {record.product_name}
                          </label>

                          <input
                            id={`minimum-${record.id}`}
                            type="number"
                            min={0}
                            max={1_000_000}
                            step={1}
                            value={minimumValue}
                            onChange={(event) => {
                              setMinimumValue(
                                event.target.value,
                              )
                              setErrorId(null)
                              setErrorMessage('')
                            }}
                            disabled={isSubmitting}
                            autoFocus
                            required
                          />

                          <button
                            type="submit"
                            className="minimum-save-button"
                            disabled={isSubmitting}
                          >
                            {isSubmitting
                              ? 'Guardando…'
                              : 'Guardar'}
                          </button>

                          <button
                            type="button"
                            className="minimum-cancel-button"
                            onClick={cancelEditing}
                            disabled={isSubmitting}
                          >
                            Cancelar
                          </button>

                          {errorId === record.id && (
                            <span
                              className="minimum-error"
                              role="alert"
                            >
                              {errorMessage}
                            </span>
                          )}
                        </form>
                      ) : (
                        <button
                          type="button"
                          className="minimum-edit-button"
                          onClick={() => {
                            startEditing(record)
                          }}
                        >
                          Configurar mínimo
                        </button>
                      )}
                    </td>
                  </>
                )}
              </tr>
            )
          })}

          {records.length === 0 && (
            <tr>
              <td
                colSpan={8}
                className="empty-state"
              >
                No hay productos que coincidan con esta consulta.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}