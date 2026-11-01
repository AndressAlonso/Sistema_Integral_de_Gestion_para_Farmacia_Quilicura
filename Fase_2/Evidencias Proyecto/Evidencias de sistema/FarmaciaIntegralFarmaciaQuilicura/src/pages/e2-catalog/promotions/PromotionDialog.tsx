import Notification from '../../../components/Notification'
import { useEffect, useRef, type Dispatch, type FormEvent, type SetStateAction } from 'react'
import type { Category, Product } from '../catalog.api'
import type { PromotionInput } from './promotions.api'

export type PromotionDraft = { name: string; kind: PromotionInput['kind']; value: string; starts: string; ends: string; target: string; targetId: string; active: boolean }
type Props = { form: PromotionDraft; setForm: Dispatch<SetStateAction<PromotionDraft>>; products: Product[]; categories: Category[]; editing: boolean; busy: boolean; error: string; onSubmit: (event: FormEvent) => Promise<void>; onClose: () => void }

export default function PromotionDialog({ form, setForm, products, categories, editing, busy, error, onSubmit, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => { if (element?.open) element.close() }
  }, [])
  return <dialog ref={dialog} className="app-modal promotions-dialog" aria-labelledby="promotion-dialog-title" aria-busy={busy}
    onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
    <header className="promotions-dialog-heading">
      <div><h2 id="promotion-dialog-title">{editing ? 'Editar promoción' : 'Crear promoción'}</h2><p>Completa los datos y revisa el efecto antes de confirmar.</p></div>
      <button type="button" aria-label="Cerrar promoción" disabled={busy} onClick={onClose}>×</button>
    </header>
    {error && <Notification message={error} kind="error" />}
    <form onSubmit={event => void onSubmit(event)}><fieldset disabled={busy}>
          <p id="promotion-target-help" className="promotions-alert">
            {form.target === 'category'
              ? 'Aplica a los productos de la categoría elegida. No necesitas seleccionar un producto.'
              : 'Aplica únicamente al producto elegido. No necesitas seleccionar una categoría.'}
          </p><div className="promotions-grid">
          <label>Nombre<input required maxLength={150} value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} /></label>
          <label>Tipo<select value={form.kind} onChange={event => setForm({ ...form, kind: event.target.value as PromotionInput['kind'] })}><option value="PERCENT">Porcentaje</option><option value="FIXED_PRICE">Precio fijo</option></select></label>
          <label>{form.kind === 'PERCENT' ? 'Porcentaje (%)' : 'Precio final ($)'}<input required type="number" min="0" max={form.kind === 'PERCENT' ? '100' : '999999999999.99'} step="0.01" value={form.value} onChange={event => setForm({ ...form, value: event.target.value })} /></label>
          <label>Aplicar a<select aria-describedby="promotion-target-help" value={form.target} onChange={event => setForm({ ...form, target: event.target.value, targetId: '' })}><option value="product">Producto específico</option><option value="category">Categoría completa</option></select></label>
          <label>{form.target === 'product' ? 'Producto' : 'Categoría'}<select key={form.target} required aria-describedby="promotion-target-help" value={form.targetId} onChange={event => setForm({ ...form, targetId: event.target.value })}><option value="">{form.target === 'product' ? 'Selecciona un producto…' : 'Selecciona una categoría…'}</option>{form.target === 'product' ? products.filter(row => row.is_active || row.id === form.targetId).map(row => <option key={row.id} value={row.id}>{row.name} · {row.sku}</option>) : categories.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
          <label>Inicio (hora local)<input required type="datetime-local" value={form.starts} onChange={event => setForm({ ...form, starts: event.target.value })} /></label>
          <label>Término (hora local)<input required type="datetime-local" value={form.ends} onChange={event => setForm({ ...form, ends: event.target.value })} /></label>
          <label className="promotions-check"><input type="checkbox" checked={form.active} onChange={event => setForm({ ...form, active: event.target.checked })} />Habilitada</label>
        </div><section className="promotions-alert" aria-label="Revisión de la promoción">
          <p><strong>Antes de confirmar</strong></p>
          <p>{form.active ? 'La promoción quedará habilitada durante las fechas indicadas.' : 'La promoción quedará deshabilitada y no se aplicará a ventas nuevas.'}</p>
          <p>Destino: {form.target === 'product' ? products.find(item => item.id === form.targetId)?.name ?? 'Selecciona un producto' : categories.find(item => item.id === form.targetId)?.name ?? 'Selecciona una categoría'}{form.target === 'category' ? ' · Afecta a todos sus productos.' : '.'}</p>
          <p>{form.kind === 'PERCENT' ? `Descuento: ${form.value || '—'} %.` : `Precio final fijo: $${form.value || '—'}.`} Se aplicará en tienda y POS cuando ofrezca el mejor precio.</p>
        </section><div className="promotions-actions"><button type="button" disabled={busy} onClick={onClose}>Cancelar</button><button type="submit" className="promotions-primary">{busy ? 'Guardando…' : 'Confirmar promoción'}</button></div></fieldset></form>
  </dialog>
}
