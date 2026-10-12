# E3-H2 y E4-H4: lotes creados mediante recepción

Decisión del usuario: ingresar mercadería y crear sus lotes mediante Recepción,
con proveedor, tipo/número/fecha de documento y sucursal. Cada fila corresponde
a un producto y un lote con vencimiento y cantidad. Una recepción permite varios
productos y varios lotes de un mismo producto. La fecha no identifica el lote.

Inventario conserva la consulta de lotes y vencimientos, filtro por producto y
sucursal y comparación de stock físico con cantidades de lotes. Se retiró su
formulario independiente y la escritura que solo creaba el lote sin aumentar
el stock ni registrar un movimiento.

Contrato retirado: POST /api/inventory/lots conserva autenticación, autorización
y validación de origen, pero responde 409 indicando usar Recepción de mercadería.
El frontend ya no lo consume. POST /api/goods-receipts conserva su contrato y
transacción: crea/reutiliza lotes, suma cantidades/stock y registra movimientos
con usuario y documento. Las consultas GET de Inventario se mantienen.

No hay cambios de esquema ni migraciones. No se corrigen automáticamente datos
históricos incoherentes: requieren reconciliación autorizada para no duplicar
existencias. Los ajustes manuales y reservas conservan sus validaciones.

Pruebas: rechazo de creación por la ruta antigua sin cambiar stock, recepción
con productos distintos del mismo nombre y lotes de igual vencimiento, cantidades
independientes, movimientos, idempotencia y regresión de ajustes de inventario.
