import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import OnlineCatalogPage from '../pages/OnlineCatalogPage'
import { listBranches, listProducts } from '../services/catalog.api'


const { selectedBranch } = vi.hoisted(() => ({ selectedBranch: vi.fn() }))
vi.mock('../hooks/useCart', async () => {
  const { useState } = await import('react')
  return { useCart: function useCart() {
    const [branch, setBranch] = useState<string | null>(null)
    return { draft: { pickup_branch_id: branch }, selectBranch: (id: string) => { selectedBranch(id); setBranch(id || null) } }
  } }
})

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
  fireEvent.click(screen.getByRole('button', { name: /Ver disponibilidad en/ }))
  fireEvent.click(screen.getByRole('button', { name: /Centro/ }))
  await waitFor(() => expect(listProducts).toHaveBeenLastCalledWith('Paracetamol', 'centro'))
  expect(selectedBranch).toHaveBeenLastCalledWith('centro')
  fireEvent.click(await screen.findByRole('button', { name: 'Ver todos los productos' }))
  await waitFor(() => expect(listProducts).toHaveBeenLastCalledWith('', ''))
  expect(selectedBranch).toHaveBeenLastCalledWith('')
  expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('')
  expect(screen.getByRole('button', { name: /Ver disponibilidad en Todas las sucursales/ })).toBeTruthy()
})

it('combina categoría y ofertas usando el precio promocional real y permite limpiar ambos', async () => {
  vi.mocked(listBranches).mockResolvedValue([])
  const common = { description: '', requires_prescription: true, online_purchase_allowed: false, image_url: null, availability: [] }
  vi.mocked(listProducts).mockResolvedValue([
    { ...common, id: 'a', name: 'Producto oferta', category: { id: 'vit', name: 'Vitaminas' }, price: '800', base_price: '1000', promotion: { code: 'PROMO', name: 'Oferta vigente', kind: 'PERCENT', value: '20' } },
    { ...common, id: 'b', name: 'Producto normal', category: { id: 'vit', name: 'Vitaminas' }, price: '1000' },
    { ...common, id: 'c', name: 'Producto cuidado', category: { id: 'care', name: 'Cuidado personal' }, price: '500' },
  ])
  render(<MemoryRouter><OnlineCatalogPage /></MemoryRouter>)
  await screen.findByText('3 productos encontrados.')
  fireEvent.click(screen.getByRole('button', { name: /Categorías/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Vitaminas' }))
  expect(screen.getByText('2 productos encontrados.')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: /Ofertas/ }))
  expect(screen.getByText('1 producto encontrado.')).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Producto oferta' })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: 'Producto normal' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: /Limpiar filtros/ }))
  await screen.findByText('3 productos encontrados.')
})

