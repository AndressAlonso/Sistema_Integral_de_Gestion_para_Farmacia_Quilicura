import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { apiRequest } from '../../services/http'
import AuditPage from './AuditPage'

vi.mock('../../services/http', () => ({ apiRequest: vi.fn() }))
vi.mock('../../components/Notification', () => ({ default: ({ message }: { message: string }) => <div role="alert">{message}</div> }))
const result = { events: [{ id: 'e1', at: '2026-01-10T15:00:00Z', action: 'usuario_interno.actualizado', reference: 'Usuario Ana', actor: { id: 'u1', name: 'Andrés histórico' }, branch: { id: 'b1', name: 'Centro' }, data: { cambios: { nombre: { anterior: 'Ana', nuevo: 'Ana María' } } } }], total: 21, page: 1, limit: 20, branches: [{ id: 'b1', name: 'Centro' }] }
beforeEach(() => {
  vi.mocked(apiRequest).mockResolvedValue({ json: async () => result } as Response)
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
})
afterEach(() => { cleanup(); vi.resetAllMocks() })

it('envía sucursal y período juntos y reinicia la página al filtrar', async () => {
  render(<AuditPage />)
  await screen.findByText('Andrés histórico')
  fireEvent.click(screen.getByText('Siguiente'))
  await waitFor(() => expect(vi.mocked(apiRequest).mock.lastCall?.[0]).toContain('page=2'))
  await screen.findByText('Andrés histórico')
  fireEvent.change(screen.getByLabelText('Sucursal'), { target: { value: 'b1' } })
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-01-01' } })
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-01-31' } })
  fireEvent.click(screen.getByText('Aplicar filtros'))
  await waitFor(() => expect(vi.mocked(apiRequest).mock.lastCall?.[0]).toBe('/api/audit?page=1&limit=20&branch_id=b1&date_from=2026-01-01&date_to=2026-01-31'))
})

it('abre el detalle histórico mediante un botón accesible y permite cerrarlo', async () => {
  render(<AuditPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'Ver detalle de Usuario Ana' }))
  expect(screen.getByRole('dialog')).toBeTruthy()
  expect(screen.getByText('Ana María')).toBeTruthy()
  fireEvent.click(screen.getByLabelText('Cerrar detalle'))
  expect(screen.queryByRole('dialog')).toBeNull()
})

it('rechaza un período invertido sin consultar y permite reintentar errores', async () => {
  render(<AuditPage />)
  await screen.findByText('Andrés histórico')
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-02-01' } })
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-01-01' } })
  fireEvent.click(screen.getByText('Aplicar filtros'))
  expect(screen.getByRole('alert').textContent).toContain('posterior')
  expect(apiRequest).toHaveBeenCalledTimes(1)
  vi.mocked(apiRequest).mockRejectedValueOnce(new Error('Sin conexión'))
  fireEvent.click(screen.getByLabelText('Actualizar auditoría'))
  await screen.findByText('Sin conexión')
  fireEvent.click(screen.getByText('Reintentar'))
  await screen.findByText('Andrés histórico')
})

it('presenta un resultado vacío', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce({ json: async () => ({ ...result, events: [], total: 0 }) } as Response)
  render(<AuditPage />)
  expect(await screen.findByText('No hay operaciones para estos filtros.')).toBeTruthy()
})
