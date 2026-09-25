import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Category, ProductInput } from './catalog.api'

type Props = {
  mode: 'product' | 'category'
  categories: Category[]
  busy: boolean
  error: string
  onClose: () => void
  onProduct: (input: ProductInput) => void
  onCategory: (name: string) => void
}

export default function CatalogDialog({ mode, categories, busy, error, onClose, onProduct, onCategory }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [validation, setValidation] = useState('')
  const [requiresPrescription, setRequiresPrescription] = useState(false)
  const isProduct = mode === 'product'
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { if (element?.open) element.close() }
  }, [])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setValidation('')
    const data = new FormData(event.currentTarget)
    const text = (key: string) => String(data.get(key) ?? '').trim()
    const name = text('name')
    if (!name) { setValidation('Escribe un nombre válido.'); return }
    if (!isProduct) { onCategory(name); return }
    const sku = text('sku')
    const price = text('price').replace(',', '.')
    if (!sku) { setValidation('Escribe un SKU válido.'); return }
    if (!/^\d{1,12}(\.\d{1,2})?$/.test(price)) {
      setValidation('Ingresa un precio desde 0, menor a un billón, con hasta dos decimales.'); return
    }
    const barcodes = text('barcodes').split(/\r?\n/).map(code => code.trim()).filter(Boolean)
    if (barcodes.some(code => code.length > 128)) {
      setValidation('Cada código de barras admite hasta 128 caracteres.'); return
    }
    if (new Set(barcodes).size !== barcodes.length) {
      setValidation('Hay códigos de barras repetidos en el formulario.'); return
    }
    if (!categories.some(category => category.id === text('category_id'))) {
      setValidation('Selecciona una categoría válida.'); return
    }
    onProduct({
      name, sku, price, description: text('description'), category_id: text('category_id'),
      barcodes, requires_prescription: requiresPrescription,
      is_active: data.has('is_active'), published_online: data.has('published_online'),
    })
  }

  return (
    <dialog ref={dialog} className="app-modal users-dialog users-dialog-fullscreen catalog-dialog"
      aria-labelledby="catalog-dialog-title" aria-busy={busy}
      onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
      <form onSubmit={submit} onChange={() => setValidation('')}>
        <header className="users-dialog-heading">
          <div><h2 id="catalog-dialog-title">{isProduct ? 'Nuevo producto' : 'Nueva categoría'}</h2>
            <p className="catalog-help">{isProduct ? 'Completa la ficha del producto para incorporarlo al catálogo.' : 'Organiza los productos de la farmacia.'}</p></div>
          <button type="button" className="users-close" aria-label="Cerrar formulario" disabled={busy} onClick={onClose}>×</button>
        </header>
        <fieldset className="users-fields" disabled={busy}>
          <legend className="sr-only">{isProduct ? 'Datos del producto' : 'Datos de la categoría'}</legend>
          <h3 className="users-form-section">Información general</h3>
          <label>Nombre *<input name="name" required maxLength={150} autoComplete="off" /></label>
          {isProduct && <>
            <label>SKU *<input name="sku" required maxLength={64} autoComplete="off" /><small>Identificador único del producto.</small></label>
            <label>Categoría *<select name="category_id" required defaultValue=""><option value="" disabled>Selecciona una categoría</option>
              {categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select></label>
            <label>Precio inicial (CLP) *<input name="price" required inputMode="decimal" placeholder="Ej.: 1990,00" autoComplete="off" /><small>Sin separador de miles. Hasta dos decimales.</small></label>
            <label className="catalog-full">Descripción<textarea name="description" rows={3} /></label>
            <h3 className="users-form-section">Identificación y disponibilidad</h3>
            <label className="catalog-full">Códigos de barras<textarea name="barcodes" rows={3} spellCheck={false} autoComplete="off" aria-describedby="barcode-help" />
              <small id="barcode-help">Opcional. Escribe un código por línea; se conservan los ceros iniciales.</small></label>
            <label className="users-checkbox"><input type="checkbox" name="is_active" defaultChecked />Producto activo</label>
            <label className="users-checkbox"><input type="checkbox" name="published_online" />Publicado en catálogo online</label>
            <label className="users-checkbox"><input type="checkbox" name="requires_prescription" checked={requiresPrescription} onChange={event => setRequiresPrescription(event.target.checked)} />Requiere receta</label>
            {requiresPrescription && <p className="catalog-full catalog-notice">Los productos con receta pueden mostrarse online; su compra es presencial.</p>}
          </>}
          <p className="catalog-full catalog-help">* Campos obligatorios.</p>
        </fieldset>
        {(validation || error) && <p className="users-error" role="alert">{validation || error}</p>}
        <footer className="users-dialog-actions">
          <button type="button" className="users-button" disabled={busy} onClick={onClose}>Cancelar</button>
          <button type="submit" className="users-button primary" disabled={busy}>{busy ? 'Guardando…' : isProduct ? 'Crear producto' : 'Crear categoría'}</button>
        </footer>
      </form>
    </dialog>
  )
}
