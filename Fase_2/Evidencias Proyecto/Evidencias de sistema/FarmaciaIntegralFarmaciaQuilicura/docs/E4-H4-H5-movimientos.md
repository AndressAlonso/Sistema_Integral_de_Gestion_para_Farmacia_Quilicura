# E4-H4 / E4-H5 — Recepción y ajustes desde Transferencias

Implementación del 30 de septiembre de 2026 en `Proyecto`. La propuesta de las dos
tablas fue aprobada explícitamente en la conversación. Sustituye el acceso anterior
de recepción en Inventario y la situación «en espera» indicada en las notas previas.

## Uso

1. Iniciar sesión y abrir **Transferencias → Registrar movimiento**.
2. Elegir **Recepción de mercadería** o **Ajuste de inventario**.
3. Seleccionar sucursal. En recepción, agregar productos del catálogo; en ajustes, lotes existentes.
4. Completar respaldo, revisar las cantidades y marcar la confirmación.
5. Pulsar **Guardar movimiento** una sola vez para guardar todas las filas.

Recepción pide proveedor, tipo/número/fecha de documento y unidades recibidas.
Cada fila pide lote del envase y vencimiento futuro. Se sugieren lotes existentes
del producto en la sucursal y se completa su vencimiento al seleccionarlos.
Al confirmar, el backend crea el lote si falta o suma al existente si coincide su
vencimiento. Con 20 unidades y una recepción de 5, quedan 25. No requiere stock previo.

Ajuste pide motivo y cantidad final por lote. Con 20 unidades y cantidad final 18,
se registra una diferencia de −2. El formulario muestra la cantidad actual y la
diferencia; las filas sin cambios se omiten. Se permiten cantidades finales cero.

E4-H5 exige rol `ADMINISTRADOR` o `ENCARGADO_INVENTARIO` además del permiso
`inventario.ajustar`. FastAPI rechaza otros roles incluso si tienen ese permiso.
Administrador conserva alcance global; Encargado solo su sucursal. Las opciones
de la API y el botón del frontend respetan esa combinación. Recepción mantiene
su autorización independiente. No requiere cambios de esquema ni migraciones.

Se pueden agregar hasta cien filas de distintos productos o distintos lotes del
mismo producto, sin repetir un lote. Una operación corresponde a una sucursal.
El vencimiento no se modifica. Un lote vencido puede corregirse por conteo, pero
no aparece como opción para recibir nuevas unidades y no recupera vigencia al ajustarlo.

Los cambios permanecen en el formulario hasta guardar. Si falta un dato o falla
una fila, no se guarda ninguna modificación de la operación.

## Alcance y requisito de datos

Crear un producto solo registra su ficha de catálogo. No crea inventario en cero
en las sucursales. La recepción crea el inventario de la sucursal elegida junto
con sus lotes y existencias dentro de la misma transacción.
La recepción consulta todos los productos activos mediante
`GET /api/goods-receipts/options`, incluso sin inventario ni lotes.
No es obligatorio registrar antes un lote en cero en Inventario.
La misma recepción permite varias filas del mismo producto con lotes diferentes;
repetir producto y número de lote exige reunir las unidades en una sola fila.

No se modificó el esquema. Se retiró el script de inicialización en cero.
Los inventarios que posteriormente se agotan conservan sus registros e historial.
`GET /api/stock-operations/options` agrega `products` (id, name, sku, branch_id,
quantity) sin quitar campos anteriores. `POST /api/inventory/lots` ahora acepta
cantidad cero; sigue rechazando negativos y cantidades superiores al stock sin lote.

La API anterior de recepción conserva su capacidad y contrato; el nuevo formulario
la consume con datos de lotes nuevos o existentes. Las transferencias entre sucursales
conservan su pantalla y flujo E4-H1/H2/H3.

## Persistencia y seguridad del ajuste

Migración nueva **0010_ajustes_inventario**, posterior a 0009. No se modificaron
migraciones anteriores ni se recreó PostgreSQL.

- `ajuste_inventario`: UUID de solicitud, hash de datos, sucursal, usuario, motivo y fecha.
- `ajuste_inventario_detalle`: UUID, ajuste, lote, cantidad anterior y nueva.
- Se reutiliza `movimiento_inventario` con tipo AJUSTE y referencia a la cabecera.

