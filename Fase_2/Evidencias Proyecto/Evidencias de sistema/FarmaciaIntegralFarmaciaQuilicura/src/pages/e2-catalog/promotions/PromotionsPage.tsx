import PaginatedTableBody from '../../../components/PaginatedTableBody'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { listCategories, listProducts } from '../catalog.api'
import type { Category, Product } from '../catalog.api'
import { listPromotions, savePromotion } from './promotions.api'
import type { Promotion } from './promotions.api'
import PromotionDialog, { type PromotionDraft } from './PromotionDialog'
import './promotions.css'

const blank: PromotionDraft = { name: '', kind: 'PERCENT', value: '', starts: '', ends: '', target: 'product', targetId: '', active: true }
function localDate(value: string) {
  const date = new Date(value)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
function status(row: Promotion) {
  if (!row.is_active) return 'Desactivada'
  const now = Date.now()
  if (now < Date.parse(row.starts_at)) return 'Programada'
  if (now >= Date.parse(row.ends_at)) return 'Finalizada'
  return 'Vigente'
}
export default function PromotionsPage() {
  const [rows, setRows] = useState<Promotion[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [form, setForm] = useState(blank)
  const [editing, setEditing] = useState<string>()
  const [editorOpen, setEditorOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([listPromotions(), listProducts(), listCategories()]).then(([promotions, items, groups]) => {
      if (active) { setRows(promotions); setProducts(items); setCategories(groups) }
    }).catch(err => { if (active) setError(err instanceof Error ? err.message : 'No se pudo cargar la información.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  function closeEditor() {
    if (busy) return
    setEditorOpen(false); setEditing(undefined); setForm(blank); setError('')
  }
  function create() {
    setEditing(undefined); setForm(blank); setError(''); setNotice(''); setEditorOpen(true)
  }
  function edit(row: Promotion) {
    setEditing(row.id); setError(''); setNotice(''); setEditorOpen(true)
    setForm({ name: row.name, kind: row.kind, value: row.value, starts: localDate(row.starts_at), ends: localDate(row.ends_at), target: row.product_id ? 'product' : 'category', targetId: row.product_id ?? row.category_id ?? '', active: row.is_active })
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy) return; setError(''); setNotice('')
    const start = new Date(form.starts), end = new Date(form.ends)
    if (!form.name.trim() || !form.targetId || !Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || end <= start) {
      setError('Completa los datos y selecciona un término posterior al inicio.'); return
    }
    setBusy(true)
    try {
      const saved = await savePromotion({ name: form.name.trim(), kind: form.kind, value: form.value,
        starts_at: start.toISOString(), ends_at: end.toISOString(), product_id: form.target === 'product' ? form.targetId : null,
        category_id: form.target === 'category' ? form.targetId : null, is_active: form.active }, editing)
      setRows(previous => [saved, ...previous.filter(row => row.id !== saved.id)])
      setEditorOpen(false); setEditing(undefined); setForm(blank); setNotice('Promoción guardada. Durante su vigencia se aplicará en la tienda y en ventas cuando ofrezca el mejor precio.')
    } catch (err) { setError(err instanceof Error ? err.message : 'No se pudo guardar la promoción.') }
    finally { setBusy(false) }
  }
  return <main className="promotions-page">
    <header className="promotions-heading"><div><p className="promotions-kicker">CATÁLOGO</p><h1>Promociones</h1><p>Configura descuentos por producto o categoría.</p></div><button type="button" className="promotions-primary" disabled={loading || busy} onClick={create}>Nueva promoción</button></header>
    <p className="promotions-alert">Los descuentos no se acumulan. Se aplica únicamente la promoción vigente que deje el menor precio final. Un precio fijo es el precio final del producto.</p>
    {error && !editorOpen && <p role="alert" className="promotions-error">{error}</p>}
    {notice && <p role="status" className="promotions-alert">{notice}</p>}
    {loading ? <p role="status">Cargando promociones…</p> : <>
      {editorOpen && <PromotionDialog form={form} setForm={setForm} products={products} categories={categories} editing={!!editing} busy={busy} error={error} onSubmit={submit} onClose={closeEditor} />}
      <section className="promotions-panel"><h2>Promociones registradas</h2>{rows.length === 0 ? <p>No hay promociones registradas.</p> : <div className="promotions-table"><table className="responsive-admin-table"><thead><tr><th>Nombre y destino</th><th>Descuento</th><th>Vigencia</th><th>Estado</th><th>Acción</th></tr></thead><PaginatedTableBody total={rows.length} columns={5} labels={["Nombre y destino", "Descuento", "Vigencia", "Estado", "Acción"]}>{rows.map(row => <tr key={row.id}>
        <td><strong>{row.name}</strong><small>{row.product_id ? products.find(item => item.id === row.product_id)?.name ?? 'Producto' : categories.find(item => item.id === row.category_id)?.name ?? 'Categoría'}</small></td>
        <td>{row.kind === 'PERCENT' ? `${row.value}%` : `$${Number(row.value).toLocaleString('es-CL')}`}<small>{row.kind === 'PERCENT' ? 'Porcentaje' : 'Precio final fijo'}</small></td>
        <td>{new Date(row.starts_at).toLocaleString('es-CL')}<small>Hasta {new Date(row.ends_at).toLocaleString('es-CL')}</small></td><td>{status(row)}</td><td><button disabled={busy} onClick={() => edit(row)}>Editar</button></td>
      </tr>)}</PaginatedTableBody></table></div>}</section>
    </>}
  </main>
}
