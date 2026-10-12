import { useEffect, useRef, useState, type ReactNode } from 'react'
import { CartContext } from '../hooks/useCart'
import { validateCart } from '../services/cart.api'
import type { CartDraft, CartValidation } from '../types/cart'

const key = 'sigfq_cart_v1'
const empty: CartDraft = { version: 1, items: [], pickup_branch_id: null }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function restore(): CartDraft {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) ?? 'null')
    if (!value || value.version !== 1 || !Array.isArray(value.items) || value.items.length > 50
      || !(value.pickup_branch_id === null || (typeof value.pickup_branch_id === 'string' && uuid.test(value.pickup_branch_id)))) return empty
    const items: CartDraft['items'] = []
    for (const item of value.items) {
      if (!item || typeof item.product_id !== 'string' || !uuid.test(item.product_id) || !Number.isInteger(item.quantity)
        || item.quantity < 1 || item.quantity > 99 || items.some(i => i.product_id === item.product_id)) return empty
      items.push({ product_id: item.product_id, quantity: item.quantity })
    }
    return { version: 1, items, pickup_branch_id: value.pickup_branch_id }
  } catch { return empty }
}

export default function CartProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState<CartDraft>(restore)
  const [validation, setValidation] = useState<CartValidation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const current = useRef(draft)
  const adding = useRef(false)
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => {
    try { sessionStorage.setItem(key, JSON.stringify(draft)) } catch { /* El carrito continúa en memoria si el navegador bloquea almacenamiento. */ }
    let active = true
    void validateCart(draft).then(result => { if (active) setValidation(result) })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'No pudimos validar el carrito.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [draft, attempt])
  function update(next: CartDraft) {
    current.current = next
    setDraft(next); setValidation(null); setLoading(true); setError('')
  }
  async function add(id: string): Promise<string | null> {
    if (adding.current) return 'Espera mientras confirmamos el producto.'
    const original = current.current
    const existing = original.items.find(i => i.product_id === id)
    if (!existing && original.items.length >= 50) return 'El carrito admite hasta 50 productos distintos.'
    if (existing && existing.quantity >= 99) return 'El máximo por producto es 99 unidades.'
    const next: CartDraft = { ...original, items: existing ? original.items.map(i => i.product_id === id ? { ...i, quantity: i.quantity + 1 } : i) : [...original.items, { product_id: id, quantity: 1 }] }
    adding.current = true
    try {
      const result = await validateCart(next)
      const line = result.items.find(i => i.product_id === id)
      if (!line?.valid) return line?.issues.join(' ') || 'No se pudo agregar el producto.'
      if (current.current !== original || !mounted.current) return 'El carrito cambió. Intenta agregar el producto nuevamente.'
      update(next)
      return null
    } catch (cause) { return cause instanceof Error ? cause.message : 'No pudimos agregar el producto.' }
    finally { adding.current = false }
  }
  return <CartContext.Provider value={{ draft, validation, loading, error, add,
    change: (id, quantity) => { if (Number.isInteger(quantity) && quantity >= 1 && quantity <= 99) update({ ...current.current, items: current.current.items.map(i => i.product_id === id ? { ...i, quantity } : i) }) },
    remove: id => update({ ...current.current, items: current.current.items.filter(i => i.product_id !== id) }),
    selectBranch: id => update({ ...current.current, pickup_branch_id: id || null }),
    refresh: () => { setValidation(null); setLoading(true); setError(''); setAttempt(a => a + 1) },
  }}>{children}</CartContext.Provider>
}
