import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import OrdersPage from './OrdersPage'
import { listOrders } from './orders.api'

vi.mock('./orders.api', async () => ({ ...await vi.importActual('./orders.api'), listOrders: vi.fn() }))
vi.mock('./OrderPreparationDialog', () => ({ default: ({ id, onClose }: { id: string; onClose: () => void }) => <div role="dialog" aria-label={`Detalle ${id}`}><button onClick={onClose}>Cerrar</button></div> }))
afterEach(cleanup)

it('abre el detalle desde cualquier celda y conserva el botón accesible', async () => {
  vi.mocked(listOrders).mockResolvedValue({ page: 1, limit: 15, total: 1, branches: [{ id: 'branch', name: 'Centro' }], orders: [{ id: 'qa', number: 'WEB-QA', status: 'PAGADO', created_at: '2026-10-20T12:00:00Z', currency: 'CLP', total: '100', pickup_branch: { id: 'branch', name: 'Centro' }, items: [] }] })
  render(<OrdersPage />)
  fireEvent.click(await screen.findByRole('cell', { name: 'Centro' }))
  expect(screen.getByRole('dialog', { name: 'Detalle qa' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
  const button = screen.getByRole('button', { name: 'Abrir pedido WEB-QA' })
  button.focus()
  expect(document.activeElement).toBe(button)
  fireEvent.click(button)
  expect(screen.getAllByRole('dialog')).toHaveLength(1)
})
