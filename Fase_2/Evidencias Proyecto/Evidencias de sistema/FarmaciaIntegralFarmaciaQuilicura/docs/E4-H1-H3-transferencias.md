# E4-H1, E4-H2 y E4-H3 — Transferencias manuales

> Actualización: recepción y ajustes se retomaron por aprobación del usuario.
> El botón nuevo de Transferencias está documentado en
> [E4-H4-H5-movimientos.md](E4-H4-H5-movimientos.md). Las menciones de E4-H4
> «en espera» más abajo describen el estado al entregar inicialmente E4-H1/H2/H3.

Implementación inicial en la rama `Proyecto`, sobre el modelo PostgreSQL existente.
Alcance: solicitud, reserva por lote, aprobación/rechazo, despacho y recepción completa.
E4-H4 (recepción de mercadería de proveedores) permanece pendiente de discusión del equipo;
sus cambios locales anteriores se conservaron. No incluye ajustes E4-H5 ni transferencias
automáticas por pedidos E7-H3.

## Flujo y stock

| Operación | Estado resultante | Físico origen | Reserva origen | Disponible destino |
|---|---|---|---|---|
| Solicitar 8 unidades | SOLICITADA | Sin cambios | +8 | Sin cambios |
| Aprobar | AUTORIZADA | Sin cambios | Se conserva | Sin cambios |
| Rechazar antes de despacho | RECHAZADA | Sin cambios | −8 | Sin cambios |
| Confirmar despacho | EN_TRANSITO | −8 | −8 | Sin cambios |
| Confirmar recepción total | RECIBIDA | Sin cambios | Sin cambios | +8 |

Cada operación se realiza en una transacción. Si falla un producto o lote, se revierte
la operación completa. No se hace una entrada al destino al aprobar ni al despachar.
El stock en tránsito corresponde a los detalles de transferencias `EN_TRANSITO`, y no
se incorpora al inventario destino hasta recibir. No se necesita otra columna de stock.

Se reservan lotes por FEFO: vencimiento más cercano, desempate por UUID. Solo se utilizan
lotes activos cuya fecha sea posterior a la fecha UTC actual. Se comprueba disponibilidad
agregada y por lote; otras reservas existentes también reducen el stock disponible.
Al despachar se vuelve a verificar vigencia, actividad y cantidad del lote reservado.
Si venció, se impide el despacho y se puede rechazar la transferencia para liberar reservas.

Al recibir se conserva número de lote y vencimiento; se crea el inventario destino si
no existe. Un lote con el mismo número se acumula únicamente si está activo y tiene el
mismo vencimiento. Un conflicto revierte la recepción completa y mantiene el tránsito.
Si el lote vence durante el transporte, se registra igualmente la llegada física con
su vencimiento original; no se convierte en un lote vigente.

La recepción es total: se escriben las cantidades realmente contadas. Diferencias,
productos faltantes, sobrantes o repetidos no afectan inventario. No se implementa un
flujo de recepción parcial o resolución de diferencias en esta versión.

## Acceso y sucursales

Todos los endpoints requieren la sesión existente de E1 y `transferencias.consultar`.

| Acción | Permiso adicional | Alcance |
|---|---|---|
| Consultar | Ninguno | Administrador: todas; demás usuarios: origen o destino propio |
| Solicitar | transferencias.solicitar | Administrador: cualquier origen; demás: origen asignado |
| Aprobar/rechazar | transferencias.autorizar | Además exige rol ADMINISTRADOR |
| Despachar | transferencias.despachar | Administrador: cualquier origen; demás: origen asignado |
| Recibir | transferencias.recibir | Administrador: cualquier destino; demás: destino asignado |

El administrador gestiona globalmente sin cambiar su sucursal, conservando los permisos
requeridos, validaciones de estado/stock y registro del responsable. Los demás usuarios
confirman despacho/recepción únicamente en su sucursal asignada. Ocultar acciones en
React es solo presentación: FastAPI repite todas las comprobaciones.

El seed entrega los cinco permisos nuevos a Administrador; Encargado de inventario
recibe consultar, solicitar, despachar y recibir. Reejecutarlo no repone permisos que
el equipo haya retirado después ni cambia nombres personalizados de roles existentes.
Para un rol personalizado se asignan los permisos desde el gestor existente.

Sucursales con transferencias pendientes no pueden desactivarse. Las que tienen
historial de transferencias no muestran eliminación, aunque no tengan inventario.
Los responsables, productos y lotes referenciados quedan protegidos por claves foráneas.