Las claves foráneas utilizan RESTRICT. Cada lote aparece una sola vez por ajuste.
Las cantidades tienen restricciones de no negatividad; el motivo no puede estar vacío.
Se conserva producto/sucursal desde la relación lote → inventario existente.

El servicio crea todo dentro de una transacción PostgreSQL. Bloquea sucursal, producto,
inventario y lote en un orden compatible con transferencias. Antes de escribir:

- Comprueba permisos, usuario activo y sucursal autorizada.
- Verifica que los lotes pertenezcan a esa sucursal y estén activos.
- Compara la cantidad actual con `expected_quantity`; si otro usuario la cambió,
  devuelve 409 para que se actualice el formulario.
- Impide disminuir el lote por debajo de su reserva de transferencia.
- Impide que el stock físico total quede por debajo del reservado o sea negativo.
- Controla el límite de enteros de PostgreSQL.

Cada detalle registra antes/después por lote; el kardex registra antes/después
del stock agregado, diferencia, responsable, motivo y fecha. Si hay aumentos y
disminuciones del mismo producto, se registran los aumentos primero para conservar
la consistencia de las reservas también en los saldos intermedios.

El UUID de solicitud y su hash permiten reconocer reintentos: mismos datos y usuario
devuelven el resultado confirmado (200) sin repetir movimientos. Otro contenido con
el mismo UUID da conflicto. Un bloqueo advisory serializa intentos con el mismo UUID.

El navegador conserva una solicitud pendiente en sessionStorage por usuario. Tras
un error de conexión se pueden cerrar/reabrir el modal o recargar esa pestaña y
reintentar con los mismos datos. Cerrar la pestaña elimina ese almacenamiento; antes
de repetir una operación nueva, revisar los movimientos. No se almacenan credenciales.

## Permisos

- Recepción: `inventario.registrar_entrada`, ya existente.
- Ajustes: `inventario.ajustar`, nuevo.
- El acceso a la pantalla Transferencias sigue requiriendo `transferencias.consultar`.
- Administrador puede operar en cualquier sucursal activa.
- Los demás usuarios autorizados operan únicamente en su sucursal asignada.

El seed de ajustes agrega el nuevo permiso a Administrador y Encargado de inventario
solo en su primera instalación. No restablece personalizaciones al volver a ejecutarse.
Un rol personalizado con el permiso no habilita ajustes por sí solo: el usuario
también debe tener Administrador o Encargado de inventario.

## Contratos API

Todos requieren sesión existente. Los POST validan el origen HTTP. Fechas ISO 8601;
UUID como strings. No hay cambios al contrato de login ni al de transferencias.

### GET /api/stock-operations/options

Permiso: recepción o ajustes. Respuesta 200:

```json
{
  "branches": [{ "id": "UUID", "name": "Sucursal" }],
  "lots": [{
    "id": "UUID", "product_id": "UUID", "product_name": "Producto",
    "sku": "SKU", "branch_id": "UUID", "number": "L001",
    "expiration_date": "2027-05-31", "quantity": 20
  }],
  "can_receive": true,
  "can_adjust": true
}
```

### POST /api/inventory-adjustments

Permiso: `inventario.ajustar`. Entrada:

```json
{
  "request_id": "UUID por operación",
  "branch_id": "UUID",
  "reason": "Diferencia detectada en conteo físico",
  "items": [{ "lot_id": "UUID", "expected_quantity": 20, "new_quantity": 18 }]
}
```

Respuesta 201 (200 en reintento confirmado): id, branch_id, user_id, reason,
created_at, items. Cada ítem incluye lot_id, lot_number, product_id, product_name,
previous_quantity, new_quantity y difference. No devuelve el hash interno.

### GET /api/inventory-adjustments/{id}

Permiso: `inventario.ajustar`, con alcance por sucursal. Devuelve el ajuste confirmado
en el formato anterior. También está documentado en OpenAPI `/docs`.

### POST /api/goods-receipts

Contrato anterior conservado: request_id, branch_id, supplier, document_type,
document_number, document_date e items(product_id,lot_number,expiration_date,quantity).
La cantidad significa unidades recibidas, no cantidad final. Responde 201/200.

Errores: 401 sin sesión; 403 sin permiso/sucursal/origen; 404 ajuste inexistente;
409 datos cambiados, reserva afectada, registro inactivo o ID incompatible;
422 datos inválidos; 500 mensaje genérico sin SQL, hashes ni stack traces.

## Archivos

Nuevos:

- `backend/app/inventory_adjustments/__init__.py`: módulo.
- `schemas.py`: validación y respuestas tipadas.
- `repository.py`: consultas, bloqueos, opciones y serialización.
- `service.py`: reglas y transacción del ajuste.
- `routes.py`: tres endpoints nuevos.
- `seed.py`: permiso reproducible sin restablecer roles.
- `backend/migrations/versions/0010_ajustes_inventario.py`: esquema aprobado.
- `backend/tests/test_inventory_adjustments.py`: pruebas funcionales y concurrentes.
- `src/pages/e4-transfers/StockOperationDialog.tsx`: modal común al 98%.
- `src/pages/e4-transfers/stock-operations.api.ts`: cliente de opciones/ajustes.
- `src/pages/e4-transfers/stock-operations.css`: estilos específicos.
- Esta guía.

Modificados:

- `backend/app/models.py`: dos modelos del ajuste.
- `backend/app/main.py`: repositorio, rutas y errores de validación.
- `backend/app/role_catalog.py`: permiso y roles iniciales.
- `src/pages/e4-transfers/TransfersPage.tsx`: botón, modal y confirmación.
- `src/pages/e3-inventory/InventoryPage.tsx`: retiro del acceso anterior de recepción.
- `src/pages/e3-inventory/LotPanel.tsx` y `backend/app/inventory/routes.py`:
  mensajes dirigidos al nuevo acceso.

`receipts.api.ts` se trasladó de e3-inventory a e4-transfers. Se retiraron el antiguo
`ReceiptDialog.tsx` y `receipts.css`, reemplazados por el formulario común. No se
duplicó el servicio de recepción ni se retiraron sus tablas o migraciones.

## Pruebas y ejecución

Los 21 casos nuevos cubren ajuste masivo positivo/negativo, antes/después y kardex,
reintentos, conflicto de ID, datos inválidos, rollback por una fila incorrecta,
cantidades desactualizadas, reservas agregadas y por lote, permisos, origen HTTP,
sesión, sucursal, recepción sobre lotes existentes, cero, expiración, seed y dos
operaciones simultáneas en conexiones independientes.

Los tests normales revierten datos mediante rollback. Concurrencia confirma fixtures
con UUID exclusivos y elimina solo esos fixtures en `finally`. Solo usar PostgreSQL
local de desarrollo, nunca producción.

Desde esta carpeta del proyecto, en PowerShell:

```powershell
docker compose up -d db
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.inventory_adjustments.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

En otra consola desde la carpeta del frontend:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --strictPort
```

Comprobaciones:

```powershell
cd backend
$env:SIGFQ_TEST_ROLLBACK = '1'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app/inventory_adjustments tests/test_inventory_adjustments.py
cd ..
npm.cmd run build
npm.cmd run lint
```

Los compañeros deben aplicar 0010, ejecutar el seed y reiniciar FastAPI. No hay
dependencias nuevas ni variables nuevas. Refrescar la sesión para cargar el permiso.
Los cambios compartidos se limitan a los archivos enumerados. No se hizo commit/push.

Respaldo PostgreSQL previo a 0010: `N:\TempD\sigfq-pre-ajustes-20260930-134316.dump`.
Conservarlo fuera de Git; contiene datos locales.

## Límites de verificación

Resultado final: **263 pruebas aprobadas**, incluidas las 21 nuevas. Dos avisos de
deprecación de las dependencias de testing. HTTP local: login/opciones/transferencias
y frontend 200; ajuste vacío 422; logout 204; opciones sin sesión 401. El usuario
de desarrollo conserva sus credenciales y recibió el permiso de ajustes por seed.

TypeScript/build y lint del código nuevo pasan. El lint general conserva los cuatro
hallazgos anteriores de React en Inventario y los tres de Ruff en ese módulo. No se
modificaron para esta tarea. No hay navegador conectado para revisión visual automática;
la integración se verifica mediante API, pruebas PostgreSQL y compilación.
