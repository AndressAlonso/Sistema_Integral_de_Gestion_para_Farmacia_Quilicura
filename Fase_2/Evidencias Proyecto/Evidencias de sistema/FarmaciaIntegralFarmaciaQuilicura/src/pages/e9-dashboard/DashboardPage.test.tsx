import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { canAccessAdminPage } from '../../layouts/adminNavigation'
import { apiRequest } from '../../services/http'
import DashboardPage from './DashboardPage'
import { dashboardFixture } from './dashboard.fixture'
import { chileToday, presetDates } from './filters'

vi.mock('../../services/http', () => ({ apiRequest: vi.fn() }))
vi.mock('../../components/Notification', () => ({ default: ({ message }: { message: string }) => <div role="alert">{message}</div> }))
beforeEach(() => { vi.mocked(apiRequest).mockResolvedValue({ json: async () => dashboardFixture } as Response) })
afterEach(() => { cleanup(); vi.resetAllMocks() })

describe('E9-H1 / E9-H3', () => {
  it('presenta indicadores, gráficos y alertas con datos del backend', async () => {
    render(<DashboardPage />)
    await screen.findByText('94 ventas · POS y online')
    expect(screen.getByRole('group', { name: 'Ventas registradas por día' })).toBeTruthy()
    expect(screen.getByRole('img', { name: /Distribución de/ })).toBeTruthy()
    expect(screen.getByText('Agotado')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Por vencer/ }))
    expect(screen.getByText('Lote VC-2601')).toBeTruthy()
  })
  it('filtra inmediatamente por sucursal y conserva el período', async () => {
    render(<DashboardPage />)
    await screen.findByText('94 ventas · POS y online')
    fireEvent.click(screen.getByRole('button', { name: 'Quilicura Centro' }))
    await waitFor(() => expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining('branch_id=b1'), {}, {}, true))
    await screen.findByText('94 ventas · POS y online')
    fireEvent.click(screen.getByRole('button', { name: '7 días' }))
    await waitFor(() => expect(vi.mocked(apiRequest).mock.lastCall?.[0]).toContain(`branch_id=b1&date_from=${presetDates('week').date_from}&date_to=${chileToday()}`))
  })
  it('permite filtrar desde el gráfico de sucursales y volver a todas', async () => {
    render(<DashboardPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Filtrar por Lo Marcoleta' }))
    await waitFor(() => expect(vi.mocked(apiRequest).mock.lastCall?.[0]).toContain('branch_id=b2'))
    fireEvent.click(screen.getByRole('button', { name: 'Todas' }))
    await waitFor(() => expect(vi.mocked(apiRequest).mock.lastCall?.[0]).not.toContain('branch_id='))
  })
  it('no consulta un rango inválido y aplica las fechas personalizadas juntas', async () => {
    render(<DashboardPage />)
    await screen.findByText('94 ventas · POS y online')
    fireEvent.click(screen.getByRole('button', { name: 'Personalizado' }))
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-11-10' } })
    fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-11-01' } })
    fireEvent.click(screen.getByText('Aplicar período'))
    expect(screen.getByRole('alert').textContent).toContain('posterior')
    expect(apiRequest).toHaveBeenCalledTimes(1)
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2025-01-01' } })
    fireEvent.click(screen.getByText('Aplicar período'))
    expect(screen.getByRole('alert').textContent).toContain('366')
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-11-01' } })
    fireEvent.click(screen.getByText('Aplicar período'))
    await waitFor(() => expect(vi.mocked(apiRequest).mock.lastCall?.[0]).toBe('/api/dashboard?date_from=2026-11-01&date_to=2026-11-01'))
  })
  it('muestra fallo sin cifras antiguas y permite reintentar', async () => {
    render(<DashboardPage />)
    await screen.findByText('94 ventas · POS y online')
    vi.mocked(apiRequest).mockRejectedValueOnce(new Error('Sin conexión'))
    fireEvent.click(screen.getByLabelText('Actualizar indicadores'))
    await screen.findByText('Sin conexión')
    expect(screen.queryByText('94 ventas · POS y online')).toBeNull()
    fireEvent.click(screen.getByText('Reintentar'))
    await screen.findByText('94 ventas · POS y online')
  })
  it('ignora respuestas tardías de filtros anteriores', async () => {
    let finish!: (response: Response) => void
    vi.mocked(apiRequest).mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
    render(<DashboardPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Hoy' }))
    await screen.findByText('94 ventas · POS y online')
    finish({ json: async () => ({ ...dashboardFixture, sales: { ...dashboardFixture.sales, count: 999 } }) } as Response)
    await waitFor(() => expect(screen.queryByText('999 ventas · POS y online')).toBeNull())
  })
  it('presenta vacíos sin dibujar datos ficticios', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ json: async () => ({ ...dashboardFixture,
      sales: { total: '0', count: 0, average: '0', returns: '0', net: '0' },
      daily: [{ date: '2026-11-01', total: '0', count: 0 }], payments: [], by_branch: [], top_products: [],
    }) } as Response)
    render(<DashboardPage />)
    await screen.findByText('0 ventas · POS y online')
    expect(screen.queryByRole('img', { name: /Distribución/ })).toBeNull()
    expect(screen.getAllByText('No hay ventas en este período.')).toHaveLength(3)
  })
  it('restringe el dashboard a administrador y socio', () => {
    expect(canAccessAdminPage('/admin/dashboard', [], ['SOCIO'])).toBe(true)
    expect(canAccessAdminPage('/admin/dashboard', [], ['ADMINISTRADOR'])).toBe(true)
    expect(canAccessAdminPage('/admin/dashboard', ['pos.operar'], ['CAJERO'])).toBe(false)
  })
  it('calcula los atajos en fecha chilena y atraviesa meses correctamente', () => {
    expect(chileToday(new Date('2026-01-02T01:00:00Z'))).toBe('2026-01-01')
    expect(presetDates('week', '2026-03-02')).toEqual({ date_from: '2026-02-24', date_to: '2026-03-02' })
    expect(presetDates('month', '2026-03-02')).toEqual({ date_from: '2026-03-01', date_to: '2026-03-02' })
  })
})