## Archivos creados

| Ruta | Propósito |
|---|---|
| backend/app/transfers/__init__.py | Módulo del monolito |
| backend/app/transfers/schemas.py | Entradas y respuestas tipadas, publicadas en OpenAPI |
| backend/app/transfers/routes.py | Rutas, autenticación, origen y errores HTTP |
| backend/app/transfers/service.py | Reglas, permisos, FEFO y transiciones atómicas |
| backend/app/transfers/repository.py | Consultas, bloqueos y movimientos de inventario |
| backend/app/transfers/seed.py | Instalación reproducible de nuevos permisos |
| backend/migrations/versions/0009_transferencias.py | Tres tablas aprobadas para E4-H1/H2/H3 |
| backend/tests/test_transfers.py | Casos funcionales, integridad y concurrencia |
| src/pages/e4-transfers/transfers.api.ts | Contratos TypeScript y cliente HTTP |
| src/pages/e4-transfers/TransfersPage.tsx | Listado, resumen, filtros y apertura de formularios |
| src/pages/e4-transfers/TransferForm.tsx | Solicitud y recuperación de reintentos |
| src/pages/e4-transfers/TransferDetail.tsx | Detalle, trazabilidad y confirmación de acciones |
| src/pages/e4-transfers/transfers.css | Estilos del módulo, reutilizando estilos existentes |
| docs/E4-H1-H3-transferencias.md | Esta guía |

## Archivos compartidos modificados para esta entrega

| Ruta | Cambio necesario |
|---|---|
| backend/app/models.py | Transferencia, TransferenciaDetalle y TransferenciaLote |
| backend/app/main.py | Registro del repositorio/router y mensaje seguro de validación |
| backend/app/role_catalog.py | Cinco permisos E4 y valores iniciales de los roles |
| backend/app/users/roles_repository.py | Grupo Transferencias visible en el gestor de permisos |
| backend/app/branches/repository.py | Bloqueo de desactivación pendiente y eliminación con historial |
| backend/app/branches/routes.py | Respuesta 409 para transferencia pendiente |
| src/routes/AppRouter.tsx | Pantalla en /admin/transfers |
| src/layouts/adminNavigation.ts | Visibilidad por permiso real, reemplazando el placeholder |

No se reemplazaron contratos de login, usuarios, catálogo ni inventario. Los archivos
anteriores de E4-H4 también aparecen en `git status`, pero corresponden al trabajo
previo en espera. Existe además un cambio anterior en una copia hermana de branches/routes.py;
no forma parte de esta entrega ni fue modificado por ella.

## Base de datos y concurrencia

Migración `0009_transferencias`, hija de `0008_recepcion_mercaderia`:

- `transferencia`: origen, destino, estado, responsables/fechas y hash de solicitud.
- `transferencia_detalle`: producto y cantidad; un producto por transferencia.
- `transferencia_lote`: asignación de cada lote de origen y vínculo con lote destino.

UUID, fechas con zona horaria y referencias `RESTRICT`. Checks para sucursales distintas,
estados admitidos y cantidades positivas; UNIQUE para producto por transferencia y lote
por detalle. Se reutilizan `inventario_sucursal`, `lote_inventario` y `movimiento_inventario`.
No se modificaron migraciones anteriores ni se recreó la base.

La solicitud usa `request_id` UUID como clave idempotente, más un hash de los datos.
Un bloqueo transaccional advisory serializa solicitudes repetidas. Con el mismo usuario,
ID y datos se devuelve el resultado existente sin reservar otra vez; datos distintos
con el mismo ID producen 409.

Las filas de inventario se bloquean al modificar stock, en orden de producto. Las
transiciones bloquean la transferencia y comprueban su estado de nuevo. Las sucursales
se bloquean en lectura para coordinar con su desactivación. Recepciones repetidas o
simultáneas no duplican lotes ni movimientos. Un rechazo libera la reserva una sola vez.

Se registran movimientos RESERVA, LIBERACION_RESERVA, TRANSFERENCIA_SALIDA y
TRANSFERENCIA_ENTRADA con responsable, fecha, referencia y valores antes/después.
La asignación por lote queda trazable desde la referencia de transferencia.

## Contratos API

Base: `/api/transfers`. Sesión HttpOnly existente, validación de origen en POST.
Fechas JSON ISO 8601; UUID como strings. No se expone hash de solicitud ni información
de autenticación. Las respuestas completas también se pueden explorar en `/docs`.

