import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../../../services/http'
import UserDialog, { type UserEditor } from './UserDialog'
import { createUser, deactivateUser, listUsers, updateUser, type InternalUser, type NewUserInput, type UserInput, type UserList } from './users.api'
import './users.css'

export default function UsersPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<UserList | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('')
  const [editor, setEditor] = useState<UserEditor | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const sending = useRef(false)

  useEffect(() => {
    let active = true
    listUsers().then(result => {
      if (active) { setData(result); setLoading(false) }
    }).catch((cause: unknown) => {
      if (!active) return
      if (cause instanceof ApiError && cause.status === 401) navigate('/login', { replace: true })
      setLoadError(cause instanceof ApiError ? cause.message : 'No pudimos cargar los usuarios.')
      setLoading(false)
    })
    return () => { active = false }
  }, [attempt, navigate])

  function openEditor(value: UserEditor) {
    setError('')
    setMessage('')
    setEditor(value)
  }

  async function mutate(operation: () => Promise<InternalUser>, success: string) {
    if (sending.current) return
    sending.current = true
    setBusy(true)
    setError('')
    try {
      const saved = await operation()
      setData(current => current ? {
        ...current,
        users: current.users.some(user => user.id === saved.id)
          ? current.users.map(user => user.id === saved.id ? saved : user)
          : [...current.users, saved],
        current_user: current.current_user.id === saved.id ? saved : current.current_user,
      } : null)
      setEditor(null)
      setMessage(success)
      if (saved.id === data?.current_user.id) {
        if (!saved.is_active) navigate('/login', { replace: true })
        else if (!saved.permissions.includes('usuarios.gestionar')) navigate('/session', { replace: true })
      }
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) navigate('/login', { replace: true })
      if (cause instanceof ApiError && cause.status === 403) {
        setEditor(null)
        setData(null)
        setLoadError(cause.message)
      } else setError(cause instanceof ApiError ? cause.message : 'No pudimos guardar el usuario. Intenta nuevamente.')
    } finally {
      sending.current = false
      setBusy(false)
    }
  }

  async function save(input: UserInput | NewUserInput) {
    if (editor?.mode === 'create' && 'password' in input) await mutate(() => createUser(input), 'Usuario creado correctamente.')
    else if (editor?.user) {
      const id = editor.user.id
      await mutate(() => updateUser(id, input), 'Usuario actualizado correctamente.')
    }
  }

  async function deactivate() {
    if (!editor?.user) return
    const id = editor.user.id
    await mutate(() => deactivateUser(id), 'Usuario desactivado. Su acceso al sistema quedó bloqueado.')
  }

  if (loading) return <p role="status">Cargando usuarios…</p>
  if (loadError) return <div><p className="users-error" role="alert">{loadError}</p><button className="users-button" onClick={() => { setLoading(true); setLoadError(''); setAttempt(value => value + 1) }}>Reintentar</button></div>
  if (!data) return null
  const normalized = query.trim().toLocaleLowerCase('es')
  const users = data.users.filter(user =>
    (!normalized || `${user.name} ${user.email}`.toLocaleLowerCase('es').includes(normalized)) &&
    (!role || user.roles.includes(role)) &&
    (!status || user.is_active === (status === 'active')),
  )
  const statistics = [
    { label: 'Usuarios activos', value: data.users.filter(user => user.is_active).length, detail: 'Personal habilitado', symbol: '♙', style: 'green' },
    { label: 'Administradores', value: data.users.filter(user => user.roles.includes('ADMIN')).length, detail: 'Gestión de usuarios', symbol: 'A', style: 'purple' },
    { label: 'Usuarios registrados', value: data.users.length, detail: 'Cuentas del sistema', symbol: 'U', style: 'green' },
    { label: 'Cuentas inactivas', value: data.users.filter(user => !user.is_active).length, detail: 'Acceso deshabilitado', symbol: '!', style: 'red' },
  ]

  return (
    <div className="users-page">
      <header className="users-heading"><h1>Gestión de usuarios</h1><p>Administra las cuentas y el acceso del personal interno.</p></header>
      <div className="users-statistics">{statistics.map(stat => <section className="users-stat" key={stat.label} aria-label={stat.label}><span className={`users-stat-icon ${stat.style}`} aria-hidden="true">{stat.symbol}</span><div><p>{stat.label}</p><strong>{stat.value}</strong><small>{stat.detail}</small></div></section>)}</div>
      <div className="users-filters">
        <label className="users-search"><span className="sr-only">Buscar por nombre o correo</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5" /></svg><input type="search" placeholder="Buscar por nombre o correo…" value={query} onChange={event => setQuery(event.target.value)} /></label>
        <label><span className="sr-only">Filtrar por rol</span><select value={role} onChange={event => setRole(event.target.value)}><option value="">Todos los roles</option>{data.roles.map(item => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>
        <label><span className="sr-only">Filtrar por estado</span><select value={status} onChange={event => setStatus(event.target.value)}><option value="">Todos los estados</option><option value="active">Activos</option><option value="inactive">Inactivos</option></select></label>
        <button className="users-button primary" disabled={!data.current_user.permissions.includes('roles.gestionar')} title={!data.current_user.permissions.includes('roles.gestionar') ? 'Se requiere permiso para asignar roles' : undefined} onClick={() => openEditor({ mode: 'create', user: null })}>+ Nuevo usuario</button>
      </div>
      {message && <p className="users-success" role="status">{message}</p>}
      <section className="users-panel" aria-labelledby="users-list-title">
        <div className="users-panel-heading"><h2 id="users-list-title">Usuarios internos</h2><p role="status">{users.length} {users.length === 1 ? 'usuario encontrado' : 'usuarios encontrados'}</p></div>
        <div className="users-table-scroll" tabIndex={0} role="region" aria-label="Listado de usuarios internos">
          <table className="users-table"><thead><tr><th scope="col">Usuario</th><th scope="col">Correo</th><th scope="col">Rol</th><th scope="col">Sucursal</th><th scope="col">Estado</th><th scope="col">Acciones</th></tr></thead><tbody>
            {users.map(user => <tr key={user.id}>
              <th scope="row"><div className="users-name"><span className="users-initials" aria-hidden="true">{(user.name || user.email).split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</span><div>{user.name || 'Sin nombre registrado'}<small title={user.id}>{user.id.slice(0, 8)}</small></div></div></th>
              <td>{user.email}</td><td>{user.roles.map(code => data.roles.find(item => item.code === code)?.name ?? code).join(', ') || 'Sin rol asignado'}</td>
              <td>{user.branch_name}</td><td><span className={`users-status ${user.is_active ? '' : 'inactive'}`}>{user.is_active ? 'Activo' : 'Inactivo'}</span></td>
              <td><div className="users-row-actions"><button aria-label={`Editar ${user.name || user.email}`} onClick={() => openEditor({ mode: 'edit', user })}>Editar</button>{user.is_active && <button className="users-deactivate" aria-label={`Desactivar ${user.name || user.email}`} onClick={() => openEditor({ mode: 'deactivate', user })}>Desactivar</button>}</div></td>
            </tr>)}
            {users.length === 0 && <tr><td colSpan={6} className="users-empty">No se encontraron usuarios con esos filtros.</td></tr>}
          </tbody></table>
        </div>
      </section>
      {editor && <UserDialog key={`${editor.mode}-${editor.user?.id ?? 'new'}`} editor={editor} roles={data.roles} branches={data.branches} canAssignRoles={data.current_user.permissions.includes('roles.gestionar')} busy={busy} error={error} onClose={() => { if (!sending.current) setEditor(null) }} onSave={save} onDeactivate={deactivate} />}
    </div>
  )
}
