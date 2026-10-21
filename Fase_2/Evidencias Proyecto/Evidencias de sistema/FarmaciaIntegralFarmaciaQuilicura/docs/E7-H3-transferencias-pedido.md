# E7-H3 — Transferencias automáticas por pedido online

## Alcance y estado
Implementada sobre E7-H1 y las transferencias existentes de E4.
La creación se dispara después de un resultado de pago aceptado.
Por ahora el resultado se obtiene mediante un simulador restringido a desarrollo.
No implementa Flow, cobros reales, ventas online, vencimiento de reservas de pago,
preparación E7-H4, correos E7-H5 ni retiro E7-H6.

## Flujo y reservas
1. E7-H1 crea pedido PENDIENTE_PAGO y reservas por lote. Primero la sucursal de retiro,
   después otras sucursales activas. No se repite este cálculo ni se eligen otros lotes.
2. Simulación aceptada: bloquea el pedido, comprueba sus reservas, lo marca PAGADO y
   crea una transferencia AUTORIZADA por sucursal externa en una transacción.
3. La transferencia referencia la reserva original. No incrementa stock_reservado.
   El cálculo de reservas por lote excluye estas transferencias para no sumar dos veces.
4. Despacho: personal autorizado confirma salida; reduce físico y reservado en origen,
   desactiva la reserva original y mantiene trazabilidad de las unidades en tránsito.
5. Recepción: personal autorizado confirma cantidades exactas; incrementa físico y
   reservado en destino. Crea o acumula la reserva de destino del mismo detalle de pedido.
   Las unidades NO quedan disponibles para otras ventas. Admite varios orígenes con
   el mismo producto/lote/vencimiento y conserva las asignaciones originales del traslado.
6. Resultado fallido: cancela solo un pedido pendiente y libera sus reservas; conserva físico.
7. Repetir un resultado idéntico, despacho o recepción no duplica operaciones.
   Cambiar aceptado por fallido o viceversa devuelve 409.
8. Las transferencias online no admiten aprobar ni rechazar manualmente, incluso vía API.

Con stock totalmente local, se marca el resultado aceptado sin crear transferencias.
Un lote vencido/inactivo o conflicto de lote en destino impide confirmar la simulación:
no deja cambios parciales. No se cambia automáticamente el vencimiento ni se reactiva.
Las incidencias de un pedido pagado requieren una decisión operativa posterior; no se
liberan reservas ni se cancela silenciosamente desde el rechazo manual.

## Persistencia
Migración nueva: 0019_transferencias_pedido, posterior a 0018.
- transferencia.pedido_id: UUID opcional, FK pedido_online, RESTRICT.
- UNIQUE(pedido_id, origen_id): evita duplicar el traslado del pedido desde el mismo origen.
- solicitante_id permite NULL únicamente si existe pedido_id (CHECK).
- transferencia_lote.reserva_pedido_id: UUID opcional, FK reserva_pedido, RESTRICT y UNIQUE.
- ck_pedido_estado admite PAGADO, además de PENDIENTE_PAGO y CANCELADO.
No se reescriben migraciones anteriores ni se borra información existente.
El downgrade rechaza la reversión si existen pedidos pagados o transferencias online.

La simulación registra un evento_auditoria con origen SIMULACION_DESARROLLO, responsable,
pedido, fecha y resultado. No crea un pago Flow ni una venta ficticia.

## Contratos
### Transferencias existentes
GET /api/transfers y GET /api/transfers/{id}: autenticación interna, permiso
transferencias.consultar y alcance de sucursal (administrador tiene alcance global).
Respuesta mantiene los campos actuales y añade order_id y order_number, nulos para
las transferencias no asociadas a pedido. requested_by muestra Sistema para automáticas.
POST /api/transfers/{id}/dispatch y /receive mantienen request, permisos y respuestas.
En automáticas, /approve y /reject rechazan con 409 cuando el actor tiene permiso;
sin permiso devuelve 403. Errores generales: 401/403/404/409/422.

### Simulador
Solo con APP_ENVIRONMENT=development y ORDER_PAYMENT_SIMULATION=true.
En producción nunca se habilita; configuración incompatible impide iniciar.
- GET /api/orders/development/availability: sesión interna; {enabled: boolean}.
- GET /api/orders/development/orders: administrador; hasta 100 pedidos pendientes
  más antiguos con número, detalle, total y sucursal. No expone claves/hash.
- POST /api/orders/development/orders/{id}/payment:
  sesión interna de administrador y validación de origen.
  Request: {"outcome": "accepted" | "failed", "confirmed": true}.
  Response: {order: resumen, transfer_ids: UUID[], simulated: true, changed: boolean}.
  404 si deshabilitado/pedido inexistente; 401 sin sesión; 403 sin rol/origen inválido;
  409 estado incompatible o reserva/lote conflictivo; 422 request inválido.
El simulador no está expuesto en la tienda pública y no se activa mediante VITE_*.

## Integración que hará Martín con Flow
Usar el servicio generate_order_transfers(db, order) de app/orders/transfers.py.
Debe recibir un pedido PAGADO bajo lock_order(db, order_id) y dentro de la transacción
que coordina el resultado verificado. Nunca llamar al endpoint del simulador desde Flow.
La implementación real debe conservar el hecho de un pago confirmado si existe una
incidencia logística: no reinterpretarlo como pago fallido por un error de inventario.
E7-H2 todavía debe implementar pagos, venta online única y cancelación/liberación de
pendientes según las reglas del equipo. El simulador no sustituye esas tareas.
Acordar el próximo número de migración antes de integrar otros avances en paralelo.

