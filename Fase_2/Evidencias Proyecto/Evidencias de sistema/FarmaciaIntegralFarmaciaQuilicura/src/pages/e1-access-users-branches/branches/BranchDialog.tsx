import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Branch, BranchInput } from './branches.api'

export type BranchEditor = {
  mode: 'create' | 'edit' | 'deactivate'
  branch: Branch | null
}

type Props = {
  editor: BranchEditor
  busy: boolean
  error: string
  onClose: () => void
  onSave: (input: BranchInput) => void
  onDeactivate: () => void
}

export default function BranchDialog({
  editor,
  busy,
  error,
  onClose,
  onSave,
  onDeactivate,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const { branch, mode } = editor

  const [code, setCode] = useState(branch?.code ?? '')
  const [name, setName] = useState(branch?.name ?? '')
  const [address, setAddress] = useState(branch?.address ?? '')
  const [validationError, setValidationError] = useState('')

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
    setValidationError('')

    const normalizedCode = code.trim().toUpperCase()
    const normalizedName = name.trim()
    const normalizedAddress = address.trim()

    if (!normalizedCode) {
      setValidationError('Escribe el código de la sucursal.')
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
        ? 'Editar sucursal'
        : 'Desactivar sucursal'

  return (
    <dialog
      ref={dialog}
      className="s1 s1-dialog"
      aria-labelledby="branch-dialog-title"
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault()

        if (!busy) {
          onClose()
        }
      }}
    >
      <div className="s1-dialog-head">
        <div>
          <h2 id="branch-dialog-title">{title}</h2>

          <p>
            {mode === 'deactivate'
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

      {mode === 'deactivate' ? (
        <>
          {error && (
            <p className="s1-error" role="alert">
              {error}
            </p>
          )}

          <p className="s1-muted">
            La sucursal quedará inactiva. Su registro se conservará y
            dejará de estar disponible para nuevas operaciones.
          </p>

          <p className="s1-notice">
            La desactivación será rechazada si la sucursal todavía tiene
            usuarios activos asignados.
          </p>

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
              type="button"
              className="s1-button danger"
              disabled={busy}
              onClick={onDeactivate}
            >
              {busy ? 'Desactivando...' : 'Desactivar sucursal'}
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

          <div className="s1-field">
            <label htmlFor="branch-code">
              Código de la sucursal
            </label>

            <input
              id="branch-code"
              name="code"
              value={code}
              maxLength={30}
              placeholder="Ej.: LOCAL-02"
              autoComplete="off"
              required
              disabled={busy}
              onChange={(event) => {
                setCode(event.target.value.toUpperCase())
                setValidationError('')
              }}
            />
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

          <p className="s1-notice">
            El código debe ser único para cada sucursal. Los cambios quedarán registrados en el sistema.
          </p>

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
    </dialog>
  )
}