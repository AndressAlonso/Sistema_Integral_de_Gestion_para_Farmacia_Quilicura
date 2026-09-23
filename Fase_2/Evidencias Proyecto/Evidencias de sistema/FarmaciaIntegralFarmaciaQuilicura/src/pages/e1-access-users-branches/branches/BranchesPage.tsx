// HU: E1-H5 - Crear, actualizar y desactivar sucursales
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../../../services/http'
import BranchDialog, { type BranchEditor } from './BranchDialog'
import {
  createBranch,
  deactivateBranch,
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
  const [status, setStatus] = useState('')

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
    setError('')
    setMessage('')
    setEditor(value)
  }

  async function mutate(
    operation: () => Promise<Branch>,
    successMessage: string,
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

  const availability =
    branches.length > 0
      ? Math.round((activeBranches / branches.length) * 100)
      : 0

  const statistics = [
    {
      label: 'Sucursales activas',
      value: activeBranches,
      detail: 'Ubicaciones operativas',
      symbol: 'A',
      style: 'green',
    },
    {
      label: 'Sucursales registradas',
      value: branches.length,
      detail: 'Total en el sistema',
      symbol: 'S',
      style: 'purple',
    },
    {
      label: 'Sucursales inactivas',
      value: inactiveBranches,
      detail: 'Registros históricos',
      symbol: '!',
      style: 'red',
    },
    {
      label: 'Disponibilidad',
      value: `${availability}%`,
      detail: 'Sucursales habilitadas',
      symbol: '%',
      style: 'blue',
    },
  ]

  return (
    <div className="branches-page">
      <header className="branches-heading">
        <h1>Gestión de sucursales</h1>

        <p>
          Administra las ubicaciones operativas de Farmacia Quilicura.
        </p>
      </header>

      <div className="branches-statistics">
        {statistics.map((statistic) => (
          <section
            className="branches-stat"
            key={statistic.label}
            aria-label={statistic.label}
          >
            <span
              className={`branches-stat-icon ${statistic.style}`}
              aria-hidden="true"
            >
              {statistic.symbol}
            </span>

            <div>
              <p>{statistic.label}</p>
              <strong>{statistic.value}</strong>
              <small>{statistic.detail}</small>
            </div>
          </section>
        ))}
      </div>

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

        <label>
          <span className="sr-only">
            Filtrar por estado
          </span>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Todos los estados</option>
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
          + Nueva sucursal
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
              Sucursales registradas
            </h2>

            <p role="status">
              {filteredBranches.length}{' '}
              {filteredBranches.length === 1
                ? 'sucursal encontrada'
                : 'sucursales encontradas'}
            </p>
          </div>

          <span className="branches-count">
            {branches.length}{' '}
            {branches.length === 1
              ? 'sucursal total'
              : 'sucursales totales'}
          </span>
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
                <th scope="col">Estado</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {filteredBranches.map((branch) => (
                <tr key={branch.id}>
                  <th scope="row">
                    <div className="branches-name">
                      <strong>{branch.name}</strong>
                      <small title={branch.id}>
                        {branch.id.slice(0, 8)}
                      </small>
                    </div>
                  </th>

                  <td>{branch.code}</td>

                  <td>{branch.address}</td>

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

                  <td>
                    <div className="branches-actions">
                      <button
                        type="button"
                        aria-label={`Editar ${branch.name}`}
                        onClick={() =>
                          openEditor({
                            mode: 'edit',
                            branch,
                          })
                        }
                      >
                        Editar
                      </button>

                      {branch.is_active && (
                        <button
                          className="danger"
                          type="button"
                          aria-label={`Desactivar ${branch.name}`}
                          onClick={() =>
                            openEditor({
                              mode: 'deactivate',
                              branch,
                            })
                          }
                        >
                          Desactivar
                        </button>
                      )}
                    </div>
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

      <section className="s1-check-note">
        <h2>Desactivación controlada</h2>

        <p>
          Una sucursal no puede desactivarse mientras tenga usuarios
          activos asignados. Primero debes reasignar o desactivar esas
          cuentas.
        </p>
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
          onDeactivate={deactivate}
        />
      )}
    </div>
  )
}