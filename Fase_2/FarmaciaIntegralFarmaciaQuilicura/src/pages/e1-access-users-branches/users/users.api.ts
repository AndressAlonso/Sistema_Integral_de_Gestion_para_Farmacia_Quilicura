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
}

export interface Role {
  id: string
  code: string
  name: string
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