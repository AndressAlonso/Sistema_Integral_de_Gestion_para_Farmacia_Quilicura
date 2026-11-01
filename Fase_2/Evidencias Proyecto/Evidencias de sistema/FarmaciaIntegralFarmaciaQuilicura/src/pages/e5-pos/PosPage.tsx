import Notification from '../../components/Notification'
import PosPrice from './PosPrice'
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
import type { ScannerLink } from './scanner.api'
import useScannerReads, { type ScannerAddResult } from './useScannerReads'

export default function PosPage() {
  const { user } = useOutletContext<AuthSession>()
  const [scannerLink, setScannerLink] = useState<ScannerLink | null>(null)
  const [search, setSearch] = useState('')
  const [showSales, setShowSales] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [cart, setCartState] = useState<Array<Item & { name: string; available: number }>>([])
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

  const cartRef = useRef(cart)

  function setCart(next: typeof cart) {
    cartRef.current = next
    setCartState(next)
  }

  const { scannerNotice, scannerError } = useScannerReads({
    linkId: scannerLink?.id ?? null,
    canReceive: () =>
      !busy &&
      !pending &&
      !locked.current &&
      !showSales &&
      !dialog.current?.open,
    onProduct: add,
  })

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
  function add(product: Product): ScannerAddResult {
    if (
      pending ||
      busy ||
      locked.current ||
      showSales ||
      dialog.current?.open
    ) {
      return 'paused'
    }

    const current = cartRef.current
    const row = current.find(item => item.product_id === product.id)

    if ((row?.quantity ?? 0) >= product.available) {
      setError('No puedes superar el stock vendible disponible.')
      return 'rejected'
    }

    setQuote(null)
    setError('')

    setCart(
      row
        ? current.map(item =>
          item === row
            ? {
              ...item,
              available: product.available,
              quantity: item.quantity + 1,
            }
            : item,
        )
        : [
          ...current,
          {
            product_id: product.id,
            name: product.name,
            available: product.available,
            quantity: 1,
          },
        ],
    )

    return 'added'
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

  function cartPrice(productId: string) {
    const line = quote?.items.find(item => item.product_id === productId)
    return line ? <PosPrice price={line.price} basePrice={line.base_price} promotion={line.promotion} /> : <small>Verificando precio…</small>
  }

  return <section className="pos-page pos-sales-page">
    <header className="pos-heading">
      <div><p className="pos-eyebrow">VENTA EN SUCURSAL</p><h1>Punto de venta</h1><p>{user.branch_name} · {user.name}</p></div>
      <div className="pos-header-actions"><button className="pos-secondary" onClick={() => setShowSales(true)} title="Ventas, comprobantes y devoluciones">Historial de ventas</button><ScannerLinkDialog
      userName={user.name}
      branchName={user.branch_name}
      onLinkChange={setScannerLink}
    /><Link className={`pos-secondary pos-cash-link${cash ? ' is-open' : ''}`} to="/admin/cash">{cash ? 'Caja abierta · Ver caja' : 'Abrir caja'}</Link></div>
    </header>
    {showSales && <SalesDialog userId={user.id} canReverse={user.roles.includes('ADMINISTRADOR') && user.permissions.includes('ventas.reversar')} onClose={() => setShowSales(false)} onReceipt={setReceipt} />}
    {scannerNotice && (
      <Notification message={scannerNotice} kind="info" />
    )}

    {scannerError && (
      <Notification kind="error" message={`Escáner: ${scannerError}`} />
    )}
    {error && <Notification message={error} kind="error" />}
    {pending && <div className="pos-notice" role="status">Hay una venta pendiente de confirmar. Recupera su resultado antes de iniciar otra.<button disabled={busy} onClick={() => void pay()}>Consultar / reintentar venta</button></div>}
    <div className="pos-workspace"><section className="pos-panel pos-catalog-panel"><div className="pos-section-title"><h2>Productos</h2><span className="pos-section-caption">Busca y agrega a la venta</span></div><form className="pos-search" onSubmit={event => void find(event)}><label className="sr-only" htmlFor="pos-search">Nombre, SKU o código de barras</label><input id="pos-search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Escanea un código o escribe el nombre…" autoComplete="off" maxLength={128} /><button disabled={searching}>{searching ? 'Buscando…' : 'Buscar'}</button></form><p className="pos-muted">
      {scannerLink
        ? 'Teléfono vinculado a esta caja.'
        : 'Busca por nombre, SKU o escanea el código de barras.'}
    </p>
      <div className="pos-products">{products.length === 0 ? <div className="pos-empty"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg><strong>Encuentra el próximo producto</strong><span>Consulta su precio y disponibilidad desde el buscador.</span></div> : products.map(product => <button className="pos-product" key={product.id} disabled={!product.available || busy || !!pending} onClick={() => add(product)}><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${product.id}/image`} name={product.name} /><span><strong>{product.name}</strong><small>{product.sku}{product.requires_prescription ? ' · Requiere receta' : ''}</small></span></span><span className="pos-product-pricing"><PosPrice price={product.price} basePrice={product.base_price} promotion={product.promotion} /><small>{product.available ? `${product.available} disponibles · Agregar +` : 'Sin stock vendible'}</small></span></button>)}</div>
    </section><aside className="pos-panel pos-cart"><div className="pos-section-title"><h2>Venta actual</h2><span className="pos-unit-count">{cart.reduce((sum, item) => sum + item.quantity, 0)} unidades</span></div><div className="pos-cart-items">{!cart.length && <div className="pos-empty"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 3h2l3 12h10l3-9H6" strokeLinecap="round" strokeLinejoin="round" /><circle cx="9" cy="19" r="1" /><circle cx="18" cy="19" r="1" /></svg><strong>Tu venta comienza aquí</strong><span>Los productos que agregues aparecerán en este espacio.</span></div>}{cart.map(item => <div className="pos-cart-row" key={item.product_id}><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${item.product_id}/image`} name={item.name} /><span><strong>{item.name}</strong>{cartPrice(item.product_id)}</span></span><label>Cantidad<input aria-label={`Cantidad de ${item.name}`} type="number" min="1" max={item.available} step="1" value={item.quantity} disabled={busy || !!pending} onChange={event => { const quantity = Number(event.target.value); if (Number.isInteger(quantity) && quantity > 0 && quantity <= item.available) { setQuote(null); setCart(cart.map(row => row === item ? { ...row, quantity } : row)) } }} /></label><button className="pos-text-button" disabled={busy || !!pending} aria-label={`Quitar ${item.name}`} onClick={() => { setQuote(null); setCart(cart.filter(row => row !== item)) }}>Quitar</button></div>)}</div><div className="pos-cart-checkout"><div className="pos-summary" aria-live="polite">{quote && !pending && cart.length > 0 && <><div><span>Subtotal</span><span>{currency(quote.subtotal)}</span></div>{Number(quote.discount) > 0 && <div className="pos-summary-saving"><span>Ahorro por promociones</span><strong>−{currency(quote.discount)}</strong></div>}</>}<div className="pos-summary-total"><strong>Total a pagar</strong><strong>{pending ? "Por confirmar" : !cart.length ? currency(0) : quote ? currency(quote.total) : "Calculando…"}</strong></div></div><button className="pos-primary" disabled={!cart.length || busy || !!pending} onClick={() => void review()}>{busy ? 'Verificando…' : 'Revisar y cobrar →'}</button><p className="pos-checkout-caption">Promociones aplicadas automáticamente.</p></div></aside></div>
    <dialog className="pos-dialog" ref={dialog} onCancel={event => { if (busy || pending) event.preventDefault() }}><div className="pos-dialog-body"><div className="pos-section-title"><h2>Confirmar venta</h2><button disabled={busy || !!pending} onClick={() => dialog.current?.close()}>Volver al carrito</button></div>{quote && <><table><thead><tr><th>Producto</th><th>Cantidad</th><th>Precio final</th><th>Total</th></tr></thead><tbody>{quote.items.map(item => <tr key={item.product_id}><td><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${item.product_id}/image`} name={item.name} /><span>{item.name}<small>{item.sku}</small></span></span></td><td>{item.quantity}</td><td><PosPrice price={item.price} basePrice={item.base_price} promotion={item.promotion} /></td><td>{currency(item.total)}</td></tr>)}</tbody></table><div className="pos-payment"><label>Medio de pago<select value={payment === 'DEBITO' || payment === 'CREDITO' ? 'TARJETA' : payment} disabled={busy || !!pending} onChange={event => setPayment(event.target.value === 'TARJETA' ? 'DEBITO' : event.target.value as Payment)}><option value="EFECTIVO">Efectivo</option><option value="TARJETA">Tarjeta</option><option value="TRANSFERENCIA">Transferencia</option></select></label>{(payment === 'DEBITO' || payment === 'CREDITO') && <label>Tipo de tarjeta<select value={payment} disabled={busy || !!pending} onChange={event => setPayment(event.target.value as Payment)}><option value="DEBITO">Débito</option><option value="CREDITO">Crédito</option></select></label>}<p className={Number(quote.discount) > 0 ? 'pos-promotion-total' : undefined}>Ahorro total por promociones: <strong>{currency(quote.discount)}</strong></p><strong className="pos-total">Total {currency(quote.total)}</strong><p className="pos-muted">Confirma solo después de recibir el pago. No hay cobro bancario automático.</p><button disabled={busy} onClick={() => void pay()}>{busy ? 'Registrando…' : pending ? 'Reintentar la misma venta' : 'Confirmar pago y finalizar'}</button></div></>}{error && <Notification message={error} kind="error" />}</div></dialog>
    {receipt && <section className="pos-panel pos-receipt"><div className="pos-section-title"><h2>Venta registrada</h2><button onClick={() => window.print()}>Imprimir comprobante</button></div><h3>Farmacia Quilicura · {receipt.branch}</h3><p>{receipt.notice}</p><p>Venta {receipt.id}<br />{new Date(receipt.date).toLocaleString('es-CL')} · Cajero: {receipt.cashier}</p><table><thead><tr><th>Producto</th><th>Cantidad</th><th>Precio</th><th>Total</th></tr></thead><tbody>{receipt.items.map(item => <tr key={item.product_id}><td><span className="pos-product-info"><ProductPhoto src={`/api/pos/products/${item.product_id}/image`} name={item.name} /><span>{item.name}<small>{item.sku}</small></span></span></td><td>{item.quantity}</td><td><PosPrice price={item.price} basePrice={item.base_price} promotion={item.promotion} /></td><td>{currency(item.total)}</td></tr>)}</tbody></table><p className={Number(receipt.discount) > 0 ? 'pos-promotion-total' : undefined}>Ahorro total por promociones: <strong>{currency(receipt.discount)}</strong></p><strong className="pos-total">Total: {currency(receipt.total)}</strong><p>Medio de pago: {paymentNames[receipt.payment]}</p></section>}
  </section>
}
