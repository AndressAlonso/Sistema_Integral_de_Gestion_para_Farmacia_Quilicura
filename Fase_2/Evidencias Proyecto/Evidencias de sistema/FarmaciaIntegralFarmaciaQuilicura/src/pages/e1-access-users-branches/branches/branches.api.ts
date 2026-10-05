import { apiRequest } from '../../../services/http'

export interface Branch {
  id: string
  code: string
  name: string
  address: string
  is_active: boolean
  can_delete: boolean
  assigned_users_count: number
}

export interface BranchList {
  branches: Branch[]
}

export interface BranchInput {
  code: string
  name: string
  address: string
}

export interface NewBranchInput extends BranchInput {
  is_active: boolean
}

async function request<T>(
  path: string,
  method = 'GET',
  data?: BranchInput | NewBranchInput,
  messages: Record<number, string> = {},
): Promise<T> {
  const response = await apiRequest(
    `/api/branches${path}`,
    {
      method,
      headers: data
        ? { 'Content-Type': 'application/json' }
        : undefined,
      body: data ? JSON.stringify(data) : undefined,
    },
    {
      400: 'No pudimos guardar los datos de la sucursal.',
      422: 'Revisa el código, el nombre y la dirección de la sucursal.',
      ...messages,
    },
  )

  return response.json() as Promise<T>
}

export const listBranches = () =>
  request<BranchList>('')

export interface AssignedUser {
  id: string
  name: string
  email: string
  roles: string[]
  is_active: boolean
}

export const listAssignedUsers = (branchId: string) =>
  request<{ users: AssignedUser[] }>(`/${branchId}/users`, 'GET', undefined, {
    403: 'No tienes permiso para consultar los usuarios de esta sucursal.',
    404: 'La sucursal ya no está disponible.',
  })

export const createBranch = (data: NewBranchInput) =>
  request<Branch>(
    '',
    'POST',
    data,
    {
      409: 'Ya existe una sucursal con ese código.',
    },
  )

export const updateBranch = (
  id: string,
  data: BranchInput,
) =>
  request<Branch>(
    `/${id}`,
    'PATCH',
    data,
    {
      409: 'Ya existe una sucursal con ese código.',
    },
  )

export const activateBranch = (id: string) =>
  request<Branch>(`/${id}/activate`, 'POST')

export const deactivateBranch = (id: string) =>
  request<Branch>(
    `/${id}/deactivate`,
    'POST',
    undefined,
    {
      409:
        'No se puede desactivar la sucursal porque tiene usuarios activos asignados.',
    },
  )

export async function deleteBranch(id: string, confirmationId: string): Promise<void> {
  await apiRequest(`/api/branches/${id}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmation_id: confirmationId }),
  }, {
    409: 'No se puede eliminar: existen usuarios o registros asociados a esta sucursal.',
    422: 'Escribe el ID completo de la sucursal para confirmar.',
  })
}
