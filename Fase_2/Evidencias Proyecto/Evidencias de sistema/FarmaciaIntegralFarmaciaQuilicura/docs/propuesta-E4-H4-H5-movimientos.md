# Propuesta pendiente de aprobación — E4-H4 / E4-H5

Aprobada explícitamente por el usuario. Implementación y operación actual en
[E4-H4-H5-movimientos.md](E4-H4-H5-movimientos.md). Se conserva esta propuesta como
registro de la decisión previa a la migración 0010.

## Interfaz acordada

En Transferencias, junto a «Nueva transferencia», botón «Registrar movimiento».
Abre un modal al 98% con selector Recepción de mercadería / Ajuste de inventario.
Una sucursal por operación, varias filas y una confirmación para guardar todo.

- Recepción: documento, proveedor, fecha, producto, lote existente y cantidad recibida.
  Se consulta el vencimiento del lote; no se vuelve a crear el lote en este formulario.
- Ajuste: motivo obligatorio, producto/lote existente, cantidad actual, cantidad final
  y diferencia visible. Se cambia el lote seleccionado y el total de su inventario
  en la misma transacción. No se cambia el reservado ni se permite consumir reservas.
- El botón anterior de recepción en Inventario se retira al integrar este acceso.
- La creación de lotes sigue en Inventario. Si no hay lote seleccionable, el formulario
  informa ese requisito y no inventa ni crea automáticamente un lote.
- No incluye asociación automática de todos los productos con todas las sucursales:
  esa propuesta de inventario es independiente de este cambio.

## CAMBIO DE BASE DE DATOS PROPUESTO

HU: E4-H5; integración visual con E4-H4.

Motivo: conservar un ajuste de varias filas como una operación identificable, con
cantidades anteriores/nuevas por lote y reintentos seguros.

Estado actual: modelos/migraciones 0001–0009; existen inventario_sucursal,
lote_inventario, movimiento_inventario, recepcion_mercaderia y su detalle.
MovimientoInventario guarda el antes/después del stock agregado y una referencia
genérica. No tiene cabecera de ajuste ni cantidades anterior/nueva por lote.
La inspección es del código/migraciones; debe verificarse la instancia PostgreSQL
conectada antes de aplicar el cambio.

Cambio propuesto: dos tablas nuevas, conservando todas las tablas existentes.

Tablas afectadas: nuevas ajuste_inventario y ajuste_inventario_detalle.
inventario_sucursal, lote_inventario y movimiento_inventario solo reciben cambios
de datos al confirmar un ajuste; su estructura permanece igual.

Columnas propuestas:

| Tabla | Columnas |
|---|---|
| ajuste_inventario | id UUID PK (ID de solicitud), solicitud_hash VARCHAR(64), sucursal_id UUID, usuario_id UUID, motivo VARCHAR(250), creado_en TIMESTAMPTZ |
| ajuste_inventario_detalle | id UUID PK, ajuste_id UUID, lote_id UUID, cantidad_anterior INTEGER, cantidad_nueva INTEGER |

Todas obligatorias. UUID de detalle generado por backend; fecha de cabecera con
valor inicial del servidor. Producto y sucursal de cada detalle se obtienen desde
su lote/inventario, sin duplicar esas referencias.

Relaciones: cabecera → sucursal/usuario; detalle → cabecera/lote. Foreign keys
RESTRICT para conservar referencias históricas. Índices en estas foreign keys.
Los movimientos del kardex referencian el UUID de cabecera con referencia_tipo
AJUSTE_INVENTARIO, reutilizando el mecanismo actual.

Restricciones: PK UUID; UNIQUE(ajuste_id,lote_id); CHECK motivo no vacío;
CHECK cantidades >= 0 y cantidad_anterior <> cantidad_nueva. Validación de pertenencia
de los lotes a la sucursal, permisos y reservas en el servicio transaccional.

