import { apiRequest } from '../../services/http'
import type { OperationalFilters } from './filters'

export interface DashboardData {
  branches: { id: string; name: string }[]
  period: { date_from: string; date_to: string }
  sales: { total: string; count: number; average: string; returns: string; net: string }
  daily: { date: string; total: string; count: number }[]
  payments: { method: string; total: string; count: number }[]
  by_branch: { id: string; name: string; total: string; count: number }[]
  top_products: { id: string; name: string; quantity: number }[]
  movements: { type: string; count: number; physical: number; reserved: number }[]
  inventory: {
    as_of: string; low_count: number; expiring_count: number; expired_count: number
    low_stock: { id: string; name: string; branch: string; available: number; minimum: number }[]
    expiring: { id: string; name: string; branch: string; lot: string; date: string; quantity: number; days: number }[]
  }
}
export async function getDashboard(filters: OperationalFilters): Promise<DashboardData> {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value) })
  const response = await apiRequest(`/api/dashboard?${query}`, {}, {}, true)
  return response.json()
}
export const currency = (value: string | number) => new Intl.NumberFormat('es-CL', {
  style: 'currency', currency: 'CLP', maximumFractionDigits: 0,
}).format(Number(value))
export const number = (value: number) => value.toLocaleString('es-CL')
