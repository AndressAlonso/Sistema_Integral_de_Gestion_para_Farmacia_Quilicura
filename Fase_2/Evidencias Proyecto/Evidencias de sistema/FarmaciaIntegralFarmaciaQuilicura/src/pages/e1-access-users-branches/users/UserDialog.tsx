import ActionIcon from '../ActionIcon'
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import type {
  Branch,
  InternalUser,
  NewUserInput,
  Role,
  UserInput,
} from './users.api'

export type UserEditor = {
  mode: 'create' | 'edit' | 'deactivate' | 'delete'
  user: InternalUser | null
}

interface Props {
  editor: UserEditor
  roles: Role[]
  branches: Branch[]
  canAssignRoles: boolean
  busy: boolean
  error: string
  onClose: () => void
  onSave: (
    data: UserInput | NewUserInput,
  ) => Promise<void>
  onActivate: () => Promise<void>
  onDeactivate: () => Promise<void>
  onDelete: (confirmationEmail: string) => Promise<void>
}

export default function UserDialog({
  editor,
  roles,
  branches,
  canAssignRoles,
  busy,
  error,
  onClose,
  onSave,
  onActivate,
  onDeactivate,
  onDelete,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [mode, setMode] = useState<UserEditor['mode'] | 'activate'>(editor.mode)

  const [name, setName] = useState(
    editor.user?.name ?? '',
  )

  const [email, setEmail] = useState(
    editor.user?.email ?? '',
  )

  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [confirmationEmail, setConfirmationEmail] = useState('')

  const [selectedRoles, setSelectedRoles] = useState<string[]>(
    editor.user?.role_ids ?? [],
  )

  const [branchId, setBranchId] = useState(
    editor.user?.branch_id ?? '',
  )

  const [isActive, setIsActive] = useState(true)
  const [validation, setValidation] = useState('')

  const deactivating = mode === 'deactivate'
  const creating = mode === 'create'
  const deleting = mode === 'delete'
  const activating = mode === 'activate'
  const confirming = deactivating || activating || deleting
  const emailConfirmed = confirmationEmail.trim().toLowerCase() === editor.user?.email.toLowerCase()

  useEffect(() => {
    const element = dialog.current
    element?.showModal()

    return () => {
      if (element?.open) {
        element.close()
      }
    }
  }, [])

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (busy) {
      return
    }

    if (activating) {
      await onActivate()
      return
    }
    if (deleting) {
      if (emailConfirmed && editor.user?.can_delete) await onDelete(confirmationEmail.trim())
      return
    }

    if (deactivating) {
      await onDeactivate()
      return
    }

    if (
      !name.trim() ||
      !email.trim() ||
      selectedRoles.length === 0 ||
      !branchId
    ) {
      setValidation(
        'Completa nombre, correo, al menos un rol y una sucursal.',
      )
      return
    }

    const selectedBranch = branches.find(
      (branch) => branch.id === branchId,
    )

    if (!selectedBranch?.is_active) {
      setValidation(
        'Selecciona una sucursal activa.',
      )
      return
    }

    if (creating && password.length < 12) {
      setValidation(
        'La contraseña inicial debe tener al menos 12 caracteres.',
      )
      return
    }


    if (creating && password !== passwordConfirmation) {
      setValidation('Las contraseñas no coinciden. Escríbelas nuevamente.')
      return
    }

    setValidation('')

    const data: UserInput = {
      name: name.trim(),
      email: email.trim(),
      role_ids: selectedRoles,
      branch_id: branchId,
    }

    if (creating) {
      await onSave({
        ...data,
        password,
        is_active: isActive,
      })

      return
    }

    await onSave(data)
  }

  const activeBranches = branches.filter(
    (branch) => branch.is_active,
  )

  const currentInactiveBranch =
    editor.user &&
    branches.find(
      (branch) =>
        branch.id === editor.user?.branch_id &&
        !branch.is_active,
    )

  return (
    <dialog
      ref={dialog}
      className="users-dialog users-dialog-fullscreen app-modal"
      aria-labelledby="user-dialog-title"
      onCancel={(event) => {
        event.preventDefault()

        if (!busy) {
          onClose()
        }
      }}
    >
      <form onSubmit={submit} aria-busy={busy}>
        <div className="users-dialog-heading">
          <h2 id="user-dialog-title">
            {activating ? 'Activar usuario' : deleting ? 'Eliminar usuario definitivamente' : deactivating
              ? 'Desactivar usuario'
              : creating
                ? 'Nuevo usuario'
                : 'Ficha del usuario'}
          </h2>

          <button
            type="button"
            className="users-close"
            aria-label="Cerrar formulario"
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {!creating && !confirming && editor.user && (
          <section className="users-account-controls" aria-label="Estado y acciones de la cuenta">
            <div><strong>{editor.user.name}</strong><p>Estado: {editor.user.is_active ? 'Activo' : 'Inactivo'}</p></div>
            <div className="users-account-buttons">
              <button type="button" className="users-button" disabled={busy} onClick={() => { setValidation(''); setMode(editor.user?.is_active ? 'deactivate' : 'activate') }}><ActionIcon name="deactivate" />{editor.user.is_active ? 'Desactivar cuenta' : 'Activar cuenta'}</button>
              {editor.user.can_delete && <button type="button" className="users-button danger" disabled={busy} onClick={() => { setValidation(''); setMode('delete') }}><ActionIcon name="delete" />Eliminar cuenta</button>}
            </div>
            {editor.user.deletion_block_reason && <p className="users-account-note">{editor.user.deletion_block_reason}</p>}
          </section>
        )}
        {activating ? <p>¿Activar a <strong>{editor.user?.name || editor.user?.email}</strong>? Podrá iniciar sesión con sus credenciales y permisos asignados. Sus sesiones revocadas no se recuperarán.</p> : deleting ? (
          <div className="users-delete-content">
            <p>Esta acción elimina la cuenta inmediatamente y no se puede deshacer.
              Para bloquear el acceso conservando el registro, cancela y utiliza Desactivar.</p>
            <dl className="users-delete-summary">
              <dt>Usuario</dt><dd>{editor.user?.name}</dd>
              <dt>Correo</dt><dd>{editor.user?.email}</dd>
              <dt>ID</dt><dd>{editor.user?.id}</dd>
            </dl>
            <p>También se borrará todo su historial de sesiones y sus sesiones abiertas dejarán de funcionar.
              Otros registros asociados pueden impedir la eliminación.
              No se permite eliminar tu cuenta ni al último administrador activo.</p>
            <label className="users-delete-confirmation">
              Escribe el correo completo para confirmar
              <input type="email" required autoComplete="off" spellCheck={false}
                disabled={busy} value={confirmationEmail}
                onChange={(event) => setConfirmationEmail(event.target.value)} />
            </label>
          </div>
        ) : deactivating ? (
          <p>
            ¿Desactivar a{' '}
            <strong>
              {editor.user?.name ||
                editor.user?.email}
            </strong>
            ? Su cuenta se conservará, pero ya no podrá
            iniciar sesión ni utilizar sus sesiones
            existentes.
          </p>
        ) : (
          <fieldset
            disabled={busy}
            className="users-fields"
          >
            {creating && <h3 className="users-form-section">Datos del trabajador</h3>}
            <label>
              Nombre completo

              <input
                autoComplete="name"
                value={name}
                required
                maxLength={150}
                onChange={(event) => {
                  setName(event.target.value)
                  setValidation('')
                }}
              />
            </label>

            <label>
              Correo electrónico

              <input
                type="email"
                autoComplete="off"
                value={email}
                required
                maxLength={254}
                onChange={(event) => {
                  setEmail(event.target.value)
                  setValidation('')
                }}
              />
            </label>

            {creating && (
              <>
              <h3 className="users-form-section">Credenciales de acceso</h3>
              <label>
                Contraseña inicial

                <input
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  required
                  minLength={12}
                  maxLength={1024}
                  aria-describedby="password-hint"
                  onChange={(event) => {
                    setPassword(event.target.value)
                    setValidation('')
                  }}
                />

                <small id="password-hint">
                  Mínimo 12 caracteres.
                </small>
              </label>
              <label>
                Confirmar contraseña
                <input
                  type="password"
                  autoComplete="new-password"
                  value={passwordConfirmation}
                  required
                  minLength={12}
                  maxLength={1024}
                  aria-describedby="password-confirmation-hint"
                  aria-invalid={passwordConfirmation.length > 0 && password !== passwordConfirmation}
                  onChange={(event) => {
                    setPasswordConfirmation(event.target.value)
                    setValidation('')
                  }}
                />
                <small id="password-confirmation-hint">
                  {passwordConfirmation && password !== passwordConfirmation
                    ? 'Las contraseñas no coinciden.'
                    : 'Vuelve a escribir la contraseña inicial.'}
                </small>
              </label>
              <h3 className="users-form-section">Rol y asignación</h3>
              </>
            )}

            <fieldset
              className="users-role-fields"
              disabled={!canAssignRoles}
            >
              <legend>Roles *</legend>

              <p className="users-role-help">
                Selecciona uno o más roles. Sus permisos se suman.
                La descripción indica su responsabilidad; las funciones pendientes aún no están disponibles.
              </p>

              {roles.map((role) => (
                <div className={`users-role-card${selectedRoles.includes(role.id) ? ' selected' : ''}`} key={role.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={selectedRoles.includes(
                      role.id,
                    )}
                    onChange={(event) => {
                      setSelectedRoles((current) =>
                        event.target.checked
                          ? [...current, role.id]
                          : current.filter(
                              (id) => id !== role.id,
                            ),
                      )

                      setValidation('')
                    }}
                  />

                  <strong>{role.name}</strong>
                </label>
                <p>{role.description}</p>
                <span className="users-role-permissions-title">Permisos configurados</span>
                {role.permissions.length > 0 ? (
                  <ul>
                    {role.permissions.map((permission) => (
                      <li key={permission.code}>
                        {permission.description}
                        <small>{permission.implemented ? 'Disponible' : 'Módulo pendiente'}</small>
                      </li>
                    ))}
                  </ul>
                ) : <small>Sus permisos operativos se habilitarán al implementar los módulos correspondientes.</small>}
                </div>
              ))}
            </fieldset>

            <label>
              Sucursal

              <select
                value={branchId}
                required
                onChange={(event) => {
                  setBranchId(event.target.value)
                  setValidation('')
                }}
              >
                <option value="">
                  Selecciona una sucursal
                </option>

                {currentInactiveBranch && (
                  <option
                    value={currentInactiveBranch.id}
                    disabled
                  >
                    {currentInactiveBranch.name} (inactiva)
                  </option>
                )}

                {activeBranches.map((branch) => (
                  <option
                    key={branch.id}
                    value={branch.id}
                  >
                    {branch.name}
                  </option>
                ))}
              </select>

              {currentInactiveBranch && (
                <small>
                  La sucursal actual está inactiva.
                  Selecciona una sucursal activa antes de
                  guardar.
                </small>
              )}
            </label>

            {creating && (
              <label className="users-checkbox">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(event) =>
                    setIsActive(event.target.checked)
                  }
                />

                Cuenta activa
              </label>
            )}
          </fieldset>
        )}

        {confirming && <p className="users-account-note">Esta acción no guarda los cambios pendientes en los datos del formulario.</p>}

        {(error || validation) && (
          <p className="users-error" role="alert">
            {error || validation}
          </p>
        )}

        <div className="users-dialog-actions">
          <button
            type="button"
            className="users-button"
            disabled={busy}
            onClick={() => { if (confirming) { setMode('edit'); setValidation(''); setConfirmationEmail('') } else onClose() }}
          >
            {confirming ? 'Volver a la ficha' : 'Cancelar'}
          </button>

          <button
            type="submit"
            className={`users-button ${
              deactivating || deleting ? 'danger' : 'primary'
            }`}
            disabled={busy || (deleting && (!emailConfirmed || !editor.user?.can_delete))}
          >
            {busy
              ? 'Guardando...'
              : activating ? 'Activar cuenta' : deleting ? 'Eliminar definitivamente' : deactivating
                ? 'Desactivar cuenta'
                : 'Guardar usuario'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
