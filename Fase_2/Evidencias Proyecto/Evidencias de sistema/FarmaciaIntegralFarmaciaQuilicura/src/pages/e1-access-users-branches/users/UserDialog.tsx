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
  mode: 'create' | 'edit' | 'deactivate'
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
  onDeactivate: () => Promise<void>
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
  onDeactivate,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)

  const [name, setName] = useState(
    editor.user?.name ?? '',
  )

  const [email, setEmail] = useState(
    editor.user?.email ?? '',
  )

  const [password, setPassword] = useState('')

  const [selectedRoles, setSelectedRoles] = useState<string[]>(
    editor.user?.role_ids ?? [],
  )

  const [branchId, setBranchId] = useState(
    editor.user?.branch_id ?? '',
  )

  const [isActive, setIsActive] = useState(true)
  const [validation, setValidation] = useState('')

  const deactivating = editor.mode === 'deactivate'
  const creating = editor.mode === 'create'

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
      className="users-dialog"
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
            {deactivating
              ? 'Desactivar usuario'
              : creating
                ? 'Nuevo usuario'
                : 'Editar usuario'}
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

        {deactivating ? (
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
            )}

            <fieldset
              className="users-role-fields"
              disabled={!canAssignRoles}
            >
              <legend>Roles *</legend>

              {roles.map((role) => (
                <label key={role.id}>
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

                  {role.name}
                </label>
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
            onClick={onClose}
          >
            Cancelar
          </button>

          <button
            type="submit"
            className={`users-button ${
              deactivating ? 'danger' : 'primary'
            }`}
            disabled={busy}
          >
            {busy
              ? 'Guardando...'
              : deactivating
                ? 'Desactivar cuenta'
                : 'Guardar usuario'}
          </button>
        </div>
      </form>
    </dialog>
  )
}