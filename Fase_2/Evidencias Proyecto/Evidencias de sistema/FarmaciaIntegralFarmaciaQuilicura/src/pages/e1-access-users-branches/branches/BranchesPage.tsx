import ActionIcon from '../ActionIcon'
// HU: E1-H5 - Crear, actualizar y desactivar sucursales
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../../../services/http'
import BranchDialog, { type BranchEditor } from './BranchDialog'
import {
  activateBranch,
  createBranch,
  deactivateBranch,
  deleteBranch,
  listBranches,
  updateBranch,
  type Branch,
  type BranchInput,
} from './branches.api'
import '../sprint-one.css'
import './branches.css'

export default function BranchesPage() {
  const navigate = useNavigate()

  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [attempt, setAttempt] = useState(0)

  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('active')

  const [editor, setEditor] = useState<BranchEditor | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const sending = useRef(false)

  useEffect(() => {
    let active = true

    listBranches()
      .then((result) => {
        if (!active) {
          return
        }

        setBranches(result.branches)
        setLoading(false)
      })
      .catch((cause: unknown) => {
        if (!active) {
          return
        }

        if (cause instanceof ApiError && cause.status === 401) {
          navigate('/login', { replace: true })
          return
        }

        setLoadError(
          cause instanceof ApiError
            ? cause.message
            : 'No pudimos cargar las sucursales.',
        )

        setLoading(false)
      })

    return () => {
      active = false
    }
  }, [attempt, navigate])

  function openEditor(value: BranchEditor) {
    if (value.mode === 'delete' && !value.branch?.can_delete) return
    setError('')
    setMessage('')
    setEditor(value)
  }

  async function mutate(
    operation: () => Promise<Branch | void>,
    successMessage: string,
    deletedId?: string,
  ) {
    if (sending.current) {
      return
    }

    sending.current = true
    setBusy(true)
    setError('')

    try {
      const saved = await operation()

      setBranches((current) => {
        if (!saved) return current.filter((branch) => branch.id !== deletedId)
        const exists = current.some(
          (branch) => branch.id === saved.id,
        )

        const updated = exists
          ? current.map((branch) =>
              branch.id === saved.id ? saved : branch,
            )
          : [...current, saved]

        return updated.sort((first, second) =>
          first.name.localeCompare(second.name, 'es'),
        )
      })

      setEditor(null)
      setMessage(successMessage)
    } catch (cause: unknown) {
      if (deletedId && cause instanceof ApiError && cause.status === 409) {
        setBranches((current) => current.map((branch) =>
          branch.id === deletedId ? { ...branch, can_delete: false } : branch,
        ))
        setEditor(null)
        setMessage(cause.message)
        return
      }
      if (cause instanceof ApiError && cause.status === 401) {
        navigate('/login', { replace: true })
        return
      }

      if (cause instanceof ApiError && cause.status === 403) {
        setEditor(null)
        setLoadError(cause.message)
        return
      }

      setError(
        cause instanceof ApiError
          ? cause.message
          : 'No pudimos guardar la sucursal. Intenta nuevamente.',
      )
    } finally {
      sending.current = false
      setBusy(false)
    }
  }

  async function save(input: BranchInput) {
    if (editor?.mode === 'create') {
      await mutate(
        () =>
          createBranch({
            ...input,
            is_active: true,
          }),
        'Sucursal creada correctamente.',
      )

      return
    }

    if (editor?.mode === 'edit' && editor.branch) {
      const branchId = editor.branch.id

      await mutate(
        () => updateBranch(branchId, input),
        'Sucursal actualizada correctamente.',
      )
    }
  }

  async function activate() {
    if (!editor?.branch) return
    const id = editor.branch.id
    await mutate(() => activateBranch(id), 'Sucursal activada correctamente.')
  }

  async function deactivate() {
    if (!editor?.branch) {
      return
    }

    const branchId = editor.branch.id

    await mutate(
      () => deactivateBranch(branchId),
      'Sucursal desactivada. Su registro se conserva.',
    )
  }

  async function remove(confirmationId: string) {
    if (!editor?.branch?.can_delete) return
    const id = editor.branch.id
    await mutate(() => deleteBranch(id, confirmationId), 'Sucursal eliminada definitivamente.', id)
  }

  if (loading) {
    return <p role="status">Cargando sucursales...</p>
  }

  if (loadError) {
    return (
      <div>
        <p className="s1-error" role="alert">
          {loadError}
        </p>

        <button
          className="branches-button"
          type="button"
          onClick={() => {
            setLoading(true)
            setLoadError('')
            setAttempt((value) => value + 1)
          }}
        >
          Reintentar
        </button>
      </div>
    )
  }

  const normalizedQuery = query.trim().toLocaleLowerCase('es')

  const filteredBranches = branches.filter((branch) => {
    const searchableText =
      `${branch.code} ${branch.name} ${branch.address}`
        .toLocaleLowerCase('es')

    const matchesQuery =
      !normalizedQuery ||
      searchableText.includes(normalizedQuery)

    const matchesStatus =
      !status ||
      branch.is_active === (status === 'active')

    return matchesQuery && matchesStatus
  })

  const activeBranches = branches.filter(
    (branch) => branch.is_active,
  ).length

  const inactiveBranches = branches.filter(
    (branch) => !branch.is_active,
  ).length



  return (
    <div className="branches-page">
      <header className="branches-heading">
        <h1>Gestión de sucursales</h1>

        <p>
          Administra las ubicaciones operativas de Farmacia Quilicura.
        </p>
      </header>

      <p className="access-summary" aria-label="Recuento de sucursales">
        <span><strong>{branches.length}</strong> {branches.length === 1 ? 'sucursal' : 'sucursales'}</span>
        <span><i className="access-summary-dot active" aria-hidden="true" /><strong>{activeBranches}</strong> activas</span>
        <span><i className="access-summary-dot" aria-hidden="true" /><strong>{inactiveBranches}</strong> inactivas</span>
      </p>

      <div className="branches-filters">
        <label className="branches-search">
          <span className="sr-only">
            Buscar por código, nombre o dirección
          </span>

          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            aria-hidden="true"
          >
            <circle cx="10" cy="10" r="6" />
            <path d="m15 15 5 5" />
          </svg>

          <input
            type="search"
            placeholder="Buscar por código, nombre o dirección..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>

        <label className="branches-state-filter">
          <span>Estado</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Todas</option>
            <option value="active">Activas</option>
            <option value="inactive">Inactivas</option>
          </select>
        </label>

        <button
          className="branches-button primary"
          type="button"
          onClick={() =>
            openEditor({
              mode: 'create',
              branch: null,
            })
          }
        >
          <ActionIcon name="add" />Nueva sucursal
        </button>
      </div>

      {message && (
        <p className="branches-message" role="status">
          {message}
        </p>
      )}

      <section
        className="branches-panel"
        aria-labelledby="branch-list-title"
      >
        <div className="branches-panel-heading">
          <div>
            <h2 id="branch-list-title">
              {status === 'active' ? 'Sucursales activas' : status === 'inactive' ? 'Sucursales inactivas' : 'Todas las sucursales'}
            </h2>

            <p>Pulsa el nombre para gestionar la sucursal.</p>
            <p role="status">
              {filteredBranches.length}{' '}
              {filteredBranches.length === 1
                ? 'sucursal encontrada'
                : 'sucursales encontradas'}
            </p>
          </div>

        </div>

        <div
          className="branches-table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Listado de sucursales"
        >
          <table className="branches-table">
            <thead>
              <tr>
                <th scope="col">Sucursal</th>
                <th scope="col">Código</th>
                <th scope="col">Dirección</th>
                <th scope="col">Usuarios asignados</th>
                <th scope="col">Estado</th>

              </tr>
            </thead>

            <tbody>
              {filteredBranches.map((branch) => (
                <tr key={branch.id}>
                  <th scope="row">
                    <div className="branches-name">
                      <button type="button" className="branches-open-profile" aria-label={`Abrir ficha de ${branch.name}`} onClick={() => openEditor({ mode: 'edit', branch })}>{branch.name}<ActionIcon name="edit" /></button>
                      <small title={branch.id}>
                        {branch.id.slice(0, 8)}
                      </small>
                    </div>
                  </th>

                  <td>{branch.code}</td>

                  <td>{branch.address}</td>
                  <td>{branch.assigned_users_count}</td>

                  <td>
                    <span
                      className={
                        branch.is_active
                          ? 'branches-status'
                          : 'branches-status inactive'
                      }
                    >
                      {branch.is_active ? 'Activa' : 'Inactiva'}
                    </span>
                  </td>


                </tr>
              ))}

              {filteredBranches.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="branches-empty"
                  >
                    No se encontraron sucursales con esos filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      

      {editor && (
        <BranchDialog
          key={`${editor.mode}-${editor.branch?.id ?? 'new'}`}
          editor={editor}
          busy={busy}
          error={error}
          onClose={() => {
            if (!sending.current) {
              setEditor(null)
            }
          }}
          onSave={save}
          onActivate={activate}
          onDeactivate={deactivate}
          onDelete={remove}
          branches={branches}
        />
      )}
    </div>
  )
}
