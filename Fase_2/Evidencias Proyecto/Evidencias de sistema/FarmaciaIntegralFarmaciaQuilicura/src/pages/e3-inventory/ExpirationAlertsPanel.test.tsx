import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ExpirationAlertsPanel from './ExpirationAlertsPanel'
import { type InventoryLot, listInventoryLots } from './inventory.api'

vi.mock('./inventory.api', () => ({ listInventoryLots: vi.fn() }))

const cases = [
  [-1, 'Vencido'], [0, 'Vencido'], [1, 'Crítico'],
  [15, 'Crítico'], [16, 'Próximo a vencer'], [30, 'Próximo a vencer'],
  [31, 'Sin alerta'], [60, 'Sin alerta'], [61, 'Sin alerta'],
] as const

function makeLot(days: number, reference = new Date(2026, 11, 31, 12)): InventoryLot {
  const expiration = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate() + days)
  const date = [expiration.getFullYear(), String(expiration.getMonth() + 1).padStart(2, '0'),
    String(expiration.getDate()).padStart(2, '0')].join('-')
  return {
    id: `lot-${days}`, inventory_id: 'inventory', product_id: 'product',
    product_name: `Producto ${days}`, product_sku: 'SKU', branch_id: 'branch',
    branch_name: 'Sucursal', branch_code: 'SUC', lot_number: `L-${days}`,
    expiration_date: date, quantity: 5, is_active: true, created_at: '2026-01-01T00:00:00Z',
  }
}

async function showPanel(lots = cases.map(([days]) => makeLot(days))) {
  vi.mocked(listInventoryLots).mockResolvedValue(lots)
  render(<ExpirationAlertsPanel inventoryRecords={[]} />)
  await waitFor(() => expect(screen.queryByText('Cargando fechas de vencimiento…')).toBeNull())
}

function applyFilter(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Aplicar filtros' }))
}

beforeEach(() => {
  // Solo falsea Date: los temporizadores de React y waitFor siguen siendo reales.
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 11, 31, 12))
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('E3-H4: alertas de vencimiento', () => {
  it('clasifica todos los límites oficiales y conserva el total de lotes', async () => {
    await showPanel()
    for (const [days, label] of cases) {
      const row = screen.getByText(`L-${days}`).closest('tr')!
      expect(within(row).getByText(label)).toBeTruthy()
    }
    expect(screen.getByText('Vencido hoy')).toBeTruthy()
    expect(screen.getByText('9 lotes encontrados')).toBeTruthy()
    expect(screen.queryByText(/0 a 30|31 a 60|más de 60|Vencimiento lejano/)).toBeNull()
  })

  it.each([
    ['VENCIDO', 2], ['CRITICO', 2], ['PROXIMO', 2], ['SEGUIMIENTO', 3],
  ])('filtra %s y actualiza el contador', async (status, count) => {
    await showPanel()
    applyFilter('Estado del vencimiento', status as string)
    expect(screen.getByText(`${count} lotes encontrados`)).toBeTruthy()
    expect(screen.getAllByRole('row')).toHaveLength(Number(count) + 1)
  })

  it('incluye hoy en vencidos y excluye hoy de los períodos futuros', async () => {
    await showPanel([-1, 0, 1, 90, 91].map((days) => makeLot(days)))
    applyFilter('Periodo de vencimiento', 'EXPIRED')
    expect(screen.getByText('L--1')).toBeTruthy()
    expect(screen.getByText('L-0')).toBeTruthy()
    expect(screen.queryByText('L-1')).toBeNull()
    applyFilter('Periodo de vencimiento', '90')
    expect(screen.queryByText('L--1')).toBeNull()
    expect(screen.queryByText('L-0')).toBeNull()
    expect(screen.getByText('L-1')).toBeTruthy()
    expect(screen.getByText('L-90')).toBeTruthy()
    expect(screen.queryByText('L-91')).toBeNull()
    expect(screen.getByText('2 lotes encontrados')).toBeTruthy()
  })

  it.each([new Date(2026, 0, 31, 23, 59), new Date(2026, 8, 5, 23, 59)])(
    'cuenta días de calendario al cruzar mes o cambio de horario: %s', async (reference) => {
      vi.setSystemTime(reference)
      await showPanel([makeLot(1, reference)])
      expect(screen.getByText('1 día restante')).toBeTruthy()
      expect(screen.getByText('Crítico')).toBeTruthy()
    },
  )
})
