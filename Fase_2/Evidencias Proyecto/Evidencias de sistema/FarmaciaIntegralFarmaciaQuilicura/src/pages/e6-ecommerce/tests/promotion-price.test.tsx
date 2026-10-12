import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import PromotionPrice from '../components/PromotionPrice'
import ProductCard from '../components/ProductCard'
import CartItem from '../components/CartItem'

vi.mock('../components/AddToCartButton', () => ({ default: () => <button>Agregar al carrito</button> }))
vi.mock('../hooks/useCart', () => ({ useCart: () => ({ change: vi.fn(), remove: vi.fn() }) }))
afterEach(cleanup)
const promotion = { code: 'qa', name: 'Oferta QA', kind: 'PERCENT' as const, value: '20' }
const product = { id: 'qa', name: 'Producto QA', description: '', category: { id: 'category', name: 'Categoría' }, price: '2000', base_price: '2500', discount: '500', promotion, requires_prescription: false, online_purchase_allowed: true, image_url: null, availability: [] }

describe('Presentación de promociones online', () => {
  it('muestra precio normal tachado, final y porcentaje', () => {
    const { container } = render(<PromotionPrice price="2000" basePrice="2500" discount="500" promotion={promotion} />)
    expect(container.querySelector('del')?.textContent).toContain('2.500')
    expect(screen.getByText('20 % de descuento')).toBeTruthy()
    expect(screen.getByText(/Ahorras.*500 por unidad/)).toBeTruthy()
    expect(container.querySelector('.promotion-final')?.textContent).toContain('2.000')
  })
  it('identifica el precio fijo sin confundirlo con un importe a restar', () => {
    const { container } = render(<PromotionPrice price="100" basePrice="2500" discount="2400" promotion={{ ...promotion, kind: 'FIXED_PRICE', value: '100' }} />)
    expect(screen.getByText('Precio promocional fijo')).toBeTruthy()
    expect(container.querySelector('.promotion-final')?.textContent).toContain('100')
    expect(screen.getByText(/Ahorras.*2.400 por unidad/)).toBeTruthy()
  })
  it('sin descuento no muestra precio tachado ni etiqueta', () => {
    const { container } = render(<PromotionPrice price="2500" basePrice="2500" promotion={null} />)
    expect(container.querySelector('del')).toBeNull()
    expect(container.querySelector('.promotion-badge')).toBeNull()
  })
  it.each([false, true])('catálogo y ficha reutilizan el precio promocional: detalle %s', detail => {
    render(<MemoryRouter><ProductCard product={product} detail={detail} /></MemoryRouter>)
    expect(screen.getByText('20 % de descuento')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Producto QA' })).toBeTruthy()
  })
  it('mantiene la indicación presencial y no permite agregar productos con receta', () => {
    render(<MemoryRouter><ProductCard product={{ ...product, requires_prescription: true, online_purchase_allowed: false }} /></MemoryRouter>)
    expect(screen.getByText('Requiere receta · Compra presencial')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Agregar al carrito' })).toBeNull()
  })
  it('carrito muestra el descuento y el subtotal recibido del backend', () => {
    render(<CartItem line={{ product_id: 'qa', name: 'Producto QA', quantity: 2, unit_price: '2000', base_unit_price: '2500', unit_discount: '500', promotion, subtotal: '4000', local_available: 2, global_available: 2, requires_transfer: false, valid: true, issues: [] }} />)
    expect(screen.getByText('20 % de descuento')).toBeTruthy()
    expect(screen.getByText('4.000', { exact: false })).toBeTruthy()
  })
})
