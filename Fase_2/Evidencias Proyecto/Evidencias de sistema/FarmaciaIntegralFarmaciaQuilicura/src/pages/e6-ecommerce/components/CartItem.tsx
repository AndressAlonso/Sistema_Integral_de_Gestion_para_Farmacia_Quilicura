import { useId, useState, type FormEvent } from 'react'
import { useCart } from '../hooks/useCart'
import type { CartLine } from '../types/cart'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
export default function CartItem({ line }: { line: CartLine }) {
  const { change, remove } = useCart()
  const id = useId()
  const [quantity, setQuantity] = useState(String(line.quantity))
  const [error, setError] = useState('')
  function confirm(event: FormEvent) {
    event.preventDefault()
    const value = Number(quantity)
    if (!Number.isInteger(value) || value < 1 || value > 99) { setError('Ingresa entre 1 y 99 unidades enteras.'); return }
    setError(''); change(line.product_id, value)
  }
  return <li className="cart-item">
    <h2>{line.name ?? 'Producto no disponible'}</h2>
    {line.unit_price !== null && <p className="cart-unit-price">Precio actual: {money(line.unit_price)}</p>}
    {line.subtotal !== null && <p className="cart-subtotal">Subtotal: <strong>{money(line.subtotal)}</strong></p>}
    <form onSubmit={confirm}><label htmlFor={id}>Cantidad<input id={id} type="number" min="1" max="99" step="1" required value={quantity} onChange={e => setQuantity(e.target.value)} /></label><button type="submit">Actualizar cantidad</button></form>
    <button className="cart-remove" type="button" onClick={() => remove(line.product_id)} aria-label={`Quitar ${line.name ?? 'producto'}`}>Quitar producto</button>
    {line.local_available !== null && <p className="cart-availability">Disponibilidad local: {line.local_available} · Global: {line.global_available}</p>}
    {line.requires_transfer && <p className="cart-warning">Requiere transferencia. No confirma disponibilidad inmediata en la sucursal de retiro.</p>}
    {line.issues.map(issue => <p className="cart-error" key={issue}>{issue}</p>)}
    {error && <p role="alert" className="cart-error">{error}</p>}
  </li>
}
