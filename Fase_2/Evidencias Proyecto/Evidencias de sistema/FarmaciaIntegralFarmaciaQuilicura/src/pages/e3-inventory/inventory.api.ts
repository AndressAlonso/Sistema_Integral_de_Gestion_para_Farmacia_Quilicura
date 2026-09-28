import { apiRequest } from '../../services/http'

export type StockStatus =
  | 'SIN_STOCK'
  | 'BAJO'
  | 'DISPONIBLE'

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
  minimum: number
  stock_status: StockStatus
}

interface InventoryListResponse {
  records: InventoryRecord[]
}

export interface InventoryLot {
  id: string
  inventory_id: string
  product_id: string
  product_name: string
  product_sku: string
  branch_id: string
  branch_name: string
  branch_code: string
  lot_number: string
  expiration_date: string
  quantity: number
  is_active: boolean
  created_at: string
}

interface InventoryLotListResponse {
  lots: InventoryLot[]
}

export interface CreateInventoryLot {
  inventory_id: string
  lot_number: string
  expiration_date: string
  quantity: number
}

export async function listInventory(): Promise<InventoryRecord[]> {
  const response = await apiRequest('/api/inventory')
  const data: InventoryListResponse = await response.json()

  return data.records
}

export async function updateInventoryMinimum(
  inventoryId: string,
  minimum: number,
): Promise<InventoryRecord> {
  const response = await apiRequest(
    `/api/inventory/${inventoryId}/minimum`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        minimum,
      }),
    },
  )

  const data: InventoryRecord = await response.json()

  return data
}

export async function listInventoryLots(
  inventoryId?: string,
): Promise<InventoryLot[]> {
  const path = inventoryId
    ? `/api/inventory/${inventoryId}/lots`
    : '/api/inventory/lots'

  const response = await apiRequest(path)
  const data: InventoryLotListResponse = await response.json()

  return data.lots
}

export async function createInventoryLot(
  input: CreateInventoryLot,
): Promise<InventoryLot> {
  const response = await apiRequest(
    '/api/inventory/lots',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    },
  )

  const data: InventoryLot = await response.json()

  return data
}