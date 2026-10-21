# E7-H4 — Preparación de pedidos

## Alcance y flujo

Pedido pagado → Iniciar preparación → En preparación → Confirmar productos preparados → Listo para retiro.

Se puede iniciar preparación mientras llegan traslados. FastAPI impide marcar listo si existe una transferencia no recibida, reservas incompletas, reservas en otra sucursal, lotes vencidos/inactivos, producto inactivo o cantidades inconsistentes. La sucursal debe estar activa.

Preparar y marcar listo NO descuenta stock, NO libera reservas, NO registra otra venta y NO confirma entrega. Correos (E7-H5), QR/retiro (E7-H6) y pago real con Flow (E7-H2) no forman parte de esta implementación. El simulador existente permite probar un pedido pagado sin cobrar dinero.

## Persistencia

- Migración nueva `0020_preparacion_pedidos`, posterior a `0019_transferencias_pedido`.
- Amplía únicamente `pedido_online.ck_pedido_estado` con `EN_PREPARACION` y `LISTO_PARA_RETIRO`.
- No crea tablas, columnas ni relaciones. Conserva los datos actuales y las migraciones anteriores.
- Cada transición genera un `evento_auditoria` con acción `E7-H4_ESTADO`, referencia `Pedido {UUID}`, usuario, fecha, estado anterior y nuevo. Estado e historial se confirman juntos.
- El historial muestra creación, pagos simulados existentes y transiciones E7-H4. No inventa eventos históricos ausentes.
- El downgrade rechaza revertir si hay pedidos en los nuevos estados.

## Permisos y sucursales

`pedidos.consultar`: listado, detalle, productos, traslados e historial.

`pedidos.preparar`, junto con consulta: iniciar preparación y marcar listo.

Se agregan a Administrador y Encargado de pedidos mediante `python -m app.role_catalog --reconcile-e7`, sin retirar permisos ni modificar otros roles. El administrador trabaja con todas las sucursales; los demás usuarios solo con pedidos cuya sucursal de retiro coincide con su sucursal asignada. Los permisos se comprueban en backend, incluso si se accede directamente a la API. El administrador también necesita los permisos correspondientes.

## Contratos API

Todos requieren la cookie de sesión interna vigente; las acciones validan el origen de la petición. Las respuestas no incluyen hashes, tokens ni información interna de pagos.

| Método y ruta | Entrada | Respuesta 200 |
|---|---|---|
| GET `/api/orders` | `state`, `branch_id` opcionales; `page` ≥1, `limit` 1–100 (15 por defecto) | `orders`, `total`, `page`, `limit`, `branches` autorizadas |
| GET `/api/orders/{id}` | UUID | Resumen, `customer`, `actions`, `ready_blocked_reason`, `transfers`, `history` |
| POST `/api/orders/{id}/preparation` | `{"expected_state":"PAGADO"}` | Detalle actualizado en preparación |
| POST `/api/orders/{id}/ready` | `{"expected_state":"EN_PREPARACION"}` | Detalle actualizado listo para retiro |

El resumen reutiliza el contrato de pedidos: `id`, `number`, `created_at`, `status`, `total` decimal como texto, `currency`, `pickup_branch`, `items`.

El encabezado Estado ofrece selección múltiple y ordenación. GET `/api/orders` acepta además `states=PAGADO&states=EN_PREPARACION` (máximo cinco valores) y `sort=newest|state_asc|state_desc`. El parámetro anterior `state` se conserva; combinar `state` y `states` devuelve 422. Orden por estado: pendiente de pago, pagado, en preparación, listo para retiro, cancelado; descendente invierte ese orden. Dentro del mismo estado se ordena por fecha reciente e ID estable. El filtro y orden se aplican en backend antes de paginar, conservando la restricción de sucursal. No modifica esquema ni datos. El selector anterior se reemplazó por el menú en la columna para evitar filtros duplicados.

Sucursal de retiro utiliza el mismo componente `OrderColumnFilter.tsx`, con casillas y orden A–Z/Z–A. GET `/api/orders` acepta `branch_ids=UUID1&branch_ids=UUID2` (máximo 100) y los órdenes adicionales `branch_asc|branch_desc`. `branch_id` continúa funcionando, pero no puede combinarse con `branch_ids`. Un usuario sin rol Administrador no puede solicitar sucursales ajenas, ni siquiera combinándolas con la propia. Estado y sucursal se filtran juntos; la ordenación es única y cambiar solo las casillas conserva el orden de la otra columna. Seleccionar todas las sucursales vuelve al alcance autorizado completo. No hay cambios de esquema ni nuevos permisos.

El historial contiene `at`, `actor`, `previous`, `status`. Las transferencias incluyen `id`, `status`, `origin`, `destination`. Los errores esperados son 401 (sin sesión), 403 (permiso/sucursal/origen), 404 (pedido inexistente), 409 (transición o stock incompatible) y 422 (entrada inválida). Los errores inesperados se manejan mediante la infraestructura global existente.

El mismo POST repetido después de completarse retorna el estado sin duplicar eventos. Si el pedido ya avanzó a otra etapa, devuelve 409. Se utiliza el bloqueo del pedido compartido con E7-H1/H3 y bloqueos del inventario al marcar listo; no se confía en el estado mostrado por React.

Los endpoints de clientes no cambian de forma; `status` puede tomar los dos nuevos valores. Consumidores React/Flutter deben reconocerlos. Un pedido en preparación/listo continúa siendo un pedido pagado; no debe generarse otro pago ni rebajarse a `PAGADO` por callbacks repetidos.

## Archivos nuevos

