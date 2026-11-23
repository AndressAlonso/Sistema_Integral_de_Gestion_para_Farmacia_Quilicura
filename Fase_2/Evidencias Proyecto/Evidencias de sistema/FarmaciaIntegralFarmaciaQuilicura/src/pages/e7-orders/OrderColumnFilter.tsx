import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { orderStates, type OrderSort } from './orders.api'

export default function OrderColumnFilter({ states, sort, onApply, column = 'state', options = orderStates }: {
  states: string[]; sort: OrderSort; onApply: (states: string[], sort: OrderSort) => void
  column?: 'state' | 'branch'; options?: Record<string, string>
}) {
  const allStates = Object.keys(options)
  const title = column === 'state' ? 'Estado' : 'Sucursal de retiro'
  const label = column === 'state' ? 'Filtrar y ordenar por estado' : 'Filtrar y ordenar por sucursal'
  const activeSort = sort.startsWith(column) ? sort : 'newest'
  const id = useId()
  const trigger = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const [selected, setSelected] = useState(states)
  const [ordering, setOrdering] = useState(sort)
  function close() { setPosition(null); trigger.current?.focus() }
  useEffect(() => {
    if (!position) return
    panel.current?.querySelector<HTMLSelectElement>('select')?.focus()
    function outside(event: PointerEvent) {
      if (event.target instanceof Node && !panel.current?.contains(event.target) && !trigger.current?.contains(event.target)) setPosition(null)
    }
    function key(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); setPosition(null); trigger.current?.focus() }
    }
    function resize() { setPosition(null) }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', key)
    window.addEventListener('resize', resize)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('keydown', key)
      window.removeEventListener('resize', resize)
    }
  }, [position])
  return <>
    <button ref={trigger} type="button" className={`orders-state-trigger${states.length < allStates.length ? ' is-filtered' : ''}`} aria-expanded={!!position} aria-controls={position ? id : undefined} aria-haspopup="dialog" aria-label={label} disabled={!allStates.length} onClick={() => {
      if (position) { close(); return }
      const bounds = trigger.current!.getBoundingClientRect()
      setSelected(states); setOrdering(sort)
      setPosition({ top: Math.max(8, Math.min(bounds.bottom + 8, window.innerHeight - 420)), left: Math.max(8, Math.min(bounds.right - 300, window.innerWidth - 308)) })
    }}>{title} <span aria-hidden="true">{activeSort.endsWith('_asc') ? '↑' : activeSort.endsWith('_desc') ? '↓' : '⌄'}</span>{states.length < allStates.length && <span className="orders-filter-count">{states.length}</span>}</button>
    {position && createPortal(<div ref={panel} id={id} role="dialog" aria-label={label} className="orders-state-popover" style={position}>
      <label className="orders-sort-label">Ordenar<select value={ordering} onChange={e => setOrdering(e.target.value as OrderSort)}>
        {sort !== 'newest' && !sort.startsWith(column) && <option value={sort}>Mantener orden actual</option>}
        <option value="newest">Más recientes primero</option><option value={`${column}_asc`}>{column === 'state' ? 'Estado: inicio → fin' : 'Nombre: A → Z'}</option><option value={`${column}_desc`}>{column === 'state' ? 'Estado: fin → inicio' : 'Nombre: Z → A'}</option>
      </select></label>
      <fieldset><legend>{column === 'state' ? 'Mostrar estados' : 'Mostrar sucursales'}</legend>{allStates.map(state => <label key={state}><input type="checkbox" checked={selected.includes(state)} onChange={e => setSelected(current => e.target.checked ? [...current, state] : current.filter(value => value !== state))} />{options[state]}</label>)}</fieldset>
      <button type="button" className="orders-filter-all" onClick={() => setSelected(selected.length === allStates.length ? [] : allStates)}>{selected.length === allStates.length ? 'Desmarcar todos' : 'Seleccionar todos'}</button>
      {!selected.length && <p role="status">{column === 'state' ? 'Selecciona al menos un estado.' : 'Selecciona al menos una sucursal.'}</p>}
      <div className="orders-filter-actions"><button type="button" onClick={close}>Cancelar</button><button type="button" disabled={!selected.length} onClick={() => { onApply(allStates.filter(state => selected.includes(state)), ordering); close() }}>Aplicar</button></div>
    </div>, document.body)}
  </>
}