## Interfaz y permisos
Transferencias habituales sin etiqueta nueva.
Transferencias de pedido con etiqueta turquesa Pedido online y número WEB.
Buscador existente también encuentra el número del pedido. Detalle explica su origen
automático y muestra fechas/actores. Estado conserva su estilo independiente.
Simulador desplegable solo visible para administradores si backend lo habilita.
Encargado de pedidos recibe transferencias.consultar para seguimiento de su sucursal;
no se le concede autorizar, despachar ni recibir. Personal de inventario mantiene sus permisos.
La desactivación de sucursales también considera pedidos PAGADO pendientes de entrega.

## Archivos creados
- backend/app/orders/transfers.py: coordinación de transferencias y reservas del pedido.
- backend/app/orders/development.py: API restringida del simulador.
- backend/migrations/versions/0019_transferencias_pedido.py: cambios versionados.
- backend/tests/test_order_transfers.py: regresiones funcionales de E7-H3.
- src/pages/e4-transfers/PaymentSimulation.tsx: interfaz de simulación con confirmación.
- src/pages/e4-transfers/PaymentSimulation.test.tsx: seguridad visual y doble envío.
- docs/E7-H3-transferencias-pedido.md: este informe.

## Archivos modificados
- backend/app/models.py y app/orders/models.py: relaciones y estado PAGADO.
- backend/app/transfers/{repository,service,schemas}.py: reserva única, ciclo y respuesta.
- backend/app/branches/repository.py: proteger sucursales de pedidos pagados.
- backend/app/role_catalog.py: concesión idempotente de consulta al Encargado de pedidos.
- backend/app/config.py y app/main.py: configuración segura y registro del router.
- backend/.env.example: variable apagada por defecto.
- src/pages/e4-transfers/{TransfersPage,TransferDetail}.tsx, transfers.api.ts y transfers.css:
  etiqueta, búsqueda, seguimiento y acceso al simulador.
- TransferDetail.test.tsx: etiqueta online y ausencia de acciones manuales.
- OrderConfirmationPage.tsx y OrderHistoryItem.tsx: representar PAGADO correctamente.
La configuración backend/.env local habilita el simulador; no se versiona.

## Ejecutar — PowerShell, desde la carpeta de la aplicación
```powershell
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.role_catalog --reconcile-e7
```
Para pruebas locales, configurar backend/.env (sin copiar secretos a Git):
```dotenv
APP_ENVIRONMENT=development
ORDER_PAYMENT_SIMULATION=true
```
Reiniciar API:
```powershell
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```
En otra consola, desde la aplicación:
```powershell
npm.cmd run dev -- --host 127.0.0.1
```

## Verificar manualmente
1. Tener dos sucursales activas y producto publicado online, sin receta, con lotes vigentes.
2. Registrar existencias mediante recepción; elegir una sucursal de retiro con stock insuficiente.
3. En /tienda crear un pedido que pueda cubrirse entre ambas sucursales.
4. Como administrador, abrir /admin/transfers y desplegar Simulación de pago — desarrollo.
5. Actualizar pedidos, elegir el WEB correspondiente, marcar confirmación y aceptar.
6. Ver transferencia autorizada con etiqueta Pedido online; verificar que la reserva no se duplicó.
7. Confirmar despacho: baja físico/reservado de origen; destino aún no recibe unidades.
8. Confirmar recepción con cantidades exactas: sube físico/reservado en destino; disponible no aumenta.
9. Crear otro pedido y simular fallido: queda cancelado y libera sus propias reservas.
10. Reintentar la misma operación: no se duplica; un resultado contrario se rechaza.

## Pruebas
Backend con datos ficticios y rollback:
```powershell
cd backend
$env:SIGFQ_TEST_ROLLBACK='1'
.venv/Scripts/python.exe -m pytest tests/test_order_transfers.py tests/test_orders.py tests/test_transfers.py tests/test_transfer_destination_preflight.py tests/test_transfer_receipt_messages.py -q
```
Frontend desde la aplicación:
```powershell
npx.cmd vitest run src/pages/e4-transfers/PaymentSimulation.test.tsx src/pages/e4-transfers/TransferDetail.test.tsx src/pages/e6-ecommerce/tests/orders.test.tsx --environment jsdom
npm.cmd run build
```
Se comprueban: pago previo, stock local, reservas únicas, rechazo bloqueado, tránsito,
recepción exacta/repetida, varios orígenes y lote destino común, fallo sin efectos parciales,
liberación por pago fallido, estado incompatible, permisos/sucursal, entorno producción y origen HTTP.
Bloqueo advisory por pedido + bloqueo de inventario + constraints previenen duplicaciones.
Estas pruebas con rollback verifican reintentos, pero no son una prueba de carga concurrente
con conexiones independientes. No se declara probado Flow ni una aplicación móvil.

## Impacto para el equipo
Actualizar rama, aplicar 0019 y ejecutar --reconcile-e7. No se añadieron dependencias.
Los campos de transferencias son aditivos; si Flutter tiene enums de estado de pedido debe
contemplar PAGADO. No desplegar con simulador habilitado. E7-H3 está verificable con el
simulador; la integración con el pago real depende de E7-H2.

