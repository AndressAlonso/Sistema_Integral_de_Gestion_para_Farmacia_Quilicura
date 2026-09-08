import { getAvailableStock, type InventoryRecord } from './inventory.mock'

export default function InventoryTable({ records }: { records: InventoryRecord[] }) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Stock por producto y sucursal">
      <table>
        <caption className="sr-only">Stock físico, reservado y disponible por sucursal, en unidades</caption>
        <thead>
          <tr>
            <th scope="col">Producto</th>
            <th scope="col">Sucursal</th>
            <th scope="col" className="numeric">Físico</th>
            <th scope="col" className="numeric">Reservado</th>
            <th scope="col" className="numeric">Disponible</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => {
            const available = getAvailableStock(record)
            return (
              <tr key={record.id}>
                <th scope="row"><span className="product-name">{record.product}</span><span className="product-detail">{record.presentation}</span></th>
                <td><span className="branch-label">{record.branch}</span></td>
                {available === null ? <td colSpan={3}>Datos de stock inconsistentes</td> : (
                  <>
                    <td className="numeric">{record.physical}</td>
                    <td className="numeric reserved">{record.reserved}</td>
                    <td className="numeric"><span className={available === 0 ? 'stock-value stock-zero' : 'stock-value'}>{available}</span></td>
                  </>
                )}
              </tr>
            )
          })}
          {records.length === 0 && (
            <tr><td colSpan={5} className="empty-state">No hay productos que coincidan con esta consulta.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

