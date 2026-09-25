import { apiRequest } from '../../../services/http'

export interface InternalUser {
  id: string
  name: string
  email: string
  roles: string[]
  role_ids: string[]
  permissions: string[]
  branch_id: string
  branch_name: string
  is_active: boolean
  can_delete: boolean
  deletion_block_reason: string | null
}

export interface Role {
  id: string
  code: string
  name: string
  description: string
  permissions: Array<{
    code: string
    description: string
    implemented: boolean
  }>
}

export interface Branch {
  id: string
  name: string
  is_active: boolean
}

export interface UserList {
  users: InternalUser[]
  roles: Role[]
  branches: Branch[]
  current_user: InternalUser
}

export interface UserInput {
  name: string
  email: string
  role_ids: string[]
  branch_id: string
}

export interface NewUserInput extends UserInput {
  password: string
  is_active: boolean
}

async function request<T>(
  path: string,
  method = 'GET',
  data?: UserInput | NewUserInput,
): Promise<T> {
  const response = await apiRequest(
    `/api/users${path}`,
    {
      method,
      headers: data
        ? { 'Content-Type': 'application/json' }
        : undefined,
      body: data ? JSON.stringify(data) : undefined,
    },
    {
      409:
        'Ya existe un usuario con ese correo. Utiliza otro correo electrónico.',
      422:
        'Revisa los datos, los roles y selecciona una sucursal activa. La contraseña inicial debe tener al menos 12 caracteres.',
      400:
        'No pudimos guardar los datos. Revisa el formulario.',
    },
  )

  return response.json() as Promise<T>
}

export const listUsers = () =>
  request<UserList>('')

export const createUser = (data: NewUserInput) =>
  request<InternalUser>('', 'POST', data)

export const updateUser = (
  id: string,
  data: UserInput,
) =>
  request<InternalUser>(`/${id}`, 'PATCH', data)

export const deactivateUser = (id: string) =>
  request<InternalUser>(
    `/${id}/deactivate`,
    'POST',
  )

export const activateUser = (id: string) =>
  request<InternalUser>(`/${id}/activate`, 'POST')

export async function deleteUser(id: string, confirmationEmail: string): Promise<void> {
  await apiRequest(`/api/users/${id}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmation_email: confirmationEmail }),
  }, {
    422: 'El correo de confirmación no coincide con el usuario.',
    409: 'No se puede eliminar esta cuenta: puede ser tu cuenta, el último administrador activo o tener otros registros asociados. Utiliza Desactivar cuando corresponda.',
  })
}

export interface ManagedRole {
  id: string
  code: string
  name: string
  permission_ids: string[]
  users_count: number
  revision: string
}

export interface RoleCatalog {
  roles: ManagedRole[]
  permissions: Array<Role['permissions'][number] & { id: string; module: string }>
}

export interface RoleInput {
  name: string
  permission_ids: string[]
}

export async function listRoles(): Promise<RoleCatalog> {
  return (await apiRequest('/api/users/roles')).json() as Promise<RoleCatalog>
}

export async function saveRole(
  target: ManagedRole | null,
  data: RoleInput & { code: string },
): Promise<ManagedRole> {
  const response = await apiRequest(target ? `/api/users/roles/${target.id}` : '/api/users/roles', {
    method: target ? 'PATCH' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(target
      ? { name: data.name, permission_ids: data.permission_ids, revision: target.revision }
      : data),
  }, {
    409: 'No se pudo guardar: el código ya existe, el rol cambió o dejarías el sistema sin gestión de accesos. Recarga la lista y revisa los permisos.',
    422: 'Revisa el nombre, el código y los permisos seleccionados.',
  })
  return response.json() as Promise<ManagedRole>
}
