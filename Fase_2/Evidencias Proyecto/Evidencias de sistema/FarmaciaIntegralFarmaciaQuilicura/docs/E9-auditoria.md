# E9-H2 y E9-H3: auditoría

La pantalla `/admin/audit` está disponible para Administrador y Socio. Permite consultar responsable histórico, fecha, operación, sucursal y detalle. No permite editar ni eliminar registros.

## Cobertura

Los cambios ORM realizados desde solicitudes autenticadas de usuarios internos se registran en la misma transacción: usuarios, asignaciones de roles, permisos de roles, sucursales, categorías, productos, códigos de barras, mínimos de inventario, movimientos de existencias, recepciones, ajustes, transferencias, aperturas/cierres de caja, ventas y reversas. Se guardan únicamente los campos definidos en `app/audit/recording.py`; no se serializan entidades completas ni contraseñas, hashes o tokens.

Se integran además los eventos explícitos existentes de cambios de precio, promociones, habilitación de lotes, pago simulado y preparación de pedidos. Cada evento nuevo de un usuario interno conserva su nombre. Una operación puede producir un registro principal y registros de movimientos asociados. Los cambios que se revierten no dejan eventos confirmados.

No es una grabación de todas las interacciones: consultas, navegación, intentos fallidos, autenticación, SQL directo, scripts externos y operaciones de clientes sin sesión interna no quedan cubiertos por este observador. Tampoco se reconstruyen acciones anteriores que nunca fueron registradas. Al añadir nuevas operaciones o escrituras SQL masivas se debe revisar su cobertura explícitamente.

## Consultas y fechas

`GET /api/audit?branch_id=UUID&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&page=1&limit=20`

Respuesta: `events`, `total`, `page`, `limit`, `branches`. Acceso 401 sin sesión y 403 sin rol permitido. Los filtros se combinan; fechas inclusivas según `America/Santiago`, resueltas por PostgreSQL (incluye cambios de horario). Orden descendente por fecha y secuencia. Se valida el rango, UUID y paginación. Las transferencias se encuentran por origen o destino; acciones generales sin sucursal no aparecen al seleccionar una sucursal.

La sucursal de los registros nuevos del observador se conserva como dato histórico, sin añadir una relación que impida eliminar sucursales vacías. Se mantienen las relaciones existentes de otros eventos. El detalle de consulta filtra los campos expuestos.

## Identidad e integridad

La migración `0021_auditoria_actor_historico` retira únicamente la FK de `evento_auditoria.usuario_id`. El UUID permanece y el nombre se conserva en `datos_cambio.usuario_nombre`. Para eventos antiguos se prioriza el nombre ya guardado; cuando solo existe la cuenta actual, se recupera su nombre y se marca `nombre_recuperado_en_migracion`. No representa una reconstrucción del nombre original si este cambió antes de la migración.

El trigger de inmutabilidad se deshabilita exclusivamente dentro de la migración transaccional para esa actualización y se reactiva antes del commit. Las restricciones de ventas, caja, inventario y otras relaciones permanecen: algunas cuentas todavía requerirán desactivación. El downgrade se rechaza si hay responsables eliminados, para no perder historial.

## Alcance del sprint

E9-H2: registro, responsable, fecha, consulta e interfaz implementados para la cobertura indicada. E9-H3: sucursal, período, integración y validación implementados para auditoría. La aplicación de filtros al dashboard sigue pendiente porque ese módulo aún no está desarrollado.

Pruebas: `SIGFQ_TEST_ROLLBACK=1 python -m pytest tests/test_audit.py`; frontend `npx vitest run src/pages/e9-audit/AuditPage.test.tsx --environment jsdom`. Las pruebas de base de datos usan transacciones revertidas.
