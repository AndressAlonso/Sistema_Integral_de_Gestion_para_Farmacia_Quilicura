// HU: E3-H1 — Consultar stock por sucursal
import { useState } from 'react'
import pharmacyLogo from '../../assets/logo-farmacia-quilicura.jpg'
import { inventoryRecords } from './inventory.mock'
import InventoryTable from './InventoryTable'
import './InventoryPage.css'

const branches = [...new Set(inventoryRecords.map((record) => record.branch))]

export default function InventoryPage() {
  const [branch, setBranch] = useState('')
  const [query, setQuery] = useState('')
  const records = inventoryRecords.filter((record) =>
    (!branch || record.branch === branch)
    && record.product.toLocaleLowerCase('es').includes(query.trim().toLocaleLowerCase('es')),
  )

  return (
    <div className="inventory-app">
      <header className="app-header">
        <div className="brand"><img className="brand-logo" src={pharmacyLogo} alt="Farmacia Quilicura — Cuidando tu salud" width={250} height={100} /></div>
        <span className="workspace-label">Gestión de inventario</span>
        <span className="demo-badge">Demostración</span>
      </header>
      <main className="inventory-main">
        <p className="eyebrow">INVENTARIO / CONSULTA DE STOCK</p>
        <div className="page-heading">
          <div><h1>Stock por sucursal</h1><p>Consulta las existencias y su disponibilidad en cada sucursal.</p></div>
          <span className="read-only">Solo consulta</span>
        </div>
        <div className="demo-notice"><span aria-hidden="true">ⓘ</span><p>Vista de ejemplo con datos ficticios. Los productos, sucursales y cantidades no representan el inventario real.</p></div>
        <section className="stock-guide" aria-label="Cómo se interpreta el stock">
          <div><span className="guide-number">01</span><h2>Stock físico</h2><p>Unidades presentes en la sucursal.</p></div>
          <div><span className="guide-number">02</span><h2>Stock reservado</h2><p>Unidades comprometidas que aún no han salido.</p></div>
          <div className="available-guide"><span className="guide-number">03</span><h2>Stock disponible</h2><p>Stock físico menos stock reservado.</p></div>
        </section>
        <section className="inventory-panel" aria-labelledby="results-title">
          <div className="panel-heading"><div><h2 id="results-title">Existencias por producto</h2><p>Las cantidades se expresan en unidades.</p></div></div>
          <div className="filters">
            <div className="search-field"><label htmlFor="product-search">Buscar producto</label><input id="product-search" type="search" placeholder="Escribe el nombre de un producto" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
            <div className="branch-field"><label htmlFor="branch">Sucursal</label><select id="branch" value={branch} onChange={(event) => setBranch(event.target.value)}><option value="">Todas las sucursales</option>{branches.map((name) => <option key={name} value={name}>{name}</option>)}</select></div>
            <button type="button" className="clear-button" disabled={!branch && !query} onClick={() => { setBranch(''); setQuery('') }}>Limpiar filtros</button>
          </div>
          <InventoryTable records={records} />
          <div className="table-footer"><span role="status">{records.length} de {inventoryRecords.length} registros</span><span>Disponible = físico − reservado</span></div>
        </section>
        <footer className="page-footer"><span>Sistema Integral de Gestión para Farmacia Quilicura</span><span>Consulta de inventario multisucursal</span></footer>
      </main>
    </div>
  )
}
