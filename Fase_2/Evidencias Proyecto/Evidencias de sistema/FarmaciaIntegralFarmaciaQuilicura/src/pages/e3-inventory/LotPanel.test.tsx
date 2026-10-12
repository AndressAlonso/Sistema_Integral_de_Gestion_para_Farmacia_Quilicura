import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import LotPanel from './LotPanel'
import { listInventoryLots } from './inventory.api'
import type { InventoryLot } from './inventory.api'

vi.mock('./inventory.api', () => ({ listInventoryLots: vi.fn() }))
function lot(id: string, days: number, changes: Partial<InventoryLot> = {}): InventoryLot {
  const today = new Date()
  const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() + days)
  return { id, inventory_id: 'inventory', product_id: 'product', product_name: 'Producto QA', product_sku: 'QA',
    branch_id: 'branch', branch_name: 'Sucursal', branch_code: 'SUC', lot_number: id,
    expiration_date: [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-'),
    quantity: 10, is_active: true, created_at: '2026-01-01T00:00:00Z', ...changes }
}
async function show(lots: InventoryLot[]) {
  vi.mocked(listInventoryLots).mockResolvedValue(lots)
  render(<LotPanel inventoryRecords={[]} />)
  await screen.findByRole('region', { name: 'Lotes ordenados por vencimiento' })
}
function priority(id: string) {
  return within(screen.getByText(id, { selector: '.lot-code-primary' }).closest('tr')!).queryByText('Primero en salir')
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 12, 12))
})
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks() })
describe('E3-H2: prioridad visual FEFO', () => {
  it.each([-1, 0])('excluye lotes a %s días aunque estén habilitados y tengan unidades', async days => {
    await show([lot('No vendible', days), lot('Vendible', 1)])
    expect(priority('No vendible')).toBeNull()
    expect(priority('Vendible')).toBeTruthy()
    expect(screen.getAllByText('10')).toHaveLength(2)
  })
  it('separa estado y prioridad con etiquetas comprensibles', async () => {
    await show([lot('Ayer', -1), lot('Hoy', 0), lot('Agotado', 1, { quantity: 0 }),
      lot('Inactivo', 2, { is_active: false }), lot('Prioritario', 3), lot('Posterior', 4)])
    expect(screen.getByRole('columnheader', { name: 'Estado del lote' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Prioridad de salida:/ })).toBeTruthy()
    for (const id of ['Ayer', 'Hoy']) {
      const row = within(screen.getByText(id).closest('tr')!)
      expect(row.getByText('Vencido · No vendible')).toBeTruthy()
      expect(row.getByText('No aplica')).toBeTruthy()
    }
    expect(within(screen.getByText('Agotado').closest('tr')!).getByText('Sin unidades')).toBeTruthy()
    expect(within(screen.getByText('Inactivo').closest('tr')!).getByText('Deshabilitado')).toBeTruthy()
    expect(within(screen.getByText('Prioritario').closest('tr')!).getByText('Vigente')).toBeTruthy()
    expect(priority('Prioritario')).toBeTruthy()
    expect(within(screen.getByText('Posterior').closest('tr')!).getByText('Después')).toBeTruthy()
  })
  it('prioriza vencido y sin unidades sin repetir deshabilitado', async () => {
    await show([lot('Combinado', -1, { is_active: false, quantity: 0 })])
    const row = within(screen.getByText('Combinado').closest('tr')!)
    expect(row.getByText('Vencido · No vendible')).toBeTruthy()
    expect(row.queryByText('Deshabilitado')).toBeNull()
    expect(row.getByText('Sin unidades')).toBeTruthy()
    expect(row.getByText('No aplica')).toBeTruthy()
    expect(priority('Combinado')).toBeNull()
  })
  it('el acceso a un lote conserva la coherencia de todos los lotes de su inventario', async () => {
    vi.mocked(listInventoryLots).mockResolvedValue([lot('Destino', 1), lot('Otro lote', 2, { quantity: 5 })])
    render(<MemoryRouter><LotPanel targetLotId="Destino" inventoryRecords={[{ id: 'inventory', product_id: 'product', product_name: 'Producto QA', product_sku: 'QA', branch_id: 'branch', branch_name: 'Sucursal', branch_code: 'SUC', physical: 15, reserved: 0, available: 15, minimum: 0, stock_status: 'DISPONIBLE' }]} /></MemoryRouter>)
    await screen.findByText('Destino')
    expect(screen.queryByText('Otro lote')).toBeNull()
    expect(screen.getByText('Cantidad registrada en lotes: 15')).toBeTruthy()
    expect(screen.getByText('Diferencia: 0')).toBeTruthy()
  })
  it('mantiene la tabla vacía con el número correcto de columnas', async () => {
    await show([])
    expect(screen.getByText('No hay lotes registrados.').getAttribute('colspan')).toBe('7')
  })
  it('selecciona el primer lote vigente sin marcar el siguiente', async () => {
    await show([lot('Mañana', 1), lot('Después', 15)])
    expect(priority('Mañana')).toBeTruthy()
    expect(priority('Después')).toBeNull()
  })
  it('excluye lotes agotados y deshabilitados', async () => {
    await show([lot('Agotado', 1, { quantity: 0 }), lot('Inactivo', 2, { is_active: false }), lot('Vendible', 3)])
    expect(priority('Agotado')).toBeNull()
    expect(priority('Inactivo')).toBeNull()
    expect(priority('Vendible')).toBeTruthy()
  })
  it('no marca ninguno si todos los lotes son no vendibles', async () => {
    await show([lot('Ayer', -1), lot('Hoy', 0), lot('Agotado', 1, { quantity: 0 })])
    expect(screen.queryByText('Primero en salir')).toBeNull()
  })
  it('mantiene una prioridad independiente por inventario', async () => {
    await show([lot('Sucursal A', 1), lot('Sucursal B', 2, { inventory_id: 'inventory-b', branch_id: 'branch-b' })])
    expect(priority('Sucursal A')).toBeTruthy()
    expect(priority('Sucursal B')).toBeTruthy()
  })
  it.each([new Date(2026, 0, 31, 23, 59), new Date(2026, 8, 5, 23, 59)])('compara el día local cerca de medianoche: %s', async reference => {
    vi.setSystemTime(reference)
    await show([lot('Hoy', 0), lot('Mañana', 1)])
    expect(priority('Hoy')).toBeNull()
    expect(priority('Mañana')).toBeTruthy()
  })
})
