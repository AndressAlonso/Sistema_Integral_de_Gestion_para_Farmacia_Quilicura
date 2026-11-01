import StoreIcon from './StoreIcon'
import Notification from '../../../components/Notification'
import { useState } from 'react'
import { useCart } from '../hooks/useCart'
import '../cart.css'

export default function AddToCartButton({ productId }: { productId: string }) {
  const { add } = useCart()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [failed, setFailed] = useState(false)
  async function submit() {
    setBusy(true); setMessage('')
    const error = await add(productId)
    setFailed(!!error)
    setMessage(error ?? 'Producto agregado al carrito.'); setBusy(false)
  }
  return <div className="cart-add"><button type="button" disabled={busy} onClick={() => { void submit() }}><span className="store-label-icon"><StoreIcon name="cart" />{busy ? 'Validando…' : 'Agregar al carrito'}</span></button><Notification message={message} kind={failed ? 'error' : 'success'} /></div>
}