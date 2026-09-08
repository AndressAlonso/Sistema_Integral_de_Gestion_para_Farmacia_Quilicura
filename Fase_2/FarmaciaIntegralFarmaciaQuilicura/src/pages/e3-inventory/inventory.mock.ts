export interface InventoryRecord {
  id: string
  product: string
  presentation: string
  branch: string
  physical: number
  reserved: number
}

export const inventoryRecords: InventoryRecord[] = [
  { id: 'INV-001', product: 'Paracetamol 500 mg', presentation: 'Caja de 16 comprimidos', branch: 'Sucursal A', physical: 120, reserved: 18 },
  { id: 'INV-002', product: 'Paracetamol 500 mg', presentation: 'Caja de 16 comprimidos', branch: 'Sucursal B', physical: 45, reserved: 5 },
  { id: 'INV-003', product: 'Suero fisiológico 0,9 %', presentation: 'Frasco de 500 ml', branch: 'Sucursal A', physical: 36, reserved: 6 },
  { id: 'INV-004', product: 'Suero fisiológico 0,9 %', presentation: 'Frasco de 500 ml', branch: 'Sucursal B', physical: 12, reserved: 12 },
  { id: 'INV-005', product: 'Gasas estériles', presentation: 'Envase de 10 unidades', branch: 'Sucursal A', physical: 64, reserved: 0 },
  { id: 'INV-006', product: 'Gasas estériles', presentation: 'Envase de 10 unidades', branch: 'Sucursal B', physical: 0, reserved: 0 },
]

export function getAvailableStock(record: InventoryRecord): number | null {
  if (!Number.isInteger(record.physical) || !Number.isInteger(record.reserved)
    || record.physical < 0 || record.reserved < 0 || record.reserved > record.physical) {
    return null
  }
  return record.physical - record.reserved
}

