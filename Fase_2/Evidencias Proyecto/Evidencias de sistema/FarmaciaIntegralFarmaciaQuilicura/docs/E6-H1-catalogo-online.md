# E6-H1 — Catálogo online y disponibilidad por sucursal

La tienda pública está en `/tienda`; las fichas están en
`/tienda/productos/:productId`. No requieren una sesión interna.

## Contratos públicos de lectura

- `GET /api/ecommerce/branches`: `{branches: [{id, name, address}]}`.
- `GET /api/ecommerce/products?q=...&branch_id=...`: `{products: [...]}`.
  La búsqueda es opcional, de hasta 150 caracteres, sobre nombre y descripción.
  La sucursal opcional limita las disponibilidades, no oculta productos sin stock.
- `GET /api/ecommerce/products/{product_id}`: ficha con disponibilidad en todas
  las sucursales activas.
- `GET /api/ecommerce/products/{product_id}/image`: imagen JPEG existente.

Cada producto incluye `id`, `name`, `description`, `category: {id, name}`,
`price` como texto decimal, `requires_prescription`, `online_purchase_allowed`,
`image_url` relativa o nula y `availability: [{branch_id, branch_name, available}]`.
Solo se exponen productos activos y publicados online. Productos ocultos,
inactivos o inexistentes devuelven 404 en ficha e imagen. Una sucursal inexistente
o inactiva devuelve 404 al filtrarla; identificadores mal formados devuelven 422.

## Disponibilidad informativa

`available = stock_fisico - stock_reservado`, por producto y sucursal activa.
Sin registro de inventario se informa cero. No se añade stock en tránsito ni se
modifican inventario, reservas o movimientos. Una cantidad negativa se trata como
error de datos, no se publica ni se corrige silenciosamente.

Esta cifra no confirma unidades comprables online. La validación de lotes vigentes
y unidades vendibles se completará en E6-H4. El campo `online_purchase_allowed`
indica únicamente que el producto no está restringido por receta, independientemente
del stock. No constituye autorización de compra ni reserva.

Los productos con receta permanecen visibles, con precio e información y la leyenda
«Requiere receta · Compra presencial». No hay acciones de carrito o compra.

## Ejecución y despliegue

Se conserva PostgreSQL en Docker y FastAPI/Vite locales según README. No hay cambios
en Compose, variables de conexión, modelos ni migraciones. El cliente usa rutas
relativas `/api`; el módulo nuevo no fija host, puerto ni rutas de disco.
En un VPS el servidor web debe servir la SPA para sus rutas y dirigir `/api` a
FastAPI. Las imágenes utilizan el almacenamiento configurable ya existente.

## Pruebas

Desde backend, con la conexión existente apuntando a PostgreSQL de desarrollo:

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_e6_catalog.py -q -p no:cacheprovider
```

Se reutiliza la fixture `setup`: transacción exterior con rollback y sesiones
con savepoints. No se aplican migraciones ni se crean bases/tablas. Solo se insertan
datos temporales identificados con UUID; las imágenes se crean en el directorio
temporal de pytest, nunca en las fotos del catálogo real. Las consultas públicas
no escriben datos. El cierre de la fixture revierte los datos aunque una prueba falle.

Las pruebas cubren acceso anónimo, actividad/publicación, receta, precisión de precio,
stock informativo, ausencia de inventario, sucursales inactivas, imágenes, búsqueda,
errores de entrada y conservación de las protecciones administrativas.

## Verificación de esta implementación

- 10 pruebas específicas E6-H1 aprobadas con PostgreSQL y rollback.
- Verificación ampliada de E6, autenticación, imágenes e integración E2/E3:
  67 aprobadas y un fallo en `test_branch_with_inventory_cannot_be_deleted`.
  Se reprodujo ese mismo fallo sin registrar el módulo E6, en memoria y sin
  editar archivos. Queda pendiente fuera del alcance de esta historia.
- Build frontend aprobado. ESLint de E6 y router aprobado.
- ESLint global: cuatro errores preexistentes de `set-state-in-effect` en
  ExpirationAlertsPanel, InventoryMovementHistory y LotPanel.
- Ruff de E6, main y sus pruebas aprobado. Ruff global: tres errores
  preexistentes en inventory/repository.py e inventory/schemas.py.
- Catálogo y ficha comprobados en navegador contra los servicios locales reales.
- Aviso de deprecación de httpx en Starlette TestClient; no se cambiaron dependencias.
