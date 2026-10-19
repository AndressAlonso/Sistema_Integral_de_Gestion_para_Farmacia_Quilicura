# Integración E6 en Proyecto

Se integra `feat/e6-ecommerce-jesus` (03873ba) sobre Proyecto (e49a3a9).
La rama fuente permanece intacta. Se conservan rutas, servicios y permisos de
POS/caja y escáner, y se agregan las rutas públicas `/tienda` y los routers E6.
Los conflictos se resolvieron en `backend/app/main.py` y `src/routes/AppRouter.tsx`.
La prueba del catálogo de permisos ahora contempla los 17 permisos existentes,
incluidos los tres de POS. No se eliminaron permisos para satisfacer la prueba.

## Migraciones

Se conserva `0012_clientes` de la rama fuente sin cambiar su antecesora.
`0016_merge_e6_e8` une `0012_clientes` y `0015_lectura_scanner`; no contiene DDL.
Las migraciones anteriores permanecen intactas. La base local está en
`0013_reversas_venta`: no se aplicó ningún cambio de esquema durante este merge.
Antes de actualizar PostgreSQL se requiere autorización para las tablas de
clientes/sesiones y escáner pendientes. No ejecutar seeds ni recrear la base.

## Verificación realizada

- Build TypeScript/Vite correcto.
- Siete pruebas frontend de sesión de cliente aprobadas.
- Selección backend inicial: 120 aprobadas, 3 omitidas y 11 fallidas.
  Diez fallos corresponden a la tabla cliente ausente; uno al conteo heredado
  de permisos. Este último se corrigió: las diez pruebas unitarias del catálogo
  de roles pasaron al repetirlas (ocho pruebas PostgreSQL omitidas en esa repetición).
- Ruff de main.py correcto; Alembic reconoce una sola punta 0016_merge_e6_e8.
- Lint frontend: cuatro errores preexistentes en los componentes de Inventario
  ExpirationAlertsPanel, InventoryMovementHistory y LotPanel.

La integración no se declara validada completamente hasta aplicar las migraciones
autorizadas y repetir las pruebas de clientes/invitados. E6-H5 sigue pendiente
de E7-H1, tal como documenta la rama fuente.

## Verificación posterior autorizada — 11 de octubre de 2026

El usuario autorizó aplicar las migraciones. Se generó un respaldo local ignorado
por Git en backend/data/backups/before-e6-e8-20261011-212250.dump y se ejecutó
alembic upgrade head. La base quedó en 0016_merge_e6_e8.
La selección de pruebas de catálogo, carrito, invitados, clientes, roles,
alertas de vencimiento, POS y concurrencia finalizó con 139 aprobadas.
Los diez fallos por tablas ausentes de la comprobación anterior quedaron resueltos.
FastAPI se reinició con los routers integrados. No se probó la app en un Android
físico; tampoco se considera completada E6-H5 por esta integración.
