import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import type { AuthSession } from '../e1-access-users-branches/auth/login.api'
import { ApiError } from '../../services/http'
import { currency, errorMessage, paymentNames, posApi, type Cash, type Item, type Payment, type Product, type Quote, type Receipt, type SaleRequest } from './pos.api'
import './pos.css'
import SalesDialog from './SalesDialog'
import ProductPhoto from '../e2-catalog/ProductPhoto'
import '../e2-catalog/catalog.css'
import ScannerLinkDialog from './ScannerLinkDialog'

export default function PosPage() {
  const { user } = useOutletContext<AuthSession>()
  const [search, setSearch] = useState('')
  const [showSales, setShowSales] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [cart, setCart] = useState<Array<Item & { name: string; available: number }>>([])
  const [quote, setQuote] = useState<Quote | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [payment, setPayment] = useState<Payment>('EFECTIVO')
  const [receipt, setReceipt] = useState<Receipt | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [searching, setSearching] = useState(false)
  const [pending, setPending] = useState<SaleRequest | null>(() => {
    try { return JSON.parse(sessionStorage.getItem(`pos-pending:${user.id}`) ?? 'null') as SaleRequest | null } catch { return null }
  })
  const dialog = useRef<HTMLDialogElement>(null)
  const locked = useRef(false)
  useEffect(() => {
    if (!cart.length || pending) return
    let active = true
    const timer = setTimeout(() => {
      posApi.quote(cart.map(({ product_id, quantity }) => ({ product_id, quantity })))
        .then(result => { if (active) setQuote(result) })
        .catch(cause => { if (active) { setQuote(null); setError(errorMessage(cause)) } })
    }, 250)
    return () => { active = false; clearTimeout(timer) }
  }, [cart, pending])

  useEffect(() => {
    let active = true
    posApi.cash().then(value => { if (active) setCash(value) }).catch(cause => { if (active) setError(errorMessage(cause)) })
    return () => { active = false }
  }, [])

  async function find(event: FormEvent) {
    event.preventDefault()
    if (searching) return
    setSearching(true); setError('')
    try { setProducts((await posApi.products(search)).products) } catch (cause) { setError(errorMessage(cause)) }
    finally { setSearching(false) }
  }
  function add(product: Product) {
    if (pending || busy || locked.current) return
    const row = cart.find(item => item.product_id === product.id)
    if ((row?.quantity ?? 0) >= product.available) { setError('No puedes superar el stock vendible disponible.'); return }
    setQuote(null); setError('')
    setCart(row ? cart.map(item => item === row ? { ...item, quantity: item.quantity + 1 } : item)
      : [...cart, { product_id: product.id, name: product.name, available: product.available, quantity: 1 }])
  }
  async function review() {
    if (locked.current || !cart.length) return
    locked.current = true; setBusy(true); setError('')
    try {
      const current = await posApi.cash(); setCash(current)
      if (!current) { setError('Abre tu caja antes de cobrar.'); return }
      setQuote(await posApi.quote(cart.map(({ product_id, quantity }) => ({ product_id, quantity }))))
      dialog.current?.showModal()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { locked.current = false; setBusy(false) }
  }
  async function pay() {
    if (locked.current || (!quote && !pending)) return
    const data = pending ?? { request_id: crypto.randomUUID(), items: cart.map(({ product_id, quantity }) => ({ product_id, quantity })), payment, quote_version: quote!.version }
    locked.current = true; setBusy(true); setError('')
    try {
      // Conservar la misma solicitud antes de enviarla permite recuperar respuestas perdidas.
      sessionStorage.setItem(`pos-pending:${user.id}`, JSON.stringify(data)); setPending(data)
      const result = await posApi.sell(data)
      setReceipt(result); setCart([]); setQuote(null); setPending(null)
      sessionStorage.removeItem(`pos-pending:${user.id}`)
      dialog.current?.close()
    } catch (cause) {
      if (cause instanceof ApiError && [403, 409, 422].includes(cause.status)) {
        setPending(null); sessionStorage.removeItem(`pos-pending:${user.id}`); setQuote(null); dialog.current?.close()
      }
      setError(errorMessage(cause))
    } finally { locked.current = false; setBusy(false) }
  }

  return <section className="pos-page">
    <div className="pos-section-title"><button className="pos-secondary" onClick={() => setShowSales(true)}>Ventas, comprobantes y devoluciones</button><ScannerLinkDialog
      userName={user.name}
      branchName={user.branch_name}
    />  </div>
    {showSales && <SalesDialog userId={user.id} canReverse={user.roles.includes('ADMINISTRADOR') && user.permissions.includes('ventas.reversar')} onClose={() => setShowSales(false)} onReceipt={setReceipt} />}
    <header className="pos-heading"><div><p className="pos-eyebrow">VENTA EN SUCURSAL</p><h1>Punto de venta</h1><p>{user.branch_name} · {user.name}</p></div><Link className="pos-secondary" to="/admin/cash">{cash ? 'Caja abierta · Ver caja' : 'Abrir caja'}</Link></header>
    {error && <p className="pos-error" role="alert">{error}</p>}
    {pending && <div className="pos-notice" role="status">Hay una venta pendiente de confirmar. Recupera su resultado antes de iniciar otra.<button disabled={busy} onClick={() => void pay()}>Consultar / reintentar venta</button></div>}
    {quote && !pending && <div className="pos-panel pos-section-title" aria-live="polite"><span>Subtotal {currency(quote.subtotal)} · Descuento automático {currency(quote.discount)}</span><strong className="pos-total">Total {currency(quote.total)}</strong></div>}
    <div className="pos-workspace"><section className="pos-panel"><h2>Buscar productos</h2><form className="pos-search" onSubmit={event => void find(event)}><label className="sr-only" htmlFor="pos-search">Nombre, SKU o código de barras</label><input id="pos-search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Escanea un código o escribe el nombre…" autoComplete="off" maxLength={128} /><button disabled={searching}>{searching ? 'Buscando…' : 'Buscar'}</button></form><p className="pos-muted">Lector USB o ingreso manual. Vinculación con la app móvil pendiente.</p>
      <div className="pos-products">{products.length === 0 ? <div className="pos-empty">Busca un producto para consultar su disponibilidad.</div> : products.map(product => <button className="pos-product" key={product.id} disabled={!product.available || busy || !!pending} onClick={() => add(product)}><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${product.id}/image`} name={product.name} /><span><strong>{product.name}</strong><small>{product.sku}{product.requires_prescription ? ' · Requiere receta' : ''}</small></span></span><span><strong>{currency(product.price)}</strong><small>{product.available ? `${product.available} disponibles · Agregar +` : 'Sin stock vendible'}</small></span></button>)}</div>
    </section><aside className="pos-panel pos-cart"><div className="pos-section-title"><h2>Venta actual</h2><span>{cart.reduce((sum, item) => sum + item.quantity, 0)} unidades</span></div>{!cart.length && <div className="pos-empty">Agrega productos para comenzar.</div>}{cart.map(item => <div className="pos-cart-row" key={item.product_id}><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${item.product_id}/image`} name={item.name} /><strong>{item.name}</strong></span><label>Cantidad<input aria-label={`Cantidad de ${item.name}`} type="number" min="1" max={item.available} step="1" value={item.quantity} disabled={busy || !!pending} onChange={event => { const quantity = Number(event.target.value); if (Number.isInteger(quantity) && quantity > 0 && quantity <= item.available) { setQuote(null); setCart(cart.map(row => row === item ? { ...row, quantity } : row)) } }} /></label><button className="pos-text-button" disabled={busy || !!pending} aria-label={`Quitar ${item.name}`} onClick={() => { setQuote(null); setCart(cart.filter(row => row !== item)) }}>Quitar</button></div>)}<p className="pos-muted">El servidor verifica el stock y aplica automáticamente el mejor precio al revisar el cobro.</p><button className="pos-primary" disabled={!cart.length || busy || !!pending} onClick={() => void review()}>{busy ? 'Verificando…' : 'Revisar y cobrar →'}</button></aside></div>
    <dialog className="pos-dialog" ref={dialog} onCancel={event => { if (busy || pending) event.preventDefault() }}><div className="pos-dialog-body"><div className="pos-section-title"><h2>Confirmar venta</h2><button disabled={busy || !!pending} onClick={() => dialog.current?.close()}>Volver al carrito</button></div>{quote && <><table><thead><tr><th>Producto</th><th>Cantidad</th><th>Precio final</th><th>Total</th></tr></thead><tbody>{quote.items.map(item => <tr key={item.product_id}><td><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${item.product_id}/image`} name={item.name} /><span>{item.name}<small>{item.promotion?.name ?? 'Precio base'}</small></span></span></td><td>{item.quantity}</td><td>{currency(item.price)}</td><td>{currency(item.total)}</td></tr>)}</tbody></table><div className="pos-payment"><label>Medio de pago<select value={payment === 'EFECTIVO' ? 'EFECTIVO' : 'TARJETA'} disabled={busy || !!pending} onChange={event => setPayment(event.target.value === 'EFECTIVO' ? 'EFECTIVO' : 'DEBITO')}><option value="EFECTIVO">Efectivo</option><option value="TARJETA">Tarjeta</option></select></label>{payment !== 'EFECTIVO' && <label>Tipo de tarjeta<select value={payment} disabled={busy || !!pending} onChange={event => setPayment(event.target.value as Payment)}><option value="DEBITO">Débito</option><option value="CREDITO">Crédito</option></select></label>}<p>Descuento automático: {currency(quote.discount)}</p><strong className="pos-total">Total {currency(quote.total)}</strong><p className="pos-muted">Confirma solo después de recibir el pago. No hay cobro bancario automático.</p><button disabled={busy} onClick={() => void pay()}>{busy ? 'Registrando…' : pending ? 'Reintentar la misma venta' : 'Confirmar pago y finalizar'}</button></div></>}{error && <p className="pos-error" role="alert">{error}</p>}</div></dialog>
    {receipt && <section className="pos-panel pos-receipt"><div className="pos-section-title"><h2>Venta registrada</h2><button onClick={() => window.print()}>Imprimir comprobante</button></div><h3>Farmacia Quilicura · {receipt.branch}</h3><p>{receipt.notice}</p><p>Venta {receipt.id}<br />{new Date(receipt.date).toLocaleString('es-CL')} · Cajero: {receipt.cashier}</p><table><thead><tr><th>Producto</th><th>Cantidad</th><th>Precio</th><th>Total</th></tr></thead><tbody>{receipt.items.map(item => <tr key={item.product_id}><td><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${item.product_id}/image`} name={item.name} /><span>{item.name}<small>{item.promotion?.name ?? 'Precio base'}</small></span></span></td><td>{item.quantity}</td><td>{currency(item.price)}</td><td>{currency(item.total)}</td></tr>)}</tbody></table><p>Descuento: {currency(receipt.discount)}</p><strong className="pos-total">Total: {currency(receipt.total)}</strong><p>Medio de pago: {paymentNames[receipt.payment]}</p></section>}
  </section>
}
