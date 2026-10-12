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

  return <main className="online-store">
    <PublicHeader />
    <header className="online-header"><p className="online-eyebrow">Nuestros productos</p><h1>Catálogo online</h1><p>Encuentra información y consulta la disponibilidad en nuestras sucursales.</p></header>
    <form className="online-filters" onSubmit={search}>
      <label className="online-field online-search">Buscar producto<input type="search" maxLength={150} value={draft} onChange={event => setDraft(event.target.value)} placeholder="Nombre o información del producto" /></label>
      <button type="submit">Buscar</button>
      <BranchSelector branches={branches} value={branchId} onChange={value => { setLoading(true); setError(''); setBranchId(value) }} />
    </form>
    <div className="online-notice"><span className="online-info-mark" aria-hidden="true">i</span><p><strong>Disponibilidad informativa.</strong> Stock físico menos reservas. No confirma unidades comprables online; los lotes y unidades vendibles se validarán antes de comprar.</p></div>
    {error ? <div className="online-feedback" role="alert"><p>{error}</p><button onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></div>
      : loading ? <p className="online-feedback" role="status">Consultando catálogo…</p>
        : <><p className="online-results" role="status">{products.length === 1 ? '1 producto encontrado.' : `${products.length} productos encontrados.`}</p><div className="online-grid">{products.map(product => <ProductCard key={product.id} product={product} />)}</div>{!products.length && <p className="online-feedback">No hay productos publicados que coincidan con la búsqueda.</p>}</>}
  </main>
}