- `backend/app/orders/preparation.py`: servicio, consultas de preparación y validación transaccional reutilizando persistencia de pedidos/transferencias.
- `backend/app/orders/admin_routes.py`: rutas internas y validación del cuerpo.
- `backend/migrations/versions/0020_preparacion_pedidos.py`: restricción de estados.
- `backend/tests/test_order_preparation.py`: pruebas PostgreSQL con rollback.
- `src/pages/e7-orders/orders.api.ts`: cliente HTTP, tipos y etiquetas de estados.
- `src/pages/e7-orders/OrdersPage.tsx`: bandeja paginada con filtros de estado y sucursal.
- `src/pages/e7-orders/OrderPreparationDialog.tsx`: detalle, confirmación, traslados e historial.
- `src/pages/e7-orders/orders.css`: estilos específicos usando el diseño administrativo existente.
- `src/pages/e7-orders/OrderPreparationDialog.test.tsx`: confirmación, bloqueos y errores.

## Archivos existentes modificados

- `backend/app/orders/models.py`: estados permitidos en ORM.
- `backend/app/orders/development.py`: reintentos de pago simulado no revierten preparación.
- `backend/app/transfers/service.py`: permitir despacho/recepción cuando el pedido está en preparación.
- `backend/app/branches/repository.py`: impedir desactivar sucursal con pedidos en preparación/listos.
- `backend/app/role_catalog.py`: permisos y carga aditiva E7.
- `backend/app/main.py`: registrar router después del simulador para conservar sus rutas.
- `src/routes/AppRouter.tsx`: activar pantalla existente `/admin/orders`.
- `src/layouts/adminNavigation.ts`: usar permiso real en lugar del placeholder por rol.
- `src/pages/e6-ecommerce/components/OrderHistoryItem.tsx` y `pages/OrderConfirmationPage.tsx`: mostrar correctamente los nuevos estados.

## Ejecución — Windows PowerShell

Desde la raíz de la aplicación (la carpeta que contiene `package.json` y `backend`), con PostgreSQL disponible y el `.env` existente:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.role_catalog --reconcile-e7
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

En otra consola, desde la raíz de la aplicación:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

No se añaden dependencias ni variables de entorno nuevas. Si es una instalación nueva, instalar las dependencias existentes del repositorio antes de ejecutar.

## Pruebas

```powershell
Set-Location backend
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv\Scripts\python.exe -m pytest tests/test_order_preparation.py tests/test_order_transfers.py tests/test_orders.py tests/test_transfers.py tests/test_branches.py -q
Set-Location ..
npx.cmd vitest run src/pages/e7-orders/OrderPreparationDialog.test.tsx src/pages/e6-ecommerce/tests/orders.test.tsx src/pages/e4-transfers/TransferDetail.test.tsx --environment jsdom
npm.cmd run build
```

Se prueban: pedido no pagado/cancelado, preparación con transferencia pendiente, recepción seguida de listo, pedido local sin traslado, stock insuficiente/inactivo/vencido, historial y reintentos, origen HTTP, sesión, permisos, aislamiento por sucursal, filtros y datos inválidos. El frontend comprueba confirmación explícita, no duplicar envío y presentación de conflictos. Las pruebas de base de datos usan fixtures ficticias y rollback, no limpian datos del usuario.

Verificación ejecutada el 20/10/2026: 115 pruebas backend aprobadas en el conjunto indicado; después de reforzar la comparación con el total reservado se repitieron las 11 pruebas E7-H4, todas aprobadas. 15 pruebas frontend aprobadas. Build TypeScript/Vite, ESLint de archivos modificados y Ruff de E7-H4 aprobados. Avisos no bloqueantes: deprecación existente Starlette/httpx y bundle Vite mayor que 500 kB. FastAPI reiniciado; rutas publicadas en OpenAPI, listado sin sesión devuelve 401 y la URL del frontend responde 200. No se realizó validación visual manual en navegador.

## Prueba manual

1. Entrar como administrador o encargado autorizado; recargar sesión tras cargar permisos.
2. Crear un pedido online de prueba y simular pago aceptado desde Transferencias (solo desarrollo).
3. Abrir `http://127.0.0.1:5173/admin/orders` y seleccionar el pedido.
   Toda la fila abre el detalle y se resalta al pasar el cursor o enfocar el botón del pedido con teclado. La sección Gestionar estado aparece al inicio del detalle. Si no se puede avanzar, muestra el motivo (pago pendiente, transferencia, reservas, permisos o sucursal); el botón de listo permanece visible pero deshabilitado cuando falta recibir stock.
4. Iniciar preparación; debe aparecer el cambio en el historial.
5. Si necesita traslado, el detalle indica que falta recibirlo y no ofrece marcar listo.
6. Despachar y recibir desde Transferencias con un usuario autorizado. Volver al pedido y pulsar Actualizar.
7. Confirmar productos preparados y marcar listo. Verificar estado e historial; el inventario permanece reservado.
8. Probar usuario de otra sucursal y usuario sin permisos: la API debe impedir la operación.

## Impacto y pendientes reales

Los otros integrantes deben actualizar su rama, ejecutar la nueva migración y la carga de permisos, y reiniciar backend. No editar migraciones anteriores. Coordinar con el responsable de Flow los nuevos valores de estado; un callback repetido no debe reiniciar la preparación. E7-H5 puede usar el evento persistido de cambio a listo como punto de integración; aún no hay envío de correo ni cola de eventos. E7-H6 debe implementar el retiro sin liberar prematuramente reservas. No se ha realizado una prueba de carga con múltiples conexiones simultáneas; se verificaron reintentos y bloqueos funcionales. Revisión de otro integrante pendiente antes de integrar.
