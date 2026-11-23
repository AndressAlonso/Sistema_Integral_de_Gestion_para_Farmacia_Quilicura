import { useCart } from '../hooks/useCart'
import useAutoRefresh from '../../../hooks/useAutoRefresh'
import StoreIcon from '../components/StoreIcon'
import { useEffect, useState, type FormEvent } from 'react'
import PublicHeader from '../components/PublicHeader'
import StoreBranchMenu from '../components/StoreBranchMenu'
import ProductCard from '../components/ProductCard'
import OfferBanners from '../components/OfferBanners'
import { listBranches, listProducts } from '../services/catalog.api'
import type { PublicBranch, PublicProduct } from '../types/catalog'
import '../ecommerce.css'
import '../store-catalog.css'

export default function OnlineCatalogPage() {
  const [branches, setBranches] = useState<PublicBranch[]>([])
  const [products, setProducts] = useState<PublicProduct[]>([])
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const { draft: cartDraft, selectBranch } = useCart()
  const branchId = cartDraft.pickup_branch_id ?? ''
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [category, setCategory] = useState('')
  const [offersOnly, setOffersOnly] = useState(false)
  const [categoriesOpen, setCategoriesOpen] = useState(false)
  const categories = [...new Map(products.map(product => [product.category.id, product.category])).values()]
    .sort((a, b) => a.name.localeCompare(b.name, 'es'))
  const isOffer = (product: PublicProduct) => Boolean(product.promotion && Number(product.base_price) > Number(product.price))
  const visibleProducts = products.filter(product => (!category || product.category.id === category) && (!offersOnly || isOffer(product)))
  const offerCount = products.filter(isOffer).length
  const selectedCategory = categories.find(item => item.id === category)?.name
  function chooseCategory(id: string) {
    setCategory(id)
    setCategoriesOpen(false)
  }


  useAutoRefresh(() => setAttempt(n => n + 1), !loading)
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
      if (active) { setProducts(data); setLoading(false); setError('') }
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
    setDraft(''); setQuery(''); selectBranch(''); setCategory(''); setOffersOnly(false); setCategoriesOpen(false); setError(''); setLoading(true); setAttempt(value => value + 1)
  }

  return <main className="online-store online-shop">
    <PublicHeader onCatalogHome={clearFilters} />
    <div className="store-discovery">
    <div className="store-search-row">
      <form className="store-search-bar" onSubmit={search} role="search">
        <label className="sr-only" htmlFor="store-search">Buscar productos</label>
        <StoreIcon name="search" />
        <input id="store-search" type="search" maxLength={150} value={draft} onChange={event => setDraft(event.target.value)} placeholder="¿Qué producto buscas?" />
        <button type="submit" aria-label="Buscar productos"><StoreIcon name="search" /><span>Buscar</span></button>
      </form>
      <StoreBranchMenu branches={branches} value={branchId} onChange={id => { if (id !== branchId) { setLoading(true); setError(''); selectBranch(id) } }} />
    </div>
    <nav className="store-browse" aria-label="Explorar el catálogo">
      <button className="store-category-toggle" type="button" aria-expanded={categoriesOpen} aria-controls="store-categories" onClick={() => setCategoriesOpen(!categoriesOpen)}><StoreIcon name="categories" />Categorías <span aria-hidden="true">{categoriesOpen ? '−' : '+'}</span></button>
      <button type="button" aria-pressed={!offersOnly} onClick={() => setOffersOnly(false)}>Todos los productos</button>
      <button type="button" aria-pressed={offersOnly} onClick={() => setOffersOnly(true)}><StoreIcon name="offer" />Ofertas{!loading && !error && <span className="store-count">{offerCount}</span>}</button>
      <a href="#store-how"><StoreIcon name="location" />Compra online, retira en sucursal</a>
    </nav>
    <div id="store-categories" className="store-category-panel" hidden={!categoriesOpen}>
      <div className="store-category-heading"><strong>Explora por categoría</strong><button type="button" aria-label="Cerrar categorías" onClick={() => setCategoriesOpen(false)}>×</button></div>
      <div className="store-category-options">
        <button type="button" aria-pressed={!category} onClick={() => chooseCategory('')}><StoreIcon name="categories" />Todas las categorías</button>
        {categories.map(item => <button key={item.id} type="button" aria-pressed={category === item.id} onClick={() => chooseCategory(item.id)}><StoreIcon name="orders" />{item.name}</button>)}
      </div>
      {!categories.length && <p>{loading ? 'Consultando categorías…' : 'Las categorías aparecerán cuando haya productos disponibles para esta búsqueda.'}</p>}
    </div>
    </div>
    {!query && !category && !offersOnly && <header className="store-welcome">
      <div><p className="online-eyebrow">TU FARMACIA, MÁS CERCA</p><h1>Lo que necesitas,<br /><span>a un paso de ti.</span></h1><p>Encuentra tus productos y elige dónde retirarlos.<br />Nosotros preparamos tu pedido.</p><a className="online-shop-cta" href="#store-products">Explorar productos <span aria-hidden="true">→</span></a></div>
      <div className="store-welcome-card"><span className="store-welcome-icon"><StoreIcon name="cart" /></span><p>Compra a tu ritmo</p><strong>Tu pedido.<br />Tu sucursal.</strong><span>Consulta disponibilidad y precios antes de comprar.</span><a href="#store-how">Así funciona el retiro <span aria-hidden="true">↗</span></a></div>
    </header>}
    {!loading && !error && !query && !category && !offersOnly && <OfferBanners products={products} />}
    <section id="store-products" className="online-shop-catalog" aria-labelledby="store-products-title">
    <div className="store-catalog-heading"><div><p className="online-eyebrow">EXPLORA FARMACIA QUILICURA</p><h2 id="store-products-title">{offersOnly ? 'Ofertas para ti' : selectedCategory || 'Encuentra lo que necesitas'}</h2><p>{offersOnly ? 'Promociones vigentes, con tu ahorro a la vista.' : 'Consulta nuestros productos y su disponibilidad por sucursal.'}</p></div>{categories.length > 0 && <button className="store-change-category" type="button" onClick={() => { setCategoriesOpen(true); document.querySelector('.store-discovery')?.scrollIntoView({ block: 'start' }) }}><StoreIcon name="categories" />Ver categorías</button>}</div>
    <p className="online-shop-stock-note">La disponibilidad se confirma al preparar tu pedido. Los productos con receta se compran presencialmente.</p>
    {(query || branchId || category || offersOnly) && <div className="online-shop-active-filters"><span>{query ? `Búsqueda: “${query}”` : 'Todos los productos'}{branchId && ` · ${branches.find(branch => branch.id === branchId)?.name ?? 'Sucursal seleccionada'}`}{category && ` · ${selectedCategory || 'Categoría seleccionada'}`}{offersOnly && ' · En oferta'}</span><button type="button" onClick={clearFilters}>Limpiar filtros <span aria-hidden="true">×</span></button></div>}
    {error ? <div className="online-feedback" role="alert"><p>{error}</p><button onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></div>
      : loading ? <p className="online-feedback" role="status">Consultando catálogo…</p>
        : <><p className="online-results" role="status">{visibleProducts.length === 1 ? '1 producto encontrado.' : `${visibleProducts.length} productos encontrados.`}</p><div className="online-grid">{visibleProducts.map(product => <ProductCard key={product.id} product={product} />)}</div>{!visibleProducts.length && <div className="online-feedback online-shop-empty"><h3>No encontramos productos para esta búsqueda</h3><p>Prueba con otro nombre, cambia la categoría o limpia los filtros.</p>{(query || branchId || category || offersOnly) && <button type="button" onClick={clearFilters}>Ver todos los productos</button>}</div>}</>}
    </section>
    <section id="store-how" className="store-how" aria-labelledby="store-how-title"><div><p className="online-eyebrow">FÁCIL, DE PRINCIPIO A FIN</p><h2 id="store-how-title">De tu carrito a tu sucursal</h2></div><ol><li><StoreIcon name="cart" /><div><strong>1. Elige tus productos</strong><p>Agrega al carrito y selecciona tu sucursal.</p></div></li><li><StoreIcon name="receipt" /><div><strong>2. Confirma y paga</strong><p>Revisa el total y completa tu compra.</p></div></li><li><StoreIcon name="location" /><div><strong>3. Retira con tu QR</strong><p>Espera el aviso de que tu pedido está listo.</p></div></li></ol></section>
    <footer className="online-shop-footer"><strong>Farmacia Quilicura</strong><span>Consulta los detalles y requisitos de cada producto antes de confirmar tu pedido.</span></footer>
  </main>
}


