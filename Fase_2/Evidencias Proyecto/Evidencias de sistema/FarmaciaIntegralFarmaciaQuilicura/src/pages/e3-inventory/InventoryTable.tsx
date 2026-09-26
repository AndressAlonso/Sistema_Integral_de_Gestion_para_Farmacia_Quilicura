import type { InventoryRecord } from './inventory.api'

function isConsistent(record: InventoryRecord): boolean {
  return (
    Number.isInteger(record.physical)
    && Number.isInteger(record.reserved)
    && Number.isInteger(record.available)
    && record.physical >= 0
    && record.reserved >= 0
    && record.reserved <= record.physical
    && record.available === record.physical - record.reserved
  )
}

export default function InventoryTable({
  records,
}: {
  records: InventoryRecord[]
}) {
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Stock por producto y sucursal"
    >
      <table>
        <caption className="sr-only">
          Stock físico, reservado y disponible por sucursal, en unidades
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
          </tr>
        </thead>

        <tbody>
          {records.map((record) => {
            const consistent = isConsistent(record)

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
                    {record.branch_name} ({record.branch_code})
                  </span>
                </td>

                {!consistent ? (
                  <td colSpan={3} className="stock-error">
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
                  </>
                )}
              </tr>
            )
          })}

          {records.length === 0 && (
            <tr>
              <td colSpan={5} className="empty-state">
                No hay productos que coincidan con esta consulta.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}