import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../../../services/http'
import ActionIcon from '../ActionIcon'
import { listRoles, saveRole, type ManagedRole, type RoleCatalog } from './users.api'

interface Props {
  onClose: () => void
  onSaved: () => void
}

export default function RoleDialog({ onClose, onSaved }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const sending = useRef(false)
  const [catalog, setCatalog] = useState<RoleCatalog | null>(null)
  const [target, setTarget] = useState<ManagedRole | null>(null)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [codeEdited, setCodeEdited] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [discard, setDiscard] = useState<ManagedRole | 'new' | 'close' | 'reload' | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => element?.close()
  }, [])

  useEffect(() => {
    let active = true
    listRoles().then(result => {
      if (!active) return
      setCatalog(result)
      setLoading(false)
    }).catch((cause: unknown) => {
      if (!active) return
      setError(cause instanceof ApiError ? cause.message : 'No pudimos cargar los roles.')
      setLoading(false)
    })
    return () => { active = false }
  }, [attempt])

  const dirty = target
    ? name !== target.name || [...selected].sort().join() !== [...target.permission_ids].sort().join()
    : Boolean(name || code || selected.length)

  function choose(value: ManagedRole | 'new' | 'close' | 'reload') {
    if (sending.current) return
    if (dirty) { setDiscard(value); return }
    applyChoice(value)
  }

  function applyChoice(value: ManagedRole | 'new' | 'close' | 'reload') {
    setDiscard(null)
    if (value === 'close') { onClose(); return }
    const next = typeof value === 'string' ? null : value
    setTarget(next)
    setName(next?.name ?? '')
    setCode(next?.code ?? '')
    setSelected(next?.permission_ids ?? [])
    setCodeEdited(false)
    setConfirming(false)
    setError('')
    setMessage('')
    if (value === 'reload') {
      setLoading(true)
      setCatalog(null)
      setAttempt(current => current + 1)
    }
  }

  async function persist() {
    if (sending.current) return
    sending.current = true
    setBusy(true)
    setError('')
    try {
      const saved = await saveRole(target, { name: name.trim(), code: code.trim(), permission_ids: selected })
      setCatalog(current => current ? {
        ...current,
        roles: [...current.roles.filter(role => role.id !== saved.id), saved]
          .sort((first, second) => first.name.localeCompare(second.name, 'es')),
      } : current)
      setTarget(saved)
      setName(saved.name)
      setCode(saved.code)
      setSelected(saved.permission_ids)
      setConfirming(false)
      setMessage('Rol guardado. Sus permisos se aplican a todos los usuarios que lo tienen asignado.')
      onSaved()
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'No pudimos guardar el rol.')
      setConfirming(false)
    } finally {
      sending.current = false
      setBusy(false)
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || !dirty) return
    setError('')
    setMessage('')
    if (!name.trim() || !/^[A-Z][A-Z0-9_]{0,59}$/.test(code)) {
      setError('Escribe un nombre y un código válido.'); return
    }
    if (target && target.users_count > 0) setConfirming(true)
    else void persist()
  }

  const matches = catalog?.roles.filter(role => `${role.name} ${role.code}`.toLocaleLowerCase('es').includes(query.trim().toLocaleLowerCase('es'))) ?? []
  const modules = [...new Set(catalog?.permissions.map(permission => permission.module) ?? [])]

  return <dialog ref={dialog} className="users-dialog users-dialog-fullscreen roles-dialog app-modal" aria-labelledby="roles-title" onCancel={event => { event.preventDefault(); choose('close') }}>
    <div className="roles-dialog-content">
      <header className="users-dialog-heading"><div><h2 id="roles-title">Gestionar roles</h2><p>Define las responsabilidades y los permisos del personal.</p></div><button type="button" className="users-close" aria-label="Cerrar gestor de roles" disabled={busy} onClick={() => choose('close')}>×</button></header>
      {message && <p className="users-success" role="status">{message}</p>}
      {error && <div role="alert"><p className="users-error">{error}</p><button type="button" className="users-button" disabled={busy} onClick={() => choose('reload')}>Recargar lista</button></div>}
      {discard ? <section className="roles-confirm" aria-labelledby="role-discard-title"><h3 id="role-discard-title">Cambios sin guardar</h3><p>Si continúas, se descartarán los cambios del rol que estás editando.</p><div><button type="button" className="users-button" onClick={() => setDiscard(null)}>Seguir editando</button><button type="button" className="users-button danger" onClick={() => applyChoice(discard)}>Descartar y continuar</button></div></section>
        : confirming ? <section className="roles-confirm" aria-labelledby="role-confirm-title"><h3 id="role-confirm-title">Confirmar cambios en {target?.name}</h3><p>Este cambio afectará a los <strong>{target?.users_count} usuarios</strong> que tienen este rol. Se aplicará también a sus sesiones actuales. Los permisos de sus otros roles se conservarán.</p><div><button type="button" className="users-button" disabled={busy} onClick={() => setConfirming(false)}>Volver a editar</button><button type="button" className="users-button primary" disabled={busy} onClick={() => void persist()}>{busy ? 'Guardando…' : 'Confirmar cambios'}</button></div></section>
          : loading ? <p role="status">Cargando roles y permisos…</p> : catalog && <div className="roles-workspace">
            <aside className="roles-sidebar" aria-label="Roles existentes">
              <button type="button" className="users-button primary" disabled={busy} onClick={() => choose('new')}><ActionIcon name="add" />Nuevo rol</button>
              <label>Buscar rol<input type="search" value={query} placeholder="Nombre o código" onChange={event => setQuery(event.target.value)} /></label>
              <ul>{matches.map(role => <li key={role.id}><button type="button" disabled={busy} aria-pressed={target?.id === role.id} onClick={() => choose(role)}><strong>{role.name}</strong><span>{role.users_count} usuarios · {role.permission_ids.length} permisos</span></button></li>)}</ul>
              {matches.length === 0 && <p>No hay roles que coincidan.</p>}
            </aside>
            <form className="roles-editor" onSubmit={submit} aria-busy={busy}>
              <fieldset disabled={busy}><legend>{target ? 'Configurar rol' : 'Crear rol'}</legend>
                <div className="roles-fields"><label>Nombre del rol<input required maxLength={100} value={name} placeholder="Ej.: Supervisor" onChange={event => {
                  const value = event.target.value
                  setName(value)
                  if (!target && !codeEdited) setCode(value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60))
                }} /></label><label>Código<input required readOnly={Boolean(target)} maxLength={60} pattern="[A-Z][A-Z0-9_]*" value={code} onChange={event => { setCodeEdited(true); setCode(event.target.value.toUpperCase()) }} /><small>{target ? 'El código se conserva para mantener las asignaciones existentes.' : 'Código único sugerido. Puedes ajustarlo antes de crear el rol.'}</small></label></div>
                {target && <p className="roles-impact">Asignado a <strong>{target.users_count} usuarios</strong>. Los cambios se aplicarán a todos ellos.</p>}
                <h3>Permisos del rol</h3><p>Selecciona los accesos. Los permisos de todos los roles de un usuario se suman.</p>
                {modules.map(module => <fieldset className="roles-permission-group" key={module}><legend>{module}</legend>{catalog.permissions.filter(permission => permission.module === module).map(permission => <label key={permission.id}><input type="checkbox" checked={selected.includes(permission.id)} onChange={event => setSelected(current => event.target.checked ? [...current, permission.id] : current.filter(id => id !== permission.id))} /><span><strong>{permission.description}</strong><small>{permission.implemented ? 'Disponible' : 'Módulo pendiente: este permiso no implementa la funcionalidad.'}</small></span></label>)}</fieldset>)}
                {selected.length === 0 && <p className="roles-impact">Este rol no otorgará permisos operativos.</p>}
              </fieldset>
              <footer className="users-dialog-actions"><button type="button" className="users-button" disabled={busy} onClick={() => choose('close')}>Cancelar</button><button type="submit" className="users-button primary" disabled={busy || !dirty}>{busy ? 'Guardando…' : target ? 'Guardar cambios' : 'Crear rol'}</button></footer>
            </form>
          </div>}
    </div>
  </dialog>
}
