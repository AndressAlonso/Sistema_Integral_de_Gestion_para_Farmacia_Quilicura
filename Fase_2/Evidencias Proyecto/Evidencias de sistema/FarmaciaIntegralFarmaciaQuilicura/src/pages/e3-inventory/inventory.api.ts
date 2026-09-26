import { apiRequest } from '../../services/http'

export interface InventoryRecord {
  id: string
  product_id: string
  product_name: string
  product_sku: string
  branch_id: string
  branch_name: string
  branch_code: string
  physical: number
  reserved: number
  available: number
}

interface InventoryListResponse {
  records: InventoryRecord[]
}

export async function listInventory(): Promise<InventoryRecord[]> {
  const response = await apiRequest('/api/inventory')
  const data: InventoryListResponse = await response.json()

  return data.records
}