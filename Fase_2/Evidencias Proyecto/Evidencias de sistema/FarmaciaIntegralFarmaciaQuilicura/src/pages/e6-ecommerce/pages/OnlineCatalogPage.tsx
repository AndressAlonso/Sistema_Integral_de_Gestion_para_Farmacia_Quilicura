import StoreIcon from '../components/StoreIcon'
import { useEffect, useState, type FormEvent } from 'react'
import PublicHeader from '../components/PublicHeader'
import BranchSelector from '../components/BranchSelector'
import ProductCard from '../components/ProductCard'
import { listBranches, listProducts } from '../services/catalog.api'
import type { PublicBranch, PublicProduct } from '../types/catalog'
import '../ecommerce.css'

export default function OnlineCatalogPage() {
  const [branches, setBranches] = useState<PublicBranch[]>([])
  const [products, setProducts] = useState<PublicProduct[]>([])
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const [branchId, setBranchId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    void listBranches().then(data => { if (active) setBranches(data) }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : 'No pudimos consultar las sucursales.')
    })
    return () => { active = false }
  }, [attempt])

  useEffect(() => {
    let active = true
    void listProducts(query, branchId).then(data => {
      if (active) { setProducts(data); setLoading(false) }
    }).catch(cause => {
      if (active) { setError(cause instanceof Error ? cause.message : 'No pudimos consultar el catálogo.'); setLoading(false) }
    })
    return () => { active = false }
  }, [query, branchId, attempt])

  function search(event: FormEvent) {
    event.preventDefault()
    if (draft.trim() !== query) { setLoading(true); setError(''); setQuery(draft.trim()) }
  }

  function clearFilters() {
    setDraft(''); setQuery(''); setBranchId(''); setError(''); setLoading(true); setAttempt(value => value + 1)
  }

  return <main className="online-store online-shop">
    <PublicHeader />
    <header className="online-shop-hero">
      <div><p className="online-eyebrow">FARMACIA QUILICURA · TIENDA ONLINE</p><h1>Tu bienestar,<br /><span>más cerca de ti.</span></h1><p>Encuentra lo que necesitas, revisa los precios y prepara tu pedido para retirar en sucursal.</p><a href="#store-products" className="online-shop-cta">Explorar productos <span aria-hidden="true">↓</span></a></div>
      <aside className="online-shopping-guide" aria-label="Cómo preparar tu pedido"><h2>De tu carrito a tu sucursal</h2><ol><li><span aria-hidden="true">1</span><div><strong>Encuentra tus productos</strong><p>Busca por nombre y revisa sus detalles.</p></div></li><li><span aria-hidden="true">2</span><div><strong>Arma tu carrito</strong><p>Elige las cantidades y la sucursal de retiro.</p></div></li><li><span aria-hidden="true">3</span><div><strong>Revisa y confirma</strong><p>Comprueba los productos y el total antes de crear tu pedido.</p></div></li></ol></aside>
    </header>
    <section id="store-products" className="online-shop-catalog" aria-labelledby="store-products-title">
    <div className="online-shop-section-heading"><div><h2 id="store-products-title">Encuentra lo que necesitas</h2><p>Productos y precios de nuestra farmacia.</p></div></div>
    <form className="online-filters" onSubmit={search} role="search">
      <label className="online-field online-search"><span className="store-label-icon"><StoreIcon name="search" />¿Qué estás buscando?</span><input type="search" maxLength={150} value={draft} onChange={event => setDraft(event.target.value)} placeholder="Escribe el nombre de un producto…" /></label>
      <button type="submit"><span className="store-label-icon"><StoreIcon name="search" />Buscar</span></button>
      <BranchSelector branches={branches} value={branchId} onChange={value => { setLoading(true); setError(''); setBranchId(value) }} />
    </form>
    <p className="online-shop-stock-note">La disponibilidad se confirma al preparar tu pedido. Los productos con receta se compran presencialmente.</p>
    {(query || branchId) && <div className="online-shop-active-filters"><span>{query ? `Búsqueda: “${query}”` : 'Todos los productos'}{branchId && ` · ${branches.find(branch => branch.id === branchId)?.name ?? 'Sucursal seleccionada'}`}</span><button type="button" onClick={clearFilters}>Limpiar filtros <span aria-hidden="true">×</span></button></div>}
    {error ? <div className="online-feedback" role="alert"><p>{error}</p><button onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></div>
      : loading ? <p className="online-feedback" role="status">Consultando catálogo…</p>
        : <><p className="online-results" role="status">{products.length === 1 ? '1 producto encontrado.' : `${products.length} productos encontrados.`}</p><div className="online-grid">{products.map(product => <ProductCard key={product.id} product={product} />)}</div>{!products.length && <div className="online-feedback online-shop-empty"><h3>No encontramos productos para esta búsqueda</h3><p>Prueba con otro nombre o consulta todas las sucursales.</p>{(query || branchId) && <button type="button" onClick={clearFilters}>Ver todos los productos</button>}</div>}</>}
    </section>
    <footer className="online-shop-footer"><strong>Farmacia Quilicura</strong><span>Consulta los detalles y requisitos de cada producto antes de confirmar tu pedido.</span></footer>
  </main>
}
