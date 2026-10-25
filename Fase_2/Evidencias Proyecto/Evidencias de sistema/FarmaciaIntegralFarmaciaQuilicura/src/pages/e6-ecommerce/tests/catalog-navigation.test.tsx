import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import OnlineCatalogPage from '../pages/OnlineCatalogPage'
import { listBranches, listProducts } from '../services/catalog.api'

vi.mock('../components/PublicHeader', () => ({ default: () => null }))
vi.mock('../services/catalog.api', () => ({ listBranches: vi.fn(), listProducts: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('busca, filtra por sucursal y permite recuperar el catálogo completo sin resultados', async () => {
  vi.mocked(listBranches).mockResolvedValue([{ id: 'centro', name: 'Centro', address: 'Dirección' }])
  vi.mocked(listProducts).mockResolvedValue([])
  render(<OnlineCatalogPage />)
  await screen.findByText('0 productos encontrados.')
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'Paracetamol' } })
  fireEvent.submit(screen.getByRole('search'))
  await waitFor(() => expect(listProducts).toHaveBeenLastCalledWith('Paracetamol', ''))
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'centro' } })
  await waitFor(() => expect(listProducts).toHaveBeenLastCalledWith('Paracetamol', 'centro'))
  fireEvent.click(await screen.findByRole('button', { name: 'Ver todos los productos' }))
  await waitFor(() => expect(listProducts).toHaveBeenLastCalledWith('', ''))
  expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('')
  expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('')
})
