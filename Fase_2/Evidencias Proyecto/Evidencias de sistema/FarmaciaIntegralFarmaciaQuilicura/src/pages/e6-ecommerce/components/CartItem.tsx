import Notification from '../../../components/Notification'
import { useId, useState } from 'react'
import ProductPhoto from '../../e2-catalog/ProductPhoto'
import { useCart } from '../hooks/useCart'
import type { CartLine } from '../types/cart'
import PromotionPrice from './PromotionPrice'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
export default function CartItem({ line }: { line: CartLine }) {
  const { change, remove } = useCart()
  const id = useId()
  const [quantity, setQuantity] = useState(String(line.quantity))
  const [error, setError] = useState('')
  function confirm() {
    const value = Number(quantity)
    if (!Number.isInteger(value) || value < 1 || value > 99) { setError('Ingresa entre 1 y 99 unidades enteras.'); return }
    setError(''); if (value !== line.quantity) change(line.product_id, value)
  }
  return <li className="cart-item">
    <div className="cart-item-product">
    <ProductPhoto src={`/api/ecommerce/products/${encodeURIComponent(line.product_id)}/image`} name={line.name ?? 'producto'} />
    <div className="cart-item-description">
    <h2>{line.name ?? 'Producto no disponible'}</h2>
    {line.unit_price !== null && <PromotionPrice price={line.unit_price} basePrice={line.base_unit_price} discount={line.unit_discount} promotion={line.promotion} />}
    {line.subtotal !== null && <p className="cart-subtotal">Subtotal: <strong>{money(line.subtotal)}</strong></p>}
    </div>
    </div>
    <div className="cart-item-controls">
      <div><label htmlFor={id}>Cantidad</label><div className="cart-quantity-stepper">
        <button type="button" aria-label={`Reducir cantidad de ${line.name ?? 'producto'}`} disabled={Number(quantity) <= 1} onClick={() => { const next = Math.max(1, (Number(quantity) || line.quantity) - 1); setQuantity(String(next)); setError(''); change(line.product_id, next) }}>−</button>
        <input id={id} aria-label={`Cantidad de ${line.name ?? 'producto'}`} type="number" min="1" max="99" step="1" required value={quantity} onChange={e => setQuantity(e.target.value)} onBlur={confirm} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); confirm() } }} />
        <button type="button" aria-label={`Aumentar cantidad de ${line.name ?? 'producto'}`} disabled={Number(quantity) >= 99} onClick={() => { const next = Math.min(99, (Number(quantity) || line.quantity) + 1); setQuantity(String(next)); setError(''); change(line.product_id, next) }}>+</button>
      </div></div>
      <button className="cart-remove cart-remove-compact" type="button" onClick={() => remove(line.product_id)} aria-label={`Quitar ${line.name ?? 'producto'}`}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7" /></svg>Quitar</button>
    </div>
    {line.local_available !== null && <p className="cart-availability">Disponibilidad local: {line.local_available} · Global: {line.global_available}</p>}
    {line.requires_transfer && <p className="cart-warning">Requiere transferencia. No confirma disponibilidad inmediata en la sucursal de retiro.</p>}
    {line.issues.map(issue => <p className="cart-error" key={issue}>{issue}</p>)}
    {error && <Notification message={error} kind="error" />}
  </li>
}
