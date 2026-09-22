import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Branch, InternalUser, NewUserInput, Role, UserInput } from './users.api'

export type UserEditor = { mode: 'create' | 'edit' | 'deactivate'; user: InternalUser | null }

interface Props {
  editor: UserEditor
  roles: Role[]
  branches: Branch[]
  canAssignRoles: boolean
  busy: boolean
  error: string
  onClose: () => void
  onSave: (data: UserInput | NewUserInput) => Promise<void>
  onDeactivate: () => Promise<void>
}

export default function UserDialog({ editor, roles, branches, canAssignRoles, busy, error, onClose, onSave, onDeactivate }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState(editor.user?.name ?? '')
  const [email, setEmail] = useState(editor.user?.email ?? '')
  const [password, setPassword] = useState('')
  const [selectedRoles, setSelectedRoles] = useState<string[]>(editor.user?.role_ids ?? [])
  const [branchId, setBranchId] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [validation, setValidation] = useState('')
  const deactivating = editor.mode === 'deactivate'
  const creating = editor.mode === 'create'

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    if (deactivating) { await onDeactivate(); return }
    if (!name.trim() || !email.trim() || selectedRoles.length === 0) {
      setValidation('Completa nombre, correo y al menos un rol.')
      return
    }
    setValidation('')
    const data: UserInput = { name: name.trim(), email: email.trim(), role_ids: selectedRoles }
    await onSave(creating ? { ...data, password, is_active: isActive, branch_id: branchId } : data)
  }

  return (
    <dialog ref={dialog} className="users-dialog" aria-labelledby="user-dialog-title" onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
      <form onSubmit={submit} aria-busy={busy}>
        <div className="users-dialog-heading"><h2 id="user-dialog-title">{deactivating ? 'Desactivar usuario' : creating ? 'Nuevo usuario' : 'Editar usuario'}</h2><button type="button" className="users-close" aria-label="Cerrar formulario" disabled={busy} onClick={onClose}>×</button></div>
        {deactivating ? <p>¿Desactivar a <strong>{editor.user?.name || editor.user?.email}</strong>? Su cuenta se conservará, pero ya no podrá iniciar sesión ni utilizar sus sesiones existentes.</p> : (
          <fieldset disabled={busy} className="users-fields">
            <label>Nombre completo<input autoComplete="name" value={name} onChange={event => setName(event.target.value)} required maxLength={150} /></label>
            <label>Correo electrónico<input type="email" autoComplete="off" value={email} onChange={event => setEmail(event.target.value)} required maxLength={254} /></label>
            {creating && <label>Contraseña inicial<input type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} required minLength={12} maxLength={1024} aria-describedby="password-hint" /><small id="password-hint">Mínimo 12 caracteres.</small></label>}
            <fieldset className="users-role-fields" disabled={!canAssignRoles}><legend>Roles *</legend>{roles.map(role => <label key={role.id}><input type="checkbox" checked={selectedRoles.includes(role.id)} onChange={event => setSelectedRoles(current => event.target.checked ? [...current, role.id] : current.filter(code => code !== role.id))} />{role.name}</label>)}</fieldset>
            {creating && <label>Sucursal<select value={branchId} onChange={event => setBranchId(event.target.value)} required><option value="">Selecciona una sucursal</option>{branches.map(branch => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>}
            {creating && <label className="users-checkbox"><input type="checkbox" checked={isActive} onChange={event => setIsActive(event.target.checked)} />Cuenta activa</label>}
          </fieldset>
        )}
        {(error || validation) && <p className="users-error" role="alert">{error || validation}</p>}
        <div className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={onClose}>Cancelar</button><button type="submit" className={`users-button ${deactivating ? 'danger' : 'primary'}`} disabled={busy}>{busy ? 'Guardando…' : deactivating ? 'Desactivar cuenta' : 'Guardar usuario'}</button></div>
      </form>
    </dialog>
  )
}