| Método/ruta | Entrada | Éxito |
|---|---|---|
| GET /api/transfers | Sin cuerpo | 200 `{ "transfers": [Transfer] }` |
| GET /api/transfers/options | Sin cuerpo | 200 `{branches, stock, origin_ids, can_create}` |
| GET /api/transfers/{id} | UUID en ruta | 200 Transfer |
| POST /api/transfers | CreateTransfer | 201 Transfer; 200 si es reintento ya confirmado |
| POST /api/transfers/{id}/approve | Sin datos adicionales | 200 Transfer |
| POST /api/transfers/{id}/reject | `{ "reason": "Motivo" }` | 200 Transfer |
| POST /api/transfers/{id}/dispatch | Sin datos adicionales | 200 Transfer |
| POST /api/transfers/{id}/receive | `{ "items": [{ "product_id": "UUID", "quantity": 8 }] }` | 200 Transfer |

CreateTransfer:

```json
{
  "request_id": "UUID generado una vez por solicitud",
  "origin_id": "UUID sucursal origen",
  "destination_id": "UUID sucursal destino",
  "items": [{ "product_id": "UUID producto", "quantity": 8 }]
}
```

`Transfer` contiene `id`, `origin_id`, `origin_name`, `destination_id`,
`destination_name`, `state`, `created_at`, `requested_by`, `rejection_reason`,
`items`, `actions` y `timeline`. Cada ítem contiene producto, nombre, SKU, cantidad
y lotes (número, vencimiento y unidades). Cada evento contiene `event`, `at` y `user`.
Las acciones devueltas son las disponibles para ese usuario en el estado actual.

Errores: 401 sesión inválida; 403 permisos/sucursal/origen HTTP no autorizado;
404 transferencia inexistente; 409 stock insuficiente, estado incompatible o conflicto;
422 datos inválidos. El manejador general existente evita exponer detalles internos
en errores 500. Las cantidades deben ser enteros positivos, máximo técnico un millón
por producto y cien productos por solicitud.

## Frontend

La pantalla toma la identidad desde el contexto de sesión existente. Carga listado y
opciones desde FastAPI, y filtra localmente texto, estado, origen, destino y fecha de
solicitud. Los cuatro recuentos representan todas las transferencias visibles para el
usuario, independientemente de los filtros. «Recibidas hoy» utiliza la fecha local
del navegador y el evento real de recepción.

Los modales reutilizan el tamaño global del 98%, controles y tipografía del proyecto.
Al abrir un detalle se actualizan estado y permisos desde el backend. Cada acción
requiere una confirmación expresa; rechazo pide motivo y recepción pide conteo.
Los botones se bloquean mientras se envía y se muestra el resultado confirmado.

Una solicitud sin respuesta conserva su ID/datos en sessionStorage para reintentar
en la misma pestaña incluso tras recargarla. No contiene credenciales. Si se cierra
la pestaña, se pierde ese borrador: se debe revisar el listado antes de solicitar
de nuevo. Al reabrir con respuesta pendiente, no se pueden alterar sus datos hasta
resolver el intento. Los permisos reales siempre se validan de nuevo en FastAPI.

## Verificación realizada

- 30 pruebas nuevas de E4: todas aprobadas.
- Suite completa: **242 passed**, dos avisos de deprecación de dependencias de tests.
- TypeScript y build Vite: aprobados.
- Ruff en archivos de esta entrega: aprobado.
- ESLint general: conserva cuatro errores previos en ExpirationAlertsPanel,
  InventoryMovementHistory y LotPanel; ninguno en Transferencias.
- Ruff general: conserva tres hallazgos previos de Inventario (imports y uso de
  date.today). No se modificó ese módulo para corregirlos.
- No se realizó validación visual automatizada: no había navegador conectado disponible.
- Servidor reiniciado y comprobado por HTTP: login 200, listado/opciones 200,
  frontend 200, logout 204 y acceso posterior sin sesión 401. OpenAPI expone las
  siete rutas nuevas; PostgreSQL quedó en `0009_transferencias`.

Al terminar había **una sola sucursal activa** y un producto transferible. Para
probar el recorrido completo desde la interfaz se necesita crear o activar una
segunda sucursal con la gestión existente. No se crearon sucursales reales de
negocio ni usuarios adicionales automáticamente. Los tests usan sus propias
sucursales ficticias y no dependen de los datos manuales.

