import Notification from '../../components/Notification'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Product, ProductPriceInput } from './catalog.api'

type Props = {
  product: Product
  busy: boolean
  error: string
  onClose: () => void
  onSave: (input: ProductPriceInput) => void
}

const currency = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

export default function ProductPriceDialog({
  product,
  busy,
  error,
  onClose,
  onSave,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [validation, setValidation] = useState('')
  const [newPrice, setNewPrice] = useState('')

  useEffect(() => {
    const element = dialog.current
    element?.showModal()

    return () => {
      if (element?.open) element.close()
    }
  }, [])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return

    setValidation('')
    const data = new FormData(event.currentTarget)
    const price = String(data.get('price') ?? '')
      .trim()
      .replace(',', '.')

    if (!/^\d{1,12}(\.\d{1,2})?$/.test(price)) {
      setValidation(
        'Ingresa un precio desde 0, menor que un billón y con hasta dos decimales.',
      )
      return
    }

    if (Number(price) === Number(product.price)) {
      setValidation('El nuevo precio debe ser diferente del actual.')
      return
    }

    onSave({
      price,
      expected_price: product.price,
    })
  }

  return (
    <dialog
      ref={dialog}
      className="app-modal users-dialog catalog-dialog compact-dialog"
      aria-labelledby="product-price-title"
      aria-busy={busy}
      onCancel={event => {
        event.preventDefault()
        if (!busy) onClose()
      }}
    >
      <form onSubmit={submit}>
        <header className="users-dialog-heading">
          <div>
            <h2 id="product-price-title">Cambiar precio</h2>
            <p className="catalog-help">
              {product.name} · SKU: {product.sku}
            </p>
          </div>
          <button
            type="button"
            className="users-close"
            aria-label="Cerrar cambio de precio"
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <fieldset className="users-fields" disabled={busy}>
          <legend className="sr-only">Precio del producto</legend>
          <h3 className="users-form-section">Precio base</h3>

          <label>
            Precio actual (CLP)
            <input
              value={currency.format(Number(product.price))}
              readOnly
            />
          </label>

          <label>
            Nuevo precio (CLP) *
            <input
              name="price"
              required
              inputMode="decimal"
              autoComplete="off"
              maxLength={15}
              placeholder="Ej.: 2490,00"
              aria-describedby="product-price-help"
              value={newPrice}
              onChange={event => { setNewPrice(event.target.value); setValidation('') }}
            />
            <small id="product-price-help">
              Sin separador de miles. Hasta dos decimales.
            </small>
          </label>

          <p className="catalog-full catalog-notice">
            {newPrice.trim() && Number.isFinite(Number(newPrice.replace(',', '.')))
              ? `Cambiarás el precio base de ${currency.format(Number(product.price))} a ${currency.format(Number(newPrice.replace(',', '.')))}.`
              : 'Revisa el precio actual y el nuevo antes de confirmar.'}
            {' '}Se aplicará en la tienda y el POS. El cambio quedará registrado con fecha y usuario.
          </p>
        </fieldset>

        {error && <Notification message={error} kind="error" />}{validation && <p className="users-error" role="alert">{validation}</p>}

        <footer className="users-dialog-actions">
          <button
            type="button"
            className="users-button"
            disabled={busy}
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="users-button primary"
            disabled={busy}
          >
            {busy ? 'Guardando…' : 'Confirmar cambio de precio'}
          </button>
        </footer>
      </form>
    </dialog>
  )
}