# E4-H4 — Registrar entrada de mercadería desde Inventario

> Nota histórica: el acceso desde Inventario fue reemplazado por el formulario común
> en Transferencias. Consultar [guía vigente E4-H4/H5](E4-H4-H5-movimientos.md).
> Esta nota conserva el contexto del respaldo y de la implementación inicial.

## Punto de restauración solicitado

Antes de modificar código o esquema se creó:

- Etiqueta Git local: `restore/pre-e4-h4-20260928`, commit `aaf3de7`.
- Respaldo PostgreSQL completo: `N:\TempD\sigfq-pre-e4-h4-20260928-180831.dump`.
- Copia en el contenedor: `/tmp/sigfq-pre-e4-h4.dump`.
- Parche del cambio local previo, ajeno a esta tarea:
  `N:\TempD\sigfq-pre-e4-h4-cambio-local-previo.patch`.

El respaldo fue validado con `pg_restore --list`. Contiene datos privados: no
subirlo a Git. Conservar una copia fuera del directorio temporal si se requiere
restauración a largo plazo. La etiqueta solo protege código versionado; no protege
PostgreSQL, `.env` ni imágenes locales. Estos dos últimos no fueron modificados.

Para inspeccionar el código anterior sin perder avances:

```powershell
git show restore/pre-e4-h4-20260928
```

Una restauración completa debe coordinar código y base, detener FastAPI, respaldar
primero cualquier dato posterior y restaurar el dump en una instancia aislada para
verificarlo. No ejecutar `reset --hard`, `downgrade` o `pg_restore --clean` sobre la
base actual sin aprobar la pérdida de cambios posteriores. No se ejecutó restauración.

## Qué se implementó

Botón **Registrar entrada de mercadería** dentro de Inventario. Abre el modal
compartido al 98% y permite ingresar una guía o factura con varios productos/lotes.
El proveedor se conserva como texto de respaldo; no se agrega un CRUD de proveedores.

Un producto nuevo puede seleccionarse desde el catálogo sin tener inventario previo.
El backend crea la relación producto/sucursal si falta, suma stock físico, crea o
incrementa el lote, registra el documento y un movimiento por detalle. Las reservas
existentes permanecen iguales. Un mismo lote existente debe estar activo y tener
el mismo vencimiento; de lo contrario se rechaza toda la entrada.

## Archivos creados

| Ruta | Propósito |
|---|---|
| `backend/app/goods_receipts/__init__.py` | Módulo del backend único. |
| `backend/app/goods_receipts/schemas.py` | Contratos de solicitud y respuesta. |
| `backend/app/goods_receipts/repository.py` | Consultas, bloqueos y creación segura de relación producto/sucursal. |
| `backend/app/goods_receipts/service.py` | Permisos, alcance, validaciones y transacción completa. |
| `backend/app/goods_receipts/routes.py` | Endpoints y errores HTTP controlados. |
| `backend/app/goods_receipts/seed.py` | Instala el permiso nuevo sin restablecer roles personalizados. |
| `backend/migrations/versions/0008_recepcion_mercaderia.py` | Dos tablas aprobadas de respaldo de recepción. |
| `backend/tests/test_goods_receipts.py` | Pruebas E4-H4 y concurrencia real. |
| `src/pages/e3-inventory/ReceiptDialog.tsx` | Formulario y recuperación de solicitudes pendientes. |
| `src/pages/e3-inventory/receipts.api.ts` | Cliente HTTP tipado de recepción. |
| `src/pages/e3-inventory/receipts.css` | Distribución adaptable del formulario. |
| `docs/E4-H4-recepcion-mercaderia.md` | Informe y punto de restauración. |

## Archivos modificados

- `backend/app/models.py`: modelos de recepción y detalle.
- `backend/app/main.py`: conecta repositorio, router y mensaje de validación.
- `backend/app/role_catalog.py`: declara el permiso nuevo para los roles iniciales.
- `backend/app/inventory/repository.py`: el formulario heredado de lotes bloquea el
  inventario y valida que la suma de cantidades de lotes no exceda el stock físico.
- `backend/app/inventory/routes.py`: responde 409 ante exceso de asignación a lotes.
- `src/pages/e3-inventory/InventoryPage.tsx`: botón según permiso y actualización
  de inventario/paneles después de recibir mercadería.
