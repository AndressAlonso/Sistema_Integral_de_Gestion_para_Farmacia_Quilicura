import { useEffect, useState } from 'react'
import { ApiError } from '../../../services/http'
import { listAssignedUsers, type AssignedUser } from './branches.api'

export default function AssignedUsers({ branchId }: { branchId: string }) {
  const [users, setUsers] = useState<AssignedUser[] | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    let active = true
    listAssignedUsers(branchId).then(data => {
      if (active) setUsers(data.users)
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof ApiError ? cause.message : 'No pudimos cargar los usuarios asignados.')
    })
    return () => { active = false }
  }, [branchId, attempt])

  if (error) return <div><p className="s1-error" role="alert">{error}</p><button type="button" className="branches-button" onClick={() => { setError(''); setUsers(null); setAttempt(value => value + 1) }}>Reintentar</button></div>
  if (!users) return <p role="status">Cargando usuarios asignados…</p>
  const normalized = query.trim().toLocaleLowerCase('es')
  const visible = users.filter(user =>
    `${user.name} ${user.email}`.toLocaleLowerCase('es').includes(normalized) &&
    (!status || user.is_active === (status === 'active')),
  )

  return <div className="branches-assigned-content">
    {users.length > 0 ? <>
      <div className="branches-assigned-filters">
        <label>Buscar usuario<input type="search" placeholder="Nombre o correo" value={query} onChange={event => setQuery(event.target.value)} /></label>
        <label>Estado<select value={status} onChange={event => setStatus(event.target.value)}><option value="">Todos</option><option value="active">Activos</option><option value="inactive">Inactivos</option></select></label>
      </div>
      <p role="status">{visible.length} {visible.length === 1 ? 'resultado' : 'resultados'}</p>
      <div className="branches-table-scroll" tabIndex={0} role="region" aria-label="Usuarios asignados a la sucursal">
        <table className="branches-table"><thead><tr><th scope="col">Usuario</th><th scope="col">Correo</th><th scope="col">Roles</th><th scope="col">Estado</th></tr></thead><tbody>
          {visible.map(user => <tr key={user.id}><th scope="row">{user.name}</th><td>{user.email}</td><td>{user.roles.join(', ') || 'Sin rol asignado'}</td><td><span className={`branches-status${user.is_active ? '' : ' inactive'}`}>{user.is_active ? 'Activo' : 'Inactivo'}</span></td></tr>)}
          {visible.length === 0 && <tr><td colSpan={4} className="branches-empty">No hay usuarios que coincidan con los filtros.</td></tr>}
        </tbody></table>
      </div>
    </> : <p className="s1-muted">Todavía no hay usuarios asignados a esta sucursal.</p>}
  </div>
}
