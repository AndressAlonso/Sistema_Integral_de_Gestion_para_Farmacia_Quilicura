import { apiRequest } from '../../../services/http'

export interface InternalUser {
  id: number
  name: string
  email: string
  roles: string[]
  is_active: boolean
}

export interface Role { code: string; name: string }
export interface UserList { users: InternalUser[]; roles: Role[]; current_user: InternalUser }
export interface UserInput { name: string; email: string; roles: string[] }
export interface NewUserInput extends UserInput { password: string; is_active: boolean }

async function request<T>(path: string, method = 'GET', data?: UserInput | NewUserInput): Promise<T> {
  const response = await apiRequest(`/api/users${path}`, {
    method,
    headers: data ? { 'Content-Type': 'application/json' } : undefined,
    body: data ? JSON.stringify(data) : undefined,
  }, {
    409: 'Ya existe un usuario con ese correo. Utiliza otro correo electrónico.',
    422: 'Revisa los datos obligatorios, el correo y los roles. La contraseña inicial debe tener al menos 12 caracteres.',
    400: 'No pudimos guardar los datos. Revisa el formulario.',
  })
  return response.json() as Promise<T>
}

export const listUsers = () => request<UserList>('')
export const createUser = (data: NewUserInput) => request<InternalUser>('', 'POST', data)
export const updateUser = (id: number, data: UserInput) => request<InternalUser>(`/${id}`, 'PATCH', data)
export const deactivateUser = (id: number) => request<InternalUser>(`/${id}/deactivate`, 'POST')