Migración requerida: Sí, una nueva después de 0009_transferencias. No modificar
0008 ni 0009, borrar historial o usar downgrade.

Impacto sobre otros módulos: Inventario mostrará movimientos AJUSTE ya soportados
por su interfaz. Coordinación con las reservas de Transferencias mediante los
mismos bloqueos de inventario. Usuarios involucrados quedan referenciados por FK.

Impacto sobre API: endpoints nuevos para opciones y ajustes. Se conserva el contrato
actual POST /api/goods-receipts para recepción. No se cambia login ni transferencias.

Impacto sobre frontend: botón y modal en Transferencias; selección de lotes existentes;
retiro del acceso anterior de recepción en Inventario. Permiso nuevo
inventario.ajustar para Administrador/Encargado de inventario mediante seed reproducible.
Permiso inventario.registrar_entrada existente para recepción.

Riesgos: ajustar basándose en datos desactualizados, afectar unidades reservadas,
duplicar una confirmación o producir diferencias entre lotes y stock agregado.
Mitigación: bloqueo transaccional, comparación de cantidad leída, comprobación de
reservas agregadas y por lote, ID de solicitud y rollback completo ante cualquier error.

Compatibilidad con datos existentes: no cambia ni elimina registros existentes.
No convierte entradas previas en ajustes ni modifica stock durante la migración.

## Contratos propuestos

Todos requieren sesión existente y validación de origen en POST.

| Método/ruta | Permisos | Respuesta |
|---|---|---|
| GET /api/stock-operations/options | inventario.registrar_entrada o inventario.ajustar | 200: sucursales y productos/lotes visibles, cantidades y vencimientos |
| POST /api/inventory-adjustments | inventario.ajustar | 201 ajuste; 200 si se reintenta el mismo ID/datos |
| GET /api/inventory-adjustments/{id} | inventario.ajustar, alcance por sucursal | 200 detalle de ajuste confirmado |
| POST /api/goods-receipts | inventario.registrar_entrada | Contrato actual: 201 recepción o 200 reintento |

Administrador opera en sucursales activas; encargado opera en su sucursal asignada.

Request de ajuste:

```json
{
  "request_id": "UUID",
  "branch_id": "UUID",
  "reason": "Diferencia detectada en conteo físico",
  "items": [
    { "lot_id": "UUID", "expected_quantity": 20, "new_quantity": 18 }
  ]
}
```

Respuesta de ajuste: id, branch_id, user_id, reason, created_at e items con lote,
producto, cantidad anterior, nueva y diferencia. No incluye hash interno.

Errores: 401 sin sesión; 403 sin permiso o sucursal ajena; 404 registro inexistente;
409 datos cambiados, reserva afectada, lote inactivo o ID usado con otro contenido;
422 datos incompletos, motivo vacío, negativos o lotes repetidos; 500 mensaje seguro.

La recepción usa el número/vencimiento del lote seleccionado para construir el
request existente. Crear lotes sigue fuera del modal y no cambia el contrato anterior.

## Archivos previstos

- backend/app/inventory_adjustments/: schemas, repositorio, servicio, rutas y seed.
- backend/app/models.py; backend/app/main.py; backend/app/role_catalog.py.
- Una migración nueva 0010, solo después de aprobación.
- src/pages/e4-transfers/: formulario compartido de movimientos y cliente API.
- src/pages/e4-transfers/TransfersPage.tsx: botón y mensajes de confirmación.
- src/pages/e3-inventory/InventoryPage.tsx: retirar acceso anterior de recepción.
- Reutilizar/mover ReceiptDialog y receipts.api según convenga sin duplicar lógica.
- Pruebas backend y documentación E4-H4/H5.

Pruebas: entrada por lote existente, ajuste positivo/negativo a varios lotes,
motivo/negativos inválidos, reserva agregada y por lote, sucursal/permisos, rollback
de varias filas, datos desactualizados, reintento y concurrencia. Ejecutar también
la suite existente de transferencias y build/lint.