- `src/pages/e3-inventory/LotPanel.tsx`: explica que distribuye stock existente,
  sin aumentar existencias; dirige las compras nuevas a Registrar entrada.

## Base de datos

Migración aplicada: `0008_recepcion_mercaderia`, posterior a `0007` sin reescribirla.

- `recepcion_mercaderia`: UUID reutilizado como identificador idempotente,
  hash interno de solicitud, sucursal, responsable, proveedor, tipo/número/fecha del
  documento y timestamp UTC del registro.
- `recepcion_mercaderia_detalle`: UUID, recepción, lote y cantidad positiva.
- FK `RESTRICT` para conservar referencias; un lote no se repite dentro de una recepción.
- Tablas reutilizadas: `producto`, `sucursal`, `usuario_interno`,
  `inventario_sucursal`, `lote_inventario`, `movimiento_inventario`, `permiso`,
  `rol_permiso`. No se agregaron columnas a ellas.
- Movimientos: tipo `RECEPCION`, referencia `RECEPCION_MERCADERIA` y UUID de cabecera.
  No se modifica la estructura existente de movimientos.

## Flujo real

Inventario → ReceiptDialog → POST /api/goods-receipts → autenticación de sesión
→ ReceiptService → transacción SQLAlchemy → bloqueo de solicitud → validación
de sucursal/productos → crear o bloquear inventario → crear/incrementar lote
→ sumar físico → guardar detalle y movimiento → commit → refrescar Inventario.

El identificador se guarda en `sessionStorage` por usuario antes de enviar. Ante
timeout/error del servidor se conserva el contenido y se reintenta sin duplicar.
También puede recuperarse al reabrir el formulario o recargar la misma pestaña.
Cerrar la pestaña puede perder ese borrador; comprobar el Historial antes de registrar
otra entrada si quedó una confirmación incierta. Una entrada nueva con otro UUID
se considera otra operación, aunque use el mismo documento (no se impuso una nueva
regla de unicidad de documentos que impida recepciones por partes).

## Contratos API

Autenticación en todos: cookie de sesión existente, usuario activo y permiso
`inventario.registrar_entrada`. El Administrador con permiso puede elegir cualquier
sucursal activa; otros usuarios con permiso operan únicamente en su sucursal.

### GET /api/goods-receipts/options

Sin body. Respuesta 200: `{products: [{id, name, sku}], branches: [{id, name}]}`.
Solo productos activos y sucursales activas dentro del alcance. No concede acceso
a gestionar el catálogo ni a administrar sucursales. Errores 401/403/500.

### POST /api/goods-receipts

```json
{
  "request_id": "UUID generado una sola vez para esta solicitud",
  "branch_id": "UUID de sucursal",
  "supplier": "Proveedor ficticio",
  "document_type": "FACTURA",
  "document_number": "F-123",
  "document_date": "2026-09-28",
  "items": [{
    "product_id": "UUID de producto",
    "lot_number": "PAR-001",
    "expiration_date": "2027-09-30",
    "quantity": 50
  }]
}
```

Tipo documental: `GUIA` o `FACTURA`. Cantidades enteras positivas, hasta un millón
por detalle y hasta 100 detalles. El documento no puede tener fecha futura y cada
vencimiento debe ser posterior al día UTC actual. No repetir producto/lote en el body.

Respuesta 201 al crear; 200 al repetir la misma solicitud ya confirmada:
`{id, branch_id, user_id, supplier, document_type, document_number, document_date,
created_at, items}`. No expone `solicitud_hash`.

Errores: 401 sin sesión, 403 sin permiso/sucursal/origen permitido, 409 referencia
inactiva o conflicto de lote/idempotencia/capacidad, 422 datos inválidos y 500 genérico.
El body inválido no se persiste. Un error en cualquier detalle revierte toda la entrada.

### GET /api/goods-receipts/{id}

Sin body; devuelve la misma representación de la recepción, con control de permiso
y alcance de sucursal. Errores 401/403/404/422/500. No se agrega edición/eliminación.

### POST /api/inventory/lots — compatibilidad

