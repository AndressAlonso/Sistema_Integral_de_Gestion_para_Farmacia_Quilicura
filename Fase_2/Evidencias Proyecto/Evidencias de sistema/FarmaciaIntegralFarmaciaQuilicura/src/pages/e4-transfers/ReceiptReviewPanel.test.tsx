import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ReceiptReviewPanel from './ReceiptReviewPanel'
import { reviewReceipt } from './receipt-review.api'
vi.mock('./receipt-review.api', () => ({ reviewReceipt: vi.fn() }))
const lot = { product_name: 'Producto QA', number: '2', incoming_quantity: 2, source_expiration: '2027-10-16', destination_lot_id: 'lot', destination_expiration: '2027-10-16', destination_active: false, destination_quantity: 0, conflicts: ['INACTIVE' as const], can_reactivate: true }
afterEach(cleanup)
beforeEach(() => { vi.resetAllMocks(); vi.mocked(reviewReceipt).mockResolvedValue({ destination_name: 'Centro', items: [lot] }) })
describe('Transferencias solo revisa el destino', () => {
  it('consulta explícitamente y dirige al lote en Inventario sin controles de reactivación', async () => {
    render(<MemoryRouter><ReceiptReviewPanel transferId="transfer" disabled={false} /></MemoryRouter>)
    expect(reviewReceipt).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Revisar lotes destino' }))
    const link = await screen.findByRole('link', { name: 'Ir al lote en Inventario' })
    expect(link.getAttribute('href')).toBe('/admin/inventory?tab=lots&lot_id=lot&transfer_id=transfer')
    expect(screen.queryByRole('button', { name: /Reactivar/ })).toBeNull()
    expect(screen.queryByLabelText('Motivo de reactivación')).toBeNull()
  })
  it('explica que reactivar no resuelve fechas diferentes', async () => {
    vi.mocked(reviewReceipt).mockResolvedValue({ destination_name: 'Centro', items: [{ ...lot, conflicts: ['INACTIVE', 'EXPIRATION_MISMATCH'], can_reactivate: false }] })
    render(<MemoryRouter><ReceiptReviewPanel transferId="transfer" disabled={false} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Revisar lotes destino' }))
    expect(await screen.findByText(/Los vencimientos no coinciden/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Reactivar/ })).toBeNull()
  })
})