Casos cubiertos: reserva FEFO sin salida, reintento idempotente, stock insuficiente,
reservas previas, lotes vencidos/inactivos, aprobación, rechazo y liberación única,
flujo completo con kardex/lotes, recepción repetida, cantidades diferentes, permisos,
alcance por sucursal, datos inválidos, autenticación, origen no permitido, desactivación
de sucursal pendiente, vencimiento tras reservar, conflicto en lote destino y rollback
de varios productos. Tres casos usan conexiones PostgreSQL independientes: competencia
por últimas unidades, solicitud repetida y recepción simultánea. También se comprueba
que el seed conserve roles personalizados.

Los casos normales se revierten con rollback. Los tres de concurrencia confirman
fixtures temporales con UUID exclusivos y eliminan únicamente esos datos en `finally`.
No ejecutar la suite contra producción.

## Ejecutar en Windows PowerShell

Desde esta carpeta del frontend (donde están package.json y backend):

```powershell
docker compose up -d db
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.transfers.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

En otra consola, desde la carpeta del frontend:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

Si aún no están instaladas las dependencias, utilizar el procedimiento de README;
esta entrega no añade paquetes ni variables de entorno. Verificación:

```powershell
cd backend
$env:SIGFQ_TEST_ROLLBACK = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_transfers.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app/transfers tests/test_transfers.py
cd ..
npm.cmd run build
npm.cmd run lint
```

## Prueba manual

1. Abrir http://127.0.0.1:5173 e iniciar sesión con un administrador existente.
2. Refrescar o volver a iniciar sesión después del seed para ver Transferencias.
3. Tener dos sucursales activas y un producto con stock y lotes vigentes en origen.
   No basta con crear el producto en Catálogo. No se cargó stock ficticio en los
   productos del usuario para esta entrega.
4. Abrir Transferencias → Nueva transferencia, seleccionar origen/destino y unidades.
5. Revisar Inventario: el físico se conserva, aumenta reservado y baja disponible.
6. Aprobar desde el administrador: continúa reservado. También se puede rechazar
   indicando motivo y comprobar que disponible se recupera sin cambiar físico.
7. Con usuario autorizado asignado al origen, confirmar despacho: baja físico,
   se libera reserva y queda En tránsito. Destino todavía no recibe unidades.
8. Con usuario autorizado asignado al destino, abrir Confirmar recepción. Escribir
   una cantidad diferente: debe rechazarse sin cambiar stock. Escribir las cantidades
   completas: estado Recibida, stock/lotes destino y movimiento de entrada.
9. Consultar el detalle para ver responsables, fechas y lotes. Actualizar la página
   o repetir la confirmación no debe duplicar inventario.

## Impacto para el equipo y pendientes

Los integrantes deben integrar los archivos compartidos enumerados arriba, ejecutar
la migración y el seed, y reiniciar FastAPI. No hay cambios en dependencias o .env,
ni cambios obligatorios para consumidores anteriores. React incorpora un consumidor
nuevo; Flutter no se modifica. La migración depende de 0008: no omitirla ni renumerar
el historial porque E4-H4 esté en discusión.

Pendientes reales: revisión del equipo y validación visual/manual; definición de
E4-H4; diferencias ya existentes en los rangos de alertas E3 frente a AGENTS.md;
errores previos de lint. `alembic check` detectaba antes un índice de movimientos
existente en 0007 pero ausente en el modelo ORM; no se borró ni alteró ese índice.
Esta versión no resuelve recepciones parciales ni discrepancias de transporte.

## Puntos de restauración

Antes de transferencias se guardaron fuente y base local, incluyendo los cambios
previos de E4-H4, fuera del repositorio:

- `N:\TempD\sigfq-pre-transferencias-20260928-193527.zip`
- `N:\TempD\sigfq-pre-transferencias-tracked.patch`
- `N:\TempD\sigfq-pre-transferencias-20260928-193530.dump`

El punto anterior a E4-H4 es el tag `restore/pre-e4-h4-20260928` (aaf3de7), con
dump `N:\TempD\sigfq-pre-e4-h4-20260928-180831.dump`. El dump contiene datos locales:
no subirlo a Git. No ejecutar downgrade/reset para restaurar sin revisar los nuevos
movimientos, reservas y datos que puedan haberse creado después del respaldo.

Los cambios de esta entrega se mantienen locales; no se hizo commit ni push.
