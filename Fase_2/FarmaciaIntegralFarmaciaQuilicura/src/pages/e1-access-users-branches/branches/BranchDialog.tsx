import { useEffect, useRef, useState, type FormEvent } from 'react'
import { deactivationIssues, type Branch } from './branches.mock'

type Props = {
  branch: Branch | null
  mode: 'create' | 'edit' | 'deactivate'
  onClose: () => void
  onSave: (name: string, address: string) => void
  onDeactivate: () => void
}
export default function BranchDialog({ branch, mode, onClose, onSave, onDeactivate }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState(branch?.name ?? '')
  const [address, setAddress] = useState(branch?.address ?? '')
  const [error, setError] = useState('')
  const issues = branch ? deactivationIssues(branch) : []
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) { setError('Escribe el nombre de la sucursal.'); return }
    onSave(name.trim(), address.trim())
  }
  const title = mode === 'create' ? 'Nueva sucursal' : mode === 'edit' ? 'Editar sucursal' : 'Desactivar sucursal'
  return (
    <dialog ref={dialog} className="s1 s1-dialog" aria-labelledby="branch-dialog-title" onCancel={(event) => { event.preventDefault(); onClose() }}>
      <div className="s1-dialog-head"><div><h2 id="branch-dialog-title">{title}</h2><p>{mode === 'deactivate' ? branch?.name : 'Datos de la ubicación operativa'}</p></div><button type="button" className="s1-close" aria-label="Cerrar diálogo" onClick={onClose}>×</button></div>
      {mode === 'deactivate' ? (
        <>
          {issues.length > 0 ? <><p className="s1-error" role="alert">No se puede desactivar esta sucursal mientras existan operaciones que impidan su cierre.</p><ul className="s1-check-list">{issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></> : <p className="s1-muted">La sucursal quedará inactiva. Su registro se conservará y no estará disponible para nuevas operaciones.</p>}
          <p className="s1-notice">Las comprobaciones mostradas usan datos de ejemplo. En el sistema final se validarán con información real.</p>
          <footer><button className="s1-button" onClick={onClose}>Cancelar</button><button className="s1-button danger" disabled={issues.length > 0} onClick={onDeactivate}>Desactivar sucursal</button></footer>
        </>
      ) : (
        <form onSubmit={save}>
          {error && <p className="s1-error" role="alert">{error}</p>}
          <div className="s1-field"><label htmlFor="branch-name">Nombre de la sucursal</label><input id="branch-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ej.: Sucursal Quilicura" required /></div>
          <div className="s1-field"><label htmlFor="branch-address">Dirección <span className="s1-muted">(opcional en esta propuesta)</span></label><input id="branch-address" value={address} onChange={(event) => setAddress(event.target.value)} placeholder="Calle, número y comuna" /></div>
          <p className="s1-notice">Propuesta visual: los campos y sus validaciones definitivas están pendientes de confirmar.</p>
          <footer><button type="button" className="s1-button" onClick={onClose}>Cancelar</button><button type="submit" className="s1-button primary">{mode === 'create' ? 'Crear sucursal' : 'Guardar cambios'}</button></footer>
        </form>
      )}
    </dialog>
  )
}

