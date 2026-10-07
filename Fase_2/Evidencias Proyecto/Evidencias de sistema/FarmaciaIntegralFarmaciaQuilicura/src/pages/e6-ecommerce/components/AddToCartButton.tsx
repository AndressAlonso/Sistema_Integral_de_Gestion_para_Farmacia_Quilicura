import { useState } from 'react'
import { useCart } from '../hooks/useCart'
import '../cart.css'

export default function AddToCartButton({ productId }: { productId: string }) {
  const { add } = useCart()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function submit() {
    setBusy(true); setMessage('')
    const error = await add(productId)
    setMessage(error ?? 'Producto agregado al carrito.'); setBusy(false)
  }
  return <div className="cart-add"><button type="button" disabled={busy} onClick={() => { void submit() }}>{busy ? 'Validando…' : 'Agregar al carrito'}</button><p role="status">{message}</p></div>
}
