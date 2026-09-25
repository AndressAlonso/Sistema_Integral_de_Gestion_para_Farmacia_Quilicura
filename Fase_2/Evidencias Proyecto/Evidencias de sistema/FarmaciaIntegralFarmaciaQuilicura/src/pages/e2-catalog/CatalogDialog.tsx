import { useEffect, useRef, useState, type FormEvent } from 'react'
import ProductPhoto from './ProductPhoto'
import type { Category, Product, ProductInput } from './catalog.api'

type Props = {
  mode: 'product' | 'category'
  categories: Category[]
  product?: Product
  busy: boolean
  error: string
  onClose: () => void
  onProduct: (input: ProductInput, file: File | null, remove: boolean) => void
  onCategory: (name: string) => void
}

export default function CatalogDialog({ mode, categories, product, busy, error, onClose, onProduct, onCategory }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [validation, setValidation] = useState('')
  const [requiresPrescription, setRequiresPrescription] = useState(product?.requires_prescription ?? false)
  const [selection, setSelection] = useState<{ file: File; url: string } | null>(null)
  const [removeImage, setRemoveImage] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  useEffect(() => () => { if (selection) URL.revokeObjectURL(selection.url) }, [selection])
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
    const price = product?.price ?? text('price').replace(',', '.')
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
    }, selection?.file ?? null, removeImage)
  }

  return (
    <dialog ref={dialog} className="app-modal users-dialog users-dialog-fullscreen catalog-dialog"
      aria-labelledby="catalog-dialog-title" aria-busy={busy}
      onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
      <form onSubmit={submit} onChange={event => { if (!(event.target instanceof HTMLInputElement && event.target.type === 'file')) setValidation('') }}>
        <header className="users-dialog-heading">
          <div><h2 id="catalog-dialog-title">{isProduct ? (product ? 'Editar producto' : 'Nuevo producto') : 'Nueva categoría'}</h2>
            <p className="catalog-help">{isProduct ? 'Completa la ficha del producto para incorporarlo al catálogo.' : 'Organiza los productos de la farmacia.'}</p></div>
          <button type="button" className="users-close" aria-label="Cerrar formulario" disabled={busy} onClick={onClose}>×</button>
        </header>
        <fieldset className="users-fields" disabled={busy}>
          <legend className="sr-only">{isProduct ? 'Datos del producto' : 'Datos de la categoría'}</legend>
          <h3 className="users-form-section">Información general</h3>
          <label>Nombre *<input name="name" defaultValue={product?.name ?? ''} required maxLength={150} autoComplete="off" /></label>
          {isProduct && <>
            <label>SKU *<input name="sku" defaultValue={product?.sku ?? ''} required maxLength={64} autoComplete="off" /><small>Identificador único del producto.</small></label>
            <label>Categoría *<select name="category_id" required defaultValue={product?.category_id ?? ''}><option value="" disabled>Selecciona una categoría</option>
              {categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select></label>
            <label>{product ? 'Precio actual (CLP)' : 'Precio inicial (CLP) *'}<input name="price" required={!product} readOnly={!!product} defaultValue={product?.price ?? ''} inputMode="decimal" placeholder="Ej.: 1990,00" autoComplete="off" /><small>{product ? 'El cambio de precio se gestiona por separado con su historial.' : 'Sin separador de miles. Hasta dos decimales.'}</small></label>
            <label className="catalog-full">Descripción<textarea name="description" defaultValue={product?.description ?? ''} rows={3} /></label>
            <h3 className="users-form-section">Imagen principal</h3>
            <div className="catalog-full catalog-image-editor">
              <ProductPhoto src={removeImage ? null : selection?.url ?? product?.image_url} name={product?.name ?? 'producto'} large />
              <div className="catalog-image-controls">
                <label htmlFor="product-image">Seleccionar imagen</label>
                <input ref={fileInput} id="product-image" type="file" accept="image/jpeg,image/png,image/webp" aria-describedby="image-help"
                  onChange={event => {
                    const file = event.target.files?.[0]
                    if (!file) return
                    setValidation('')
                    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024 || !file.size) {
                      setSelection(null); event.target.value = ''
                      setValidation('Selecciona una imagen JPG, PNG o WebP de hasta 5 MB.'); return
                    }
                    setRemoveImage(false); setSelection({ file, url: URL.createObjectURL(file) })
                  }} />
                <small id="image-help">Opcional. JPG, PNG o WebP; máximo 5 MB y 20 megapíxeles.</small>
                {(selection || (product?.image_url && !removeImage)) && <button type="button" className="users-button" onClick={() => {
                  setSelection(null); setRemoveImage(true); if (fileInput.current) fileInput.current.value = ''
                }}>Quitar imagen</button>}
                {removeImage && <small>La imagen se quitará al guardar los cambios.</small>}
              </div>
            </div>
            <h3 className="users-form-section">Identificación y disponibilidad</h3>
            <label className="catalog-full">Códigos de barras<textarea name="barcodes" defaultValue={product?.barcodes.join('\n') ?? ''} rows={3} spellCheck={false} autoComplete="off" aria-describedby="barcode-help" />
              <small id="barcode-help">Opcional. Escribe un código por línea; se conservan los ceros iniciales.</small></label>
            <label className="users-checkbox"><input type="checkbox" name="is_active" defaultChecked={product?.is_active ?? true} />Producto activo</label>
            <label className="users-checkbox"><input type="checkbox" name="published_online" defaultChecked={product?.published_online ?? false} />Publicado en catálogo online</label>
            <label className="users-checkbox"><input type="checkbox" name="requires_prescription" checked={requiresPrescription} onChange={event => setRequiresPrescription(event.target.checked)} />Requiere receta</label>
            {requiresPrescription && <p className="catalog-full catalog-notice">Los productos con receta pueden mostrarse online; su compra es presencial.</p>}
          </>}
          <p className="catalog-full catalog-help">* Campos obligatorios.</p>
        </fieldset>
        {(validation || error) && <p className="users-error" role="alert">{validation || error}</p>}
        <footer className="users-dialog-actions">
          <button type="button" className="users-button" disabled={busy} onClick={onClose}>Cancelar</button>
          <button type="submit" className="users-button primary" disabled={busy}>{busy ? 'Guardando…' : isProduct ? (product ? 'Guardar cambios' : 'Crear producto') : 'Crear categoría'}</button>
        </footer>
      </form>
    </dialog>
  )
}
