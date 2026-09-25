// E2-H1: listado y alta de productos y categorias.
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import type { AuthSession } from '../e1-access-users-branches/auth/login.api'
import { ApiError } from '../../services/http'
import CatalogDialog from './CatalogDialog'
import { createCategory, createProduct, listCategories, listProducts, type Category, type Product, type ProductInput } from './catalog.api'
import '../e1-access-users-branches/users/users.css'
import './catalog.css'

const currency = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', minimumFractionDigits: 0, maximumFractionDigits: 2 })
const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es')

export default function CatalogPage() {
  const session = useOutletContext<AuthSession>()
  const navigate = useNavigate()
  const allowed = session.user.permissions.includes('catalogo.gestionar')
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [status, setStatus] = useState('')
  const [editor, setEditor] = useState<'product' | 'category' | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const sending = useRef(false)

  useEffect(() => {
    if (!allowed) return
    let active = true
    Promise.all([listProducts(), listCategories()]).then(([items, groups]) => {
      if (!active) return
      setProducts(items); setCategories(groups); setLoading(false)
    }).catch((cause: unknown) => {
      if (!active) return
      if (cause instanceof ApiError && cause.status === 401) { navigate('/login', { replace: true }); return }
      setLoadError(cause instanceof ApiError ? cause.message : 'No pudimos cargar el catálogo.')
      setLoading(false)
    })
    return () => { active = false }
  }, [allowed, attempt, navigate])

  async function save(operation: () => Promise<void>, success: string) {
    if (sending.current) return
    sending.current = true; setBusy(true); setError('')
    try {
      await operation()
      setEditor(null); setMessage(success)
      // El nuevo producto debe quedar visible aunque hubiera filtros activos.
      setQuery(''); setCategoryId(''); setStatus('')
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) { navigate('/login', { replace: true }); return }
      if (cause instanceof ApiError && cause.status === 403) { setEditor(null); setLoadError(cause.message); return }
      setError(cause instanceof ApiError && cause.status !== 0 ? cause.message : 'No pudimos confirmar el guardado. Cierra el formulario y recarga el listado antes de reintentar.')
    } finally { sending.current = false; setBusy(false) }
  }
  function addProduct(input: ProductInput) {
    void save(async () => {
      const product = await createProduct(input)
      setProducts(current => [...current, product].sort((a, b) => a.name.localeCompare(b.name, 'es')))
    }, 'Producto creado correctamente.')
  }
  function addCategory(name: string) {
    void save(async () => {
      const category = await createCategory(name)
      setCategories(current => [...current, category].sort((a, b) => a.name.localeCompare(b.name, 'es')))
    }, 'Categoría creada. Ya puedes seleccionarla al registrar un producto.')
  }
  function open(mode: 'product' | 'category') { setError(''); setMessage(''); setEditor(mode) }

  if (!allowed) return <p className="users-error" role="alert">No tienes permiso para gestionar el catálogo.</p>
  if (loading) return <p role="status">Cargando catálogo…</p>
  if (loadError) return <div><p className="users-error" role="alert">{loadError}</p>
    <button className="users-button" onClick={() => { setLoading(true); setLoadError(''); setAttempt(value => value + 1) }}>Reintentar</button></div>

  const names = new Map(categories.map(category => [category.id, category.name]))
  const search = normalize(query.trim())
  const visible = products.filter(product =>
    (!search || normalize([product.name, product.sku, ...product.barcodes].join(' ')).includes(search)) &&
    (!categoryId || product.category_id === categoryId) &&
    (!status || product.is_active === (status === 'active')),
  )

  return <div className="users-page catalog-page">
    <header className="users-heading catalog-heading">
      <div><h1>Gestión de productos</h1><p>Administra el catálogo, las categorías y los códigos de barras de la farmacia.</p></div>
      <div className="catalog-heading-actions">
        <button className="users-button" onClick={() => open('category')}>+ Nueva categoría</button>
        <button className="users-button primary" disabled={!categories.length} onClick={() => open('product')}>+ Nuevo producto</button>
      </div>
    </header>
    {message && <p className="users-success" role="status">{message}</p>}
    {!categories.length && <p className="catalog-notice" role="status">Crea una categoría para comenzar a registrar productos.</p>}
    <div className="users-filters">
      <label className="users-search"><span className="sr-only">Buscar productos</span>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5" /></svg>
        <input type="search" placeholder="Buscar por nombre, SKU o código de barras…" value={query} onChange={event => setQuery(event.target.value)} />
      </label>
      <label><span className="sr-only">Filtrar por categoría</span><select value={categoryId} onChange={event => setCategoryId(event.target.value)}><option value="">Todas las categorías</option>
        {categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}
      </select></label>
      <label><span className="sr-only">Filtrar por estado</span><select value={status} onChange={event => setStatus(event.target.value)}><option value="">Todos los estados</option><option value="active">Activos</option><option value="inactive">Inactivos</option></select></label>
      {(query || categoryId || status) && <button className="users-button" onClick={() => { setQuery(''); setCategoryId(''); setStatus('') }}>Limpiar filtros</button>}
    </div>
    <section className="users-panel" aria-labelledby="catalog-list-title">
      <div className="users-panel-heading catalog-panel-heading"><div><h2 id="catalog-list-title">Productos registrados</h2><p role="status">{visible.length} de {products.length} {products.length === 1 ? 'producto' : 'productos'}</p></div><span className="catalog-category-count">{categories.length} {categories.length === 1 ? 'categoría' : 'categorías'}</span></div>
      <div className="users-table-scroll" role="region" aria-label="Listado de productos" tabIndex={0}>
        <table className="users-table catalog-table"><thead><tr>
          <th scope="col">Producto / SKU</th><th scope="col">Categoría</th><th scope="col">Precio</th><th scope="col">Códigos de barras</th><th scope="col">Condición</th><th scope="col">Estado</th><th scope="col">Publicación online</th>
        </tr></thead><tbody>
          {visible.map(product => <tr key={product.id}>
            <th scope="row"><div className="catalog-product-name"><strong>{product.name}</strong><small>{product.sku}</small>
              {product.description && <details><summary>Descripción</summary><p>{product.description}</p></details>}
            </div></th>
            <td>{names.get(product.category_id) ?? 'Categoría no disponible'}</td>
            <td className="catalog-price">{currency.format(Number(product.price))}</td>
            <td><div className="catalog-barcodes">{product.barcodes.length ? product.barcodes.map(code => <code key={code}>{code}</code>) : <span className="catalog-help">Sin códigos</span>}</div></td>
            <td><span className={product.requires_prescription ? 'catalog-prescription' : ''}>{product.requires_prescription ? 'Con receta' : 'Sin receta'}</span></td>
            <td><span className={`users-status${product.is_active ? '' : ' inactive'}`}>{product.is_active ? 'Activo' : 'Inactivo'}</span></td>
            <td>{product.published_online ? 'Publicado' : 'No publicado'}</td>
          </tr>)}
          {!visible.length && <tr><td colSpan={7} className="users-empty">{products.length ? 'No hay productos que coincidan con los filtros.' : 'Aún no hay productos. Registra el primero con «Nuevo producto».'}</td></tr>}
        </tbody></table>
      </div>
    </section>
    {editor && <CatalogDialog mode={editor} categories={categories} busy={busy} error={error} onClose={() => { if (!sending.current) setEditor(null) }} onProduct={addProduct} onCategory={addCategory} />}
  </div>
}
