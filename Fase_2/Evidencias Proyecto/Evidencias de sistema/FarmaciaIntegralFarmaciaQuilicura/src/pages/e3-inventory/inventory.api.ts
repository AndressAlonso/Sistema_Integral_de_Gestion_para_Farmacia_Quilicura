import { apiRequest } from '../../services/http'

export type StockStatus =
  | 'SIN_STOCK'
  | 'BAJO'
  | 'DISPONIBLE'

export type AlertLevel =
  | 'VENCIDO'
  | 'CRITICO'
  | 'PROXIMO'
  | 'SEGUIMIENTO'

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

export interface InventoryMovement {
  id: string
  inventory_id: string

  product_id: string
  product_name: string
  product_sku: string

  branch_id: string
  branch_name: string
  branch_code: string

  user_id: string | null
  user_name: string | null

  movement_type: string

  physical_change: number
  reserved_change: number

  physical_before: number
  physical_after: number

  reserved_before: number
  reserved_after: number

  available_before: number
  available_after: number

  reason: string

  reference_type: string | null
  reference_id: string | null

  created_at: string
}

interface InventoryMovementListResponse {
  movements: InventoryMovement[]
}

export interface InventoryMovementFilters {
  inventoryId?: string
  productId?: string
  branchId?: string
  movementType?: string
  startDate?: string
  endDate?: string
}

export interface ExpirationAlert {
  lot_id: string
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

  days_remaining: number
  alert_level: AlertLevel
}

interface ExpirationAlertListResponse {
  days: number
  include_expired: boolean
  alerts: ExpirationAlert[]
}

export interface ExpirationAlertFilters {
  days?: number
  includeExpired?: boolean
  productId?: string
  branchId?: string
}

function pathWithQuery(
  path: string,
  parameters: Record<
    string,
    string | number | boolean | undefined
  >,
): string {
  const search = new URLSearchParams()

  Object.entries(parameters).forEach(([key, value]) => {
    if (
      value === undefined
      || value === ''
    ) {
      return
    }

    search.set(
      key,
      String(value),
    )
  })

  const query = search.toString()

  return query
    ? `${path}?${query}`
    : path
}

export async function listInventory(): Promise<
  InventoryRecord[]
> {
  const response = await apiRequest('/api/inventory')

  const data: InventoryListResponse =
    await response.json()

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

  const data: InventoryRecord =
    await response.json()

  return data
}

export async function listInventoryLots(
  inventoryId?: string,
): Promise<InventoryLot[]> {
  const path = inventoryId
    ? `/api/inventory/${inventoryId}/lots`
    : '/api/inventory/lots'

  const response = await apiRequest(path)

  const data: InventoryLotListResponse =
    await response.json()

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

  const data: InventoryLot =
    await response.json()

  return data
}

export async function listInventoryMovements(
  filters: InventoryMovementFilters = {},
): Promise<InventoryMovement[]> {
  const path = pathWithQuery(
    '/api/inventory/movements',
    {
      inventory_id: filters.inventoryId,
      product_id: filters.productId,
      branch_id: filters.branchId,
      movement_type: filters.movementType,
      start_date: filters.startDate,
      end_date: filters.endDate,
    },
  )

  const response = await apiRequest(path)

  const data: InventoryMovementListResponse =
    await response.json()

  return data.movements
}

export async function listExpirationAlerts(
  filters: ExpirationAlertFilters = {},
): Promise<ExpirationAlertListResponse> {
  const path = pathWithQuery(
    '/api/inventory/expiration-alerts',
    {
      days: filters.days ?? 90,
      include_expired:
        filters.includeExpired ?? true,
      product_id: filters.productId,
      branch_id: filters.branchId,
    },
  )

  const response = await apiRequest(path)

  const data: ExpirationAlertListResponse =
    await response.json()

  return data
}