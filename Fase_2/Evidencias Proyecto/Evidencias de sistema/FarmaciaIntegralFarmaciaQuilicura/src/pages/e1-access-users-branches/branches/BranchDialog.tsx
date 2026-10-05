import ActionIcon from '../ActionIcon'
import AssignedUsers from './AssignedUsers'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Branch, BranchInput } from './branches.api'

export type BranchEditor = {
  mode: 'create' | 'edit' | 'deactivate' | 'delete'
  branch: Branch | null
}

type Props = {
  editor: BranchEditor
  busy: boolean
  error: string
  onClose: () => void
  onSave: (input: BranchInput) => void
  onActivate: () => void
  onDeactivate: () => void
  onDelete: (confirmationId: string) => void
  branches: Branch[]
}

export default function BranchDialog({
  editor,
  busy,
  error,
  onClose,
  onSave,
  onActivate,
  onDeactivate,
  onDelete,
  branches,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const { branch } = editor
  const [mode, setMode] = useState<BranchEditor['mode'] | 'activate'>(editor.mode)

  const [code, setCode] = useState(branch?.code ?? '')
  const [name, setName] = useState(branch?.name ?? '')
  const [address, setAddress] = useState(branch?.address ?? '')
  const [validationError, setValidationError] = useState('')
  const [codeEdited, setCodeEdited] = useState(false)
  const [confirmationId, setConfirmationId] = useState('')
  const [showUsers, setShowUsers] = useState(false)

  const baseCode = (name.trim() || address.trim())
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toUpperCase().replace(/[^A-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '').slice(0, 24).replace(/-+$/g, '')
  const usedCodes = new Set(branches.filter((item) => item.id !== branch?.id)
    .map((item) => item.code.toUpperCase()))
  let suggestedCode = baseCode
  let suffix = 2
  while (suggestedCode && usedCodes.has(suggestedCode)) {
    const ending = `-${String(suffix++).padStart(2, '0')}`
    suggestedCode = `${baseCode.slice(0, 30 - ending.length)}${ending}`
  }
  const effectiveCode = mode === 'create' && !codeEdited ? suggestedCode : code
  const duplicateCode = usedCodes.has(effectiveCode.trim().toUpperCase())

  useEffect(() => {
    const element = dialog.current
    element?.showModal()

    return () => {
      if (element?.open) {
        element.close()
      }
    }
  }, [])

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setValidationError('')

    const normalizedCode = effectiveCode.trim().toUpperCase()
    const normalizedName = name.trim()
    const normalizedAddress = address.trim()

    if (!normalizedCode) {
      setValidationError('Escribe el código de la sucursal.')
      return
    }

    if (duplicateCode) {
      setValidationError('Ya existe una sucursal con ese código. Utiliza otro.')
      return
    }

    if (!normalizedName) {
      setValidationError('Escribe el nombre de la sucursal.')
      return
    }

    if (!normalizedAddress) {
      setValidationError('Escribe la dirección de la sucursal.')
      return
    }

    onSave({
      code: normalizedCode,
      name: normalizedName,
      address: normalizedAddress,
    })
  }

  const title =
    mode === 'create'
      ? 'Nueva sucursal'
      : mode === 'edit'
        ? 'Ficha de la sucursal'
        : mode === 'delete' ? 'Eliminar sucursal' : mode === 'activate' ? 'Activar sucursal' : 'Desactivar sucursal'

  return (
    <dialog
      ref={dialog}
      className="s1 s1-dialog branches-dialog app-modal"
      aria-labelledby="branch-dialog-title"
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault()

        if (!busy) {
          onClose()
        }
      }}
    >
      <div className="branches-dialog-content">
      <div className="s1-dialog-head">
        <div>
          <h2 id="branch-dialog-title">{title}</h2>

          <p>
            {mode === 'deactivate' || mode === 'delete'
              ? branch?.name
              : 'Datos de la ubicación operativa'}
          </p>
        </div>

        <button
          type="button"
          className="s1-close"
          aria-label="Cerrar diálogo"
          disabled={busy}
          onClick={onClose}
        >
          ×
        </button>
      </div>

      {mode === 'edit' && branch && (
        <section className="branches-account-controls" aria-label="Estado y acciones de la sucursal">
          <div><strong>{branch.name}</strong><p>Estado: {branch.is_active ? 'Activa' : 'Inactiva'}</p></div>
          <div className="branches-account-buttons">
            <button type="button" className="branches-button" disabled={busy} onClick={() => setMode(branch.is_active ? 'deactivate' : 'activate')}><ActionIcon name="deactivate" />{branch.is_active ? 'Desactivar sucursal' : 'Activar sucursal'}</button>
            {branch.can_delete && <button type="button" className="branches-button" disabled={busy} onClick={() => setMode('delete')}><ActionIcon name="delete" />Eliminar sucursal</button>}
          </div>
          {!branch.can_delete && <p className="s1-muted">No se puede eliminar esta sucursal porque tiene usuarios o registros asociados.</p>}
        </section>
      )}
      {mode === 'edit' && branch && <section className="branches-assigned">
        <button type="button" className="branches-assigned-toggle" aria-expanded={showUsers} aria-controls="branch-assigned-users" onClick={() => setShowUsers(value => !value)}>
          <span>Usuarios asignados</span><span aria-hidden="true">{showUsers ? '−' : '+'}</span>
        </button>
        <div id="branch-assigned-users" hidden={!showUsers}>
          {showUsers && <AssignedUsers branchId={branch.id} />}
        </div>
      </section>}
      {mode !== 'create' && mode !== 'edit' && <p className="s1-muted">Esta acción no guarda los cambios pendientes en los datos del formulario.</p>}
      {mode === 'delete' ? (
        <form onSubmit={(event) => {
          event.preventDefault()
          if (!busy && confirmationId === branch?.id) onDelete(confirmationId)
        }}>
          <p className="s1-notice branches-delete-warning">
            La eliminación es inmediata y definitiva. No podrás recuperar esta sucursal.
            Si quieres conservar su registro, cancela y utiliza Desactivar.
          </p>
          <div className="branches-id-panel">
            <span>ID completo de {branch?.name}</span>
            <code>{branch?.id}</code>
            <small>Código de sucursal: {branch?.code}</small>
          </div>
          <div className="s1-field">
            <label htmlFor="branch-confirmation">Escribe el ID mostrado para confirmar</label>
            <input id="branch-confirmation" value={confirmationId}
              onChange={(event) => setConfirmationId(event.target.value)}
              autoComplete="off" spellCheck={false} required disabled={busy}
              aria-describedby="branch-delete-help" />
          </div>
          <p id="branch-delete-help" className="s1-muted">
            No se eliminarán sucursales con usuarios asignados o registros asociados.
          </p>
          {error && <p className="s1-error" role="alert">{error}</p>}
          <footer>
            <button type="button" className="s1-button" disabled={busy} onClick={() => { setMode('edit'); setConfirmationId('') }}>Volver a la ficha</button>
            <button type="submit" className="s1-button danger"
              disabled={busy || confirmationId !== branch?.id}>
              {busy ? 'Eliminando...' : 'Eliminar definitivamente'}
            </button>
          </footer>
        </form>
      ) : mode === 'deactivate' || mode === 'activate' ? (
        <>
          {error && (
            <p className="s1-error" role="alert">
              {error}
            </p>
          )}

          <p className="s1-muted">
            {mode === 'activate' ? 'La sucursal volverá a estar disponible para asignaciones y operaciones habilitadas. No se activarán automáticamente sus usuarios.' : 'La sucursal quedará inactiva. Su registro se conservará y dejará de estar disponible para nuevas operaciones.'}
          </p>

          {mode === 'deactivate' && <p className="s1-notice">
            La desactivación será rechazada si la sucursal todavía tiene
            usuarios activos asignados.
          </p>}

          <footer>
            <button
              type="button"
              className="s1-button"
              disabled={busy}
              onClick={() => setMode('edit')}
            >
              Volver a la ficha
            </button>

            <button
              type="button"
              className={`s1-button ${mode === 'activate' ? 'primary' : 'danger'}`} 
              disabled={busy}
              onClick={mode === 'activate' ? onActivate : onDeactivate}
            >
              {busy ? 'Guardando...' : mode === 'activate' ? 'Activar sucursal' : 'Desactivar sucursal'}
            </button>
          </footer>
        </>
      ) : (
        <form onSubmit={save}>
          {(validationError || error) && (
            <p className="s1-error" role="alert">
              {validationError || error}
            </p>
          )}

          <div className="s1-field branches-code-field">
            <label htmlFor="branch-code">
              Código de la sucursal
            </label>

            <input
              id="branch-code"
              name="code"
              value={effectiveCode}
              maxLength={30}
              placeholder="Ej.: LOCAL-02"
              autoComplete="off"
              required
              disabled={busy}
              aria-invalid={duplicateCode}
              aria-describedby="branch-code-help"
              onChange={(event) => {
                setCodeEdited(true)
                setCode(event.target.value.toUpperCase())
                setValidationError('')
              }}
            />
            <small id="branch-code-help" className={duplicateCode ? 'branches-code-error' : 's1-muted'}>
              {duplicateCode ? 'Este código ya está registrado.' :
                mode === 'create' ? 'Sugerido a partir del nombre o dirección. Puedes modificarlo; se verificará al guardar.' :
                  'El código no cambia automáticamente al editar el nombre o dirección.'}
            </small>
            {mode === 'create' && codeEdited && (
              <button type="button" className="branches-suggest" disabled={busy}
                onClick={() => setCodeEdited(false)}>Usar código sugerido</button>
            )}
          </div>

          <div className="s1-field">
            <label htmlFor="branch-name">
              Nombre de la sucursal
            </label>

            <input
              id="branch-name"
              name="name"
              value={name}
              maxLength={150}
              placeholder="Ej.: Sucursal Quilicura"
              required
              disabled={busy}
              onChange={(event) => {
                setName(event.target.value)
                setValidationError('')
              }}
            />
          </div>

          <div className="s1-field">
            <label htmlFor="branch-address">
              Dirección
            </label>

            <input
              id="branch-address"
              name="address"
              value={address}
              maxLength={250}
              placeholder="Calle, número y comuna"
              required
              disabled={busy}
              onChange={(event) => {
                setAddress(event.target.value)
                setValidationError('')
              }}
            />
          </div>

          <footer>
            <button
              type="button"
              className="s1-button"
              disabled={busy}
              onClick={onClose}
            >
              Cancelar
            </button>

            <button
              type="submit"
              className="s1-button primary"
              disabled={busy}
            >
              {busy
                ? 'Guardando...'
                : mode === 'create'
                  ? 'Crear sucursal'
                  : 'Guardar cambios'}
            </button>
          </footer>
        </form>
      )}
      </div>
    </dialog>
  )
}
