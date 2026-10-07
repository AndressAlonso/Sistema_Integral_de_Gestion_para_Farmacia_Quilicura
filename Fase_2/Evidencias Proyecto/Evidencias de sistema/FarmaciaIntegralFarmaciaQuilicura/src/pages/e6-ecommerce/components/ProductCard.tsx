import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { PublicProduct } from '../types/catalog'
import AddToCartButton from './AddToCartButton'

const currency = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 })

export default function ProductCard({ product, detail = false }: { product: PublicProduct; detail?: boolean }) {
  const [failedImage, setFailedImage] = useState<string | null>(null)
  return <article className={`online-product${detail ? ' online-detail' : ''}`}>
    <div className="online-photo">
      {product.image_url && failedImage !== product.image_url ? <img src={product.image_url} alt={product.name} loading="lazy"
        onError={() => setFailedImage(product.image_url)} /> : <span className="online-placeholder"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4" /><circle cx="8" cy="8" r="1.5" /><path d="m3 17 6-5 4 3 4-4 4 5" /></svg><span>Sin imagen</span></span>}
    </div>
    <div className="online-product-content">
      <p className="online-category">{product.category.name}</p>
      {detail ? <h1>{product.name}</h1> : <h2><Link to={`/tienda/productos/${encodeURIComponent(product.id)}`}>{product.name}</Link></h2>}
      <p className="online-price">{currency.format(Number(product.price))}</p>
      {product.requires_prescription && <p className="online-prescription">Requiere receta · Compra presencial</p>}
      <p className="online-description">{product.description || 'Sin información adicional.'}</p>
      <h3>Disponibilidad por sucursal <span className="online-stock-caption">Informativa</span></h3>
      {product.availability.length ? <ul className="online-stock">{product.availability.map(stock =>
        <li key={stock.branch_id}><span className="online-branch-name">{stock.branch_name}</span><span className={`online-stock-tag${stock.available === 0 ? ' online-stock-empty' : ''}`}><span>{stock.available === 0 ? 'Sin stock' : 'Disponible'}</span><strong>{stock.available} unidades</strong></span></li>,
      )}</ul> : <p>No hay sucursales activas para consultar.</p>}
      {!detail && <Link className="online-product-button" to={`/tienda/productos/${encodeURIComponent(product.id)}`} aria-label={`Ver producto: ${product.name}`}>Ver producto <span aria-hidden="true">→</span></Link>}
      {product.online_purchase_allowed && !product.requires_prescription && <AddToCartButton productId={product.id} />}
    </div>
  </article>
}
