# Propuesta E5 — POS, caja, comprobantes y reversas

Estado: aprobado por el usuario en esta sesión e implementado mediante 0012 y 0013.
También se aprobó expresamente agregar sesion_caja_id a reversa_venta para el reembolso.
Las decisiones finales y la verificación están en E5-pos-caja.md.
Rama de trabajo: Proyecto. Se reutilizan React, FastAPI y PostgreSQL existentes.

## Cambio de base de datos propuesto

HU: E5-H1 a E5-H6.

Motivo: registrar ventas y sesiones de caja reales con trazabilidad, concurrencia
e identificación de reintentos. El catálogo no representa una venta y la sesión
de autenticación no representa una caja.

Estado actual del código: migraciones hasta 0011_evento_auditoria, sin modelos de
venta, caja o reversa. No se ha verificado el esquema de una base conectada en este clon.

Cambio propuesto: agregar las siguientes tablas. Los nombres son propuestos y
deben contrastarse con el modelo acordado antes de aprobar la migración.

| Tabla | Columnas principales propuestas |
|---|---|
| sesion_caja | id UUID, usuario_id, sucursal_id, apertura_en, monto_inicial, cierre_en nullable, efectivo_contado nullable, resumen_cierre JSONB nullable |
| venta | id UUID, solicitud_hash, sesion_caja_id, usuario_id, sucursal_id, fecha, medio_pago, subtotal, descuento, total |
| venta_detalle | id UUID, venta_id, producto_id, nombre y SKU históricos, cantidad, precio_base, precio_final, promoción aplicada como snapshot JSONB nullable, total |
| venta_lote | id UUID, venta_detalle_id, lote_id, cantidad |
| reversa_venta | id UUID, solicitud_hash, venta_id, usuario_id, fecha, tipo, motivo, importe |
| reversa_venta_detalle | id UUID, reversa_id, venta_lote_id, cantidad, reintegrar_stock, motivo_condicion |

Columnas afectadas en tablas existentes: ninguna propuesta en esta fase.
Tablas existentes utilizadas: usuario_interno, sucursal, producto,
inventario_sucursal, lote_inventario, movimiento_inventario y evento_auditoria.

Relaciones: caja a usuario/sucursal; venta a caja/usuario/sucursal; detalle a
venta/producto; asignación a detalle/lote; reversa a venta/usuario; detalle de
reversa a reversa/asignación original. Claves foráneas con RESTRICT, sin borrado
en cascada del historial.

Restricciones: UUID como identificadores; NUMERIC y Decimal para dinero;
fechas con zona horaria; cantidades positivas; importes no negativos;
índice único parcial usuario/sucursal donde cierre_en sea NULL; unicidad de
producto por detalle de venta y de lote por asignación; cierre consistente con
efectivo contado. Validar medios EFECTIVO, DEBITO, CREDITO, TRANSFERENCIA.
Los IDs de venta/reversa identifican también reintentos; repetir ID con datos
distintos devuelve conflicto. Definir tipos ANULACION/DEVOLUCION con el equipo.

Migración requerida: sí, versionada después del head vigente, sin editar 0011.

Impacto en otros módulos: las ventas consumen inventario; las referencias
históricas bloquean eliminaciones. La desactivación de sucursales debe contemplar
cajas abiertas. Se debe mantener un orden de bloqueos compatible con E4.

Impacto API: endpoints nuevos; no reemplazar contratos de E1–E4.
Impacto frontend: convertir las rutas vacías /admin/pos y /admin/cash en pantallas
funcionales, reutilizando layout, sesión y estilos compartidos.
Riesgos: promociones aún no integradas; diferencias previas entre stock y lotes;
reintegro de devoluciones y su efecto financiero todavía por acordar.
Compatibilidad: creación aditiva de tablas, sin borrar ni transformar datos previos.

## Contratos propuestos

Todos corresponden a E5; requieren sesión interna y autorización en backend.
La sucursal se obtiene del usuario, no de una selección arbitraria del cliente.
Errores comunes: 401 sesión, 403 autorización, 404 inexistente, 409 conflicto,
422 validación, 500 mensaje genérico.

| HU | Método y ruta propuesta | Entrada | Resultado |
|---|---|---|---|
| H1 | GET /api/pos/products?q= | nombre, SKU, UUID o código | productos activos, precio y stock vendible de sucursal |
| H1/H2 | POST /api/pos/quote | productos y cantidades | precios calculados, promoción seleccionada, totales y versión de cotización |
| H5 | GET /api/cash/current | ninguna | caja actual o null |
| H5 | POST /api/cash/open | request_id, monto_inicial | sesión de caja |
| H5 | GET /api/cash/{id}/summary | ninguna | indicadores actuales |
| H5 | POST /api/cash/{id}/close | efectivo_contado, versión del resumen | cierre persistido |
| H3 | POST /api/pos/sales | request_id, productos/cantidades, medio, cotización confirmada | venta registrada |
| H4 | GET /api/pos/sales/{id}/receipt | ninguna | comprobante histórico imprimible |
| H6 | GET /api/pos/sales | filtros acordados de búsqueda | ventas autorizadas |
| H6 | POST /api/pos/sales/{id}/reversals | request_id, tipo, motivo, ítems y condición | reversa vinculada |

Permisos nuevos propuestos: pos.operar, caja.operar, ventas.reversar; conservar
control por rol para reversas de Administrador y alcance por sucursal para cajeros.
Los códigos definitivos deben acordarse antes de crear seeds o contratos finales.

## Promociones y móvil

No crear una tabla provisional de promociones. El servicio de cálculo consultará
un proveedor intercambiable: inicialmente fixture explícito de desarrollo,
desactivado por defecto, después persistencia de E2-H3. Comparar promociones de
producto/categoría, elegir menor precio y no acumular. Nunca aceptar descuentos
manuales enviados por React ni activarlos silenciosamente en producción.

La interfaz acepta búsqueda por teclado/código y lector USB. Mostrará móvil sin
vincular mientras E8 no exista; no simular una vinculación exitosa. El código
recibido desde E8 se enviará al mismo flujo de búsqueda de productos.

## Decisiones pendientes al redactar la propuesta (ver resolución en E5-pos-caja.md)

- Condiciones que permiten reincorporar devoluciones y cómo identificar lote.
- Efecto de reversas sobre efectivo/caja abierta y ventas de cajas ya cerradas.
- Un medio de pago por venta como propuesta inicial; pagos mixtos no definidos.
- Política de redondeo monetario y tratamiento de promociones al devolver partes.
- Una anulación posterior al despacho físico no equivale automáticamente a
  devolución vendible; la venta original nunca se elimina.

## Verificación prevista

Stock insuficiente/vencido/reservado; FEFO; límites del carrito; promociones con
vigencia/producto/categoría y conflictos; apertura con cero y apertura duplicada;
venta sin caja; ventas simultáneas de últimas unidades; reintento idéntico y
conflictivo; fallo intermedio con rollback; cierre contra venta concurrente;
contenido histórico del comprobante; reversas acumuladas que exceden la compra;
roles/sucursal; integración de frontend, lint y compilación.
