import { useEffect, useRef, useState } from 'react'
import type { PublicBranch } from '../types/catalog'
import StoreIcon from './StoreIcon'

export default function StoreBranchMenu({ branches, value, onChange }: { branches: PublicBranch[]; value: string; onChange: (id: string) => void }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    function outside(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  return <div className="store-branch-menu" ref={root} onKeyDown={event => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus() } }}>
    <button className="store-branch-trigger" type="button" ref={trigger} aria-expanded={open} aria-controls="store-branch-options" onClick={() => setOpen(!open)}><StoreIcon name="location" /><span><small>Ver disponibilidad en</small>{' '}<strong>{branches.find(branch => branch.id === value)?.name || 'Todas las sucursales'}</strong></span><span aria-hidden="true">⌄</span></button>
    {open && <div className="store-branch-options" id="store-branch-options"><p>Consultar disponibilidad</p>{[{ id: '', name: 'Todas las sucursales', address: '' }, ...branches].map(branch => <button type="button" key={branch.id} aria-pressed={value === branch.id} onClick={() => { onChange(branch.id); setOpen(false); trigger.current?.focus() }}><span><strong>{branch.name}</strong>{branch.address && <small>{branch.address}</small>}</span>{value === branch.id && <span aria-hidden="true">✓</span>}</button>)}</div>}
  </div>
}

