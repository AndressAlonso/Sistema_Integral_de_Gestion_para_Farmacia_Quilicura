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
export interface Product extends ProductInput { id: string; image_url: string | null }

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

export async function updateProduct(id: string, input: ProductInput): Promise<Product> {
  // El contrato de edicion excluye el precio; el backend tambien lo rechaza.
  const editable = {
    sku: input.sku, name: input.name, description: input.description,
    category_id: input.category_id, requires_prescription: input.requires_prescription,
    is_active: input.is_active, published_online: input.published_online, barcodes: input.barcodes,
  }
  return (await apiRequest(`/api/products/${id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editable),
  }, {
    409: 'El SKU o un código de barras está en uso. No se guardaron los cambios de la ficha.',
    422: 'Revisa los datos del producto y su categoría.',
  })).json()
}
export async function uploadProductImage(id: string, file: File): Promise<Product> {
  return (await apiRequest(`/api/products/${id}/image`, {
    method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file,
  }, {
    413: 'La imagen supera los límites: 5 MB y 20 megapíxeles.',
    415: 'El archivo no es una imagen válida. Usa JPG, PNG o WebP sin animación.',
  })).json()
}
export async function removeProductImage(id: string): Promise<Product> {
  return (await apiRequest(`/api/products/${id}/image/remove`, { method: 'POST' })).json()
}
