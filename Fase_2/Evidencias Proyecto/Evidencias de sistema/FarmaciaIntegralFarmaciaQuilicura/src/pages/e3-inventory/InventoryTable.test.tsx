import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import InventoryTable from './InventoryTable'
import type { InventoryRecord } from './inventory.api'

afterEach(cleanup)
const record: InventoryRecord = {
  id: 'qa', product_id: 'p', product_name: 'Producto QA', product_sku: 'QA',
  branch_id: 'b', branch_name: 'Centro', branch_code: 'LOCAL-QA',
  physical: 20, reserved: 5, available: 15, minimum: 10, stock_status: 'DISPONIBLE',
}
it('mantiene la consulta y oculta configurar cuando falta el permiso', () => {
  const { rerender } = render(<InventoryTable records={[record]} canConfigureMinimum={false} onRecordUpdated={vi.fn()} />)
  expect(screen.getByText('Producto QA')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Configurar aviso' })).toBeNull()
  rerender(<InventoryTable records={[record]} canConfigureMinimum onRecordUpdated={vi.fn()} />)
  expect(screen.getByRole('button', { name: 'Configurar aviso' })).toBeTruthy()
  rerender(<InventoryTable records={[record]} canConfigureMinimum={false} onRecordUpdated={vi.fn()} />)
  expect(screen.queryByRole('button', { name: 'Configurar aviso' })).toBeNull()
})
