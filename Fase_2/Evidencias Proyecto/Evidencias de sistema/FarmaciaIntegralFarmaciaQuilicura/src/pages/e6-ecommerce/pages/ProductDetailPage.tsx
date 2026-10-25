import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import PublicHeader from '../components/PublicHeader'
import { getProduct } from '../services/catalog.api'
import type { PublicProduct } from '../types/catalog'
import '../ecommerce.css'

export default function ProductDetailPage() {
  const { productId } = useParams()
  const [result, setResult] = useState<{ id: string; product?: PublicProduct; error?: string } | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    if (productId) void getProduct(productId).then(product => {
      if (active) setResult({ id: productId, product })
    }).catch(cause => {
      if (active) setResult({ id: productId, error: cause instanceof Error ? cause.message : 'No pudimos consultar el producto.' })
    })
    return () => { active = false }
  }, [productId, attempt])
  const current = result?.id === productId ? result : null
  return <main className="online-store store-product-page">
    <PublicHeader />
    <nav className="online-breadcrumb" aria-label="Ubicación"><Link className="online-link" to="/tienda">← Volver al catálogo</Link><span aria-hidden="true">/</span><span>Ficha del producto</span></nav>
    <p className="store-product-help">Conoce el producto y consulta sus existencias por sucursal. Verificaremos las unidades aptas para venta antes de confirmar tu pedido.</p>
    {current?.error ? <div className="online-feedback" role="alert"><p>{current.error}</p><button onClick={() => { setResult(null); setAttempt(value => value + 1) }}>Reintentar</button></div>
      : current?.product ? <ProductCard product={current.product} detail /> : <p className="online-feedback" role="status">Consultando producto…</p>}
  </main>
}
