// E2-H1: contratos del backend, con precios y codigos como texto.
import { apiRequest } from '../../services/http'

export interface Category { id: string; name: string }
export interface ProductInput {
  sku: string
  name: string
  description: string
  category_id: string
  price: string
  requires_prescription: boolean
  is_active: boolean
  published_online: boolean
  barcodes: string[]
}
export interface Product extends ProductInput { id: string }

export async function listCategories(): Promise<Category[]> {
  return (await apiRequest('/api/categories')).json()
}
export async function listProducts(): Promise<Product[]> {
  return (await apiRequest('/api/products')).json()
}
export async function createCategory(name: string): Promise<Category> {
  return (await apiRequest('/api/categories', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  }, { 422: 'Escribe un nombre de categoría de entre 1 y 150 caracteres.' })).json()
}
export async function createProduct(input: ProductInput): Promise<Product> {
  return (await apiRequest('/api/products', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  }, {
    409: 'El SKU o alguno de los códigos de barras ya está registrado. Revísalos antes de guardar.',
    422: 'Revisa los datos y la categoría seleccionada. El precio admite hasta dos decimales.',
  })).json()
}
