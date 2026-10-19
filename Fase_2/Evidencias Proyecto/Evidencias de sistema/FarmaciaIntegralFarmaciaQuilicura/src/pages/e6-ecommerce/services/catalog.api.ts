import { apiRequest } from '../../../services/http'
import type { PublicBranch, PublicProduct } from '../types/catalog'

const messages = { 404: 'El producto o la sucursal ya no están disponibles.', 422: 'Revisa la búsqueda y la sucursal seleccionada.' }

export async function listBranches(): Promise<PublicBranch[]> {
  const data: { branches: PublicBranch[] } = await (await apiRequest('/api/ecommerce/branches', {}, messages)).json()
  return data.branches
}

export async function listProducts(q: string, branchId: string): Promise<PublicProduct[]> {
  const params = new URLSearchParams()
  if (q.trim()) params.set('q', q.trim())
  if (branchId) params.set('branch_id', branchId)
  const data: { products: PublicProduct[] } = await (await apiRequest(`/api/ecommerce/products?${params}`, {}, messages)).json()
  return data.products
}

export async function getProduct(id: string): Promise<PublicProduct> {
  return (await apiRequest(`/api/ecommerce/products/${encodeURIComponent(id)}`, {}, messages)).json()
}