Mantiene su request/response. Su función es distribuir existencias sin lote, no
ingresar mercadería. Ahora retorna 409 si la cantidad excede el stock sin asignar.
Este ajuste evita duplicar las cantidades que ya registró una recepción.

## Seguridad y concurrencia

Se reutilizan autenticación, cookie, expiración y protección de origen de E1.
Permisos y sucursal se verifican en backend; ocultar el botón es solo interfaz.
Stock, lote, documento y movimiento se confirman juntos. La creación del inventario
usa la restricción única producto/sucursal; bloqueos por registro serializan entradas
concurrentes. El UUID de solicitud se bloquea transaccionalmente y se compara con el
hash del contenido y responsable; repetir no aumenta existencias dos veces.

El seed concede únicamente el permiso nuevo a Administrador y Encargado de
inventario en su primera instalación; repetirlo conserva retiradas posteriores y
no restablece los otros permisos/nombres personalizados.

## Pruebas ejecutadas

**212 pruebas aprobadas**, incluidas 19 nuevas de E4-H4:

- Primer ingreso de producto sin inventario: documento, stock, lote y movimiento.
- Reposición del mismo lote y conservación de reservas.
- Reintento idéntico y rechazo del mismo UUID con contenido distinto.
- Vencimiento incompatible en una entrada múltiple: rollback completo.
- Cantidades cero, negativas, fraccionarias; lote vacío y vencido.
- Documento/proveedor obligatorios, fecha futura y lista vacía.
- Sesión, permiso, origen HTTP y alcance de sucursal.
- Producto/sucursal inactivos.
- Formulario heredado de lotes no duplica existencias recibidas.
- Dos entradas simultáneas suman correctamente.
- Dos solicitudes simultáneas con el mismo UUID generan una sola entrada.

La mayoría usa rollback. Los dos casos concurrentes usan conexiones independientes,
crean fixtures confirmados con UUID exclusivos y los eliminan en `finally`, sin tocar
datos de usuarios reales. No se cargó stock de demostración al producto del usuario.

TypeScript/Vite: correcto. Ruff del módulo nuevo y ESLint de los componentes nuevos:
correctos. Lint global conserva 3 errores Python y 4 React heredados de E3 (fechas,
imports y estados dentro de efectos), ya detectados antes de este cambio.

Prueba HTTP real: login 200, permiso presente, opciones 200 con el producto existente,
entrada vacía 422, frontend 200. No se ejecutó una recepción ficticia sobre ese producto.
No fue posible revisión visual: la herramienta no tiene navegador conectado.

## Ejecutar en PowerShell

Desde la carpeta del proyecto con package.json y backend, Docker encendido:

```powershell
docker compose up -d db
Set-Location backend
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.goods_receipts.seed
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Otra consola desde la carpeta del proyecto:

```powershell
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Pruebas, desde backend:

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider
```

## Probar manualmente

1. Abrir http://127.0.0.1:5173 y recargar para recuperar los permisos de sesión.
2. Ingresar a Inventario y pulsar Registrar entrada de mercadería.
3. Seleccionar el producto del catálogo y la sucursal.
4. Completar proveedor, guía/factura, número y fecha.
5. Introducir cantidad, lote y vencimiento futuro. Agregar filas si hay más productos/lotes.
6. Guardar y comprobar stock en Disponibilidad, lote en Lotes y entrada en Historial.
7. Una segunda recepción del mismo lote y vencimiento suma sus unidades; no crea otro lote.

La cantidad usa la unidad que representa la ficha del producto. No se agregó una
conversión entre cajas y pastillas ni otro modelo de unidades.

## Impacto para el equipo y pendientes

Actualizar rama, ejecutar 0008 y el seed de permisos, reiniciar backend y recargar
frontend. No hay dependencias ni variables de entorno nuevas. Archivos compartidos
modificados: models.py, main.py, role_catalog.py y la integración de Inventario.

No se implementaron transferencias E4-H1/H2/H3 ni ajustes E4-H5.
La discrepancia de rangos de vencimiento de E3 y el índice de 0007 ausente en la
declaración del modelo siguen pendientes; no se alteraron silenciosamente.
El diagrama v2 vigente sigue pendiente de contraste y la revisión por otro integrante
no se ha realizado. Esta implementación no declara cerrada toda la épica E4.
No se realizó push.
