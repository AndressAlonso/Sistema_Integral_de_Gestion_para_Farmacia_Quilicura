# E5 — POS, caja y reversas

Rama: `Proyecto`. Implementación local; no se hizo commit ni push.

## Alcance implementado

- H1: búsqueda por nombre, SKU, UUID y código de barras; carrito con cantidades
  enteras; stock vendible de la sucursal autenticada. Lector USB como teclado.
- H2: cálculo de precios en backend, promociones por producto/categoría y
  vigencia; elegir el menor precio sin acumular. Precio base si no hay promoción.
  Los descuentos enviados por un cliente se rechazan. Proveedor de demostración
  opcional; la persistencia definitiva de promociones E2-H3 sigue pendiente.
- H5: caja por usuario/sucursal, apertura con cero, unicidad de caja abierta,
  cierre con medios de pago, ventas, ticket promedio, efectivo esperado,
  contado y diferencia; reembolsos separados y cierre histórico persistido.
- H3: cobro con un medio de pago, caja abierta, revalidación de precio/stock,
  venta, detalle, lotes y movimiento de salida en una transacción PostgreSQL.
- H4: comprobante automático y reconsulta imprimible; precios, nombres de
  productos y promociones históricos; leyenda sin validez tributaria.
- H6: consulta de ventas, devolución parcial y anulación completa; solo
  administrador con permiso; motivo, condición por lote, cantidades acumuladas,
  usuario y fecha. Se conserva la venta original.

## Decisiones confirmadas y límites

El usuario confirmó que las devoluciones aptas aumentan stock y dejan movimiento;
las no aptas se registran sin aumentar stock vendible. Se vuelve al **lote y
sucursal originales** de la venta, identificando el lote vendido. El backend
rechaza reingreso vendible si el lote está vencido/inactivo o el producto inactivo.
No se implementa un almacén de cuarentena en esta épica.

También confirmó devolver después de cerrar la caja original, registrando el
reembolso en la caja actualmente abierta del administrador. Se aprobó su FK.
El cierre anterior permanece intacto. La implementación conserva el medio de pago
original para el reembolso; si es efectivo exige saldo esperado suficiente.
Las operaciones bancarias se realizan fuera del sistema: registrar no ejecuta
un cargo ni un abono bancario.

Dinero: Decimal/NUMERIC(14,2), JSON con cadenas, redondeo HALF_UP a dos decimales,
en continuidad con la precisión del catálogo. Un medio por venta, sin pagos mixtos.
Los nombres de cajero/sucursal se consultan desde sus entidades actuales; las
referencias UUID se conservan, pero sus nombres no tienen snapshot histórico.

La app móvil E8 no está conectada. El botón «Vincular sesión» abre un aviso de integración pendiente y muestra cajero/sucursal. No genera códigos ni tokens, ni crea una sesión móvil. Se retiró por completo la simulación entre pestañas. La vinculación real requiere acordar e implementar el contrato con Flutter y backend; no está terminada por tener este botón.

Decisión confirmada: las ventas nuevas permiten Efectivo o Tarjeta (Débito o
Crédito). `POST /api/pos/sales` rechaza TRANSFERENCIA con 422 para nuevas ventas;
se conserva la consulta/reintento idempotente de ventas históricas y sus totales.
No se modificó el esquema ni sus restricciones. Esto reemplaza para ventas
nuevas los cuatro medios descritos originalmente en E5-H3.

Las imágenes existentes del catálogo se muestran en búsqueda, carrito,
confirmación y comprobante mediante `GET /api/pos/products/{id}/image`, con
autenticación y permiso `pos.operar`. Son imágenes actuales, no una copia
histórica; si faltan se muestra el marcador «Sin imagen».

Prueba manual: abrir POS y pulsar «Vincular sesión»: debe aparecer el estado sin dispositivo vinculado y permitir cerrar el aviso. Confirmar foto y Efectivo/Tarjeta en el cobro.

## Archivos creados

| Ruta relativa a la aplicación | Propósito |
|---|---|
| backend/app/pos/__init__.py | Módulo E5 |
| backend/app/pos/schemas.py | Entradas estrictas: cantidades, importes, confirmaciones |
| backend/app/pos/pricing.py | Mejor promoción y fixture opcional de desarrollo |
| backend/app/pos/repository.py | Sesiones PostgreSQL, bloqueos y consultas de caja/venta |
| backend/app/pos/service.py | Reglas y transacciones de venta, caja y reversas |
| backend/app/pos/routes.py | Contratos HTTP, autenticación y errores |
| backend/app/pos/seed.py | Permisos E5 sin sobrescribir personalizaciones posteriores |
| backend/migrations/versions/0012_pos_caja.py | H1/H3/H4/H5: caja, venta, detalle y lotes |
| backend/migrations/versions/0013_reversas_venta.py | H6: reversa y detalle con caja del reembolso |
| backend/tests/test_pos.py | Aceptación API real con rollback y cálculo de promociones |
| backend/tests/test_pos_concurrency.py | Conexiones independientes y carreras de caja/venta |
| src/pages/e5-pos/pos.api.ts | Contratos TypeScript y cliente HTTP |
| src/pages/e5-pos/PosPage.tsx | Búsqueda, carrito, cobro y comprobante |
| src/pages/e5-pos/CashPage.tsx | Apertura, resumen y cierre |
| src/pages/e5-pos/SalesDialog.tsx | Consultar venta y registrar reversas |
| src/pages/e5-pos/pos.css | Estilos aislados, responsive, modales 98% e impresión |
| docs/propuesta-E5-pos-caja.md | Propuesta aprobada y trazabilidad de decisiones |
| docs/E5-pos-caja.md | Este informe |

## Archivos existentes modificados

- `backend/app/models.py`: seis entidades E5 en la metadata compartida.
- `backend/app/main.py`: registrar repositorio/router y errores de validación E5.
- `backend/app/config.py`, `backend/.env.example`: promoción demo restringida a desarrollo.
- `backend/app/role_catalog.py`: permisos `pos.operar`, `caja.operar`, `ventas.reversar`.
- `backend/app/branches/repository.py`, `routes.py`: impedir desactivar sucursal con caja abierta
  y ocultar eliminación si conserva historial de cajas.
- `src/routes/AppRouter.tsx`: conectar las rutas existentes POS y Caja.
- `src/layouts/adminNavigation.ts`: visibilidad por permisos reales E5.
- `src/services/http.ts`: opción explícita para mostrar errores de negocio 400/409/422;
  su comportamiento predeterminado para otros módulos se conserva.

No se cambió la implementación de Inventario, Catálogo o Transferencias.
Estos archivos compartidos deben revisarse al integrar trabajo de otros integrantes.

## Base de datos

Antes: `0011_evento_auditoria`. Ahora: `0013_reversas_venta`.
Nuevas tablas: `sesion_caja`, `venta`, `venta_detalle`, `venta_lote`,
`reversa_venta`, `reversa_venta_detalle`. No se alteraron columnas de tablas previas.
UUID, claves foráneas RESTRICT, cantidades positivas, importes y medios válidos,
producto único por venta, lote único por asignación, caja abierta única por usuario/sucursal.

Se reutilizan producto, código de barras, sucursal, usuario, inventario, lotes,
reservas de transferencias y movimientos de inventario. No se agrega stock a
productos inexistentes ni se crea una tabla provisional de promociones.

Se creó respaldo local antes de migrar en
`backend/data/backups/sigfq-pre-e5.dump` (ignorado por Git).
Las migraciones anteriores permanecen intactas.

## Flujo y seguridad

React captura productos/cantidades → POST /api/pos/quote → backend verifica
permiso/sucursal → consulta stock físico, reservas y lotes no vencidos → calcula
mejor precio → devuelve totales y versión → usuario confirma pago → POST
/api/pos/sales → bloquea caja, productos e inventario → revalida → inserta venta,
detalles/asignaciones → descuenta lotes/stock → registra movimiento → commit →
comprobante imprimible.

Las consultas de precio no reservan stock. La venta verifica otra vez en la
transacción. FEFO respeta reservas por lote de transferencias. Disponible se
limita por físico menos reservado y por unidades vendibles de lotes.

Reintentos conservan request_id UUID y hash de contenido. Una misma solicitud
no vuelve a descontar/reintegrar. Un ID repetido con distinto contenido genera
409. El navegador conserva solicitudes pendientes en sessionStorage por usuario;
si pierde la respuesta, permite recuperar/reintentar antes de otra venta.
No se almacena contraseña ni token en ese almacenamiento.

Se reutiliza autenticación E1, cookie HttpOnly, comprobación de origen y permisos
del backend. Precios, descuentos, roles y sucursal no se confían a React.
Caja y cierre comparten bloqueo; la versión del resumen evita cerrar indicadores
desactualizados. Las devoluciones se serializan sobre la venta original.

## API

Todas las rutas requieren sesión. Montos como cadenas decimales, IDs UUID,
fechas ISO 8601. Errores: 401 sesión, 403 permiso, 404 recurso/alcance,
409 conflicto o estado, 422 campos, 500 mensaje genérico.

| Método/ruta | Entrada | Salida / permiso |
|---|---|---|
| GET /api/pos/products?q= | Nombre/SKU/UUID/código | products: id, name, sku, price, available, requires_prescription / pos.operar |
| POST /api/pos/quote | items:[{product_id,quantity}] | items,subtotal,discount,total,version / pos.operar |
| POST /api/pos/sales | request_id,items,payment,quote_version | Comprobante / pos.operar y caja.operar |
| GET /api/pos/sales | Ninguna | Últimas 50 autorizadas / pos.operar |
| GET /api/pos/sales/{id}/receipt | ID | Comprobante y lotes vendidos/retornables / pos.operar |
| GET /api/cash/current | Ninguna | Caja propia o null / caja.operar |
| POST /api/cash/open | request_id,initial_amount | Caja / caja.operar |
| GET /api/cash/{id}/summary | ID | Indicadores, refunds, version / caja.operar |
| POST /api/cash/{id}/close | counted_cash,summary_version | Caja con resumen persistido / caja.operar |
| POST /api/pos/sales/{id}/reversals | request_id,kind,reason,items:[{product_id,sale_lot_id,quantity,restock,condition}] | id,amount / ADMINISTRADOR + ventas.reversar + caja.operar |

Medios: EFECTIVO, DEBITO, CREDITO, TRANSFERENCIA. Tipos: DEVOLUCION, ANULACION.
Anulación exige totalidad y ninguna devolución previa. El resto son devoluciones.
El contrato detallado de entradas está disponible en `/docs` de FastAPI.

## Ejecución en PowerShell

Desde la raíz del repositorio:

```powershell
cd 'Fase_2\Evidencias Proyecto\Evidencias de sistema\FarmaciaIntegralFarmaciaQuilicura'
npm.cmd ci
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Completar .env con secretos privados y DB_* antes de iniciar.
# Iniciar Docker Desktop y el PostgreSQL existente antes de continuar.
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.pos.seed
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Otra terminal desde la carpeta de la aplicación:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

Pruebas desde backend:

```powershell
$env:SIGFQ_TEST_ROLLBACK='1'
.venv/Scripts/python.exe -m pytest tests/test_pos.py tests/test_pos_concurrency.py -q
.venv/Scripts/python.exe -m alembic check
.venv/Scripts/python.exe -m ruff check app/pos tests/test_pos.py tests/test_pos_concurrency.py
```

Los casos normales usan rollback. Los de concurrencia crean fixtures UUID
exclusivos en conexiones independientes y los eliminan en finally. Usar solo BD local de desarrollo.

Desde la aplicación: `npm.cmd run build`; lint focalizado:
`./node_modules/.bin/eslint.cmd src/pages/e5-pos src/services/http.ts src/routes/AppRouter.tsx src/layouts/adminNavigation.ts`.

## Prueba manual

1. Abrir http://127.0.0.1:5173 e iniciar sesión con usuario existente activo de
   rol Administrador o Vendedor/Cajero. No se creó ni cambió una contraseña.
2. En Caja, abrir con 0; otra apertura para el mismo usuario/sucursal debe rechazarse.
3. En POS, buscar un producto de la sucursal con stock y lotes futuros.
   Los productos sin unidades vendibles aparecen deshabilitados.
4. Agregar/modificar/quitar unidades; revisar total calculado por backend.
5. Confirmar pago; comprobar salida única en movimientos y comprobante imprimible.
6. En Ventas, consultar comprobante. Como administrador, seleccionar lote,
   cantidad, condición, motivo y confirmar la devolución con caja abierta.
7. Verificar que solo las unidades aptas vuelven a stock; consultar reembolso en caja.
8. Cerrar con efectivo contado; comprobar totales y diferencia.

Promoción demo opcional: en `.env` poner `APP_ENVIRONMENT=development` y
`POS_DEMO_PRODUCT_ID=UUID_DEL_PRODUCTO_DE_PRUEBA`; reiniciar FastAPI. Aplica 20%
de 2026 a 2030 solo a ese producto y muestra el nombre de demostración.
Quitar POS_DEMO_PRODUCT_ID para volver exclusivamente al precio base.

## Verificación y pendientes reales

Resultados ejecutados sobre PostgreSQL local:

| Verificación | Resultado |
|---|---|
| E5 + test_branches + test_branch_activation | 76 passed; incluye los 27 casos E5 |
| Suite general ejecutada antes de ampliar los últimos casos E5 | 288 passed, 1 failed preexistente |
| Ruff sobre módulo E5, configuración, main, modelos y pruebas nuevas | Correcto |
| TypeScript y build Vite | Correcto |
| ESLint en archivos frontend modificados | Correcto |
| ESLint general | 4 errores preexistentes en Inventario |
| alembic check | No new upgrade operations detected |
| FastAPI en ejecución: /openapi.json | 200 |
| POS y caja sin sesión | 401 |
| git diff --check | Sin errores de whitespace |

Casos E5: apertura cero/duplicada, búsqueda/stock cero, lotes vencidos, FEFO,
reservas de transferencias, venta sin caja, precios cambiados, rechazo de descuentos
manuales, rollback ante fallo intermedio, reintento idéntico/conflictivo, historial
del comprobante, cierre desactualizado, medios de pago, diferencia de caja,
devolución apta/no apta, cantidades acumuladas, anulación completa, producto/lote
vencido, administrador obligatorio, devolución contra caja nueva, promoción por
categoría/vigencia/mejor precio, demo aplicada desde API y bloqueada en producción.
Las carreras cubren dos cajeros con cajas diferentes, últimas unidades, misma venta,
apertura repetida y venta contra cierre.

Fallo previo conservado: `test_legacy_lot_cannot_duplicate_received_units` en
`test_goods_receipts.py`; espera 409 pero el endpoint original de lotes devuelve 201.
Inventario conserva la implementación que el usuario pidió no reemplazar. Sus
errores de lint son `react-hooks/set-state-in-effect` en ExpirationAlertsPanel,
InventoryMovementHistory y LotPanel (dos). No son fallos introducidos por E5.

El entorno informa una deprecación Starlette/httpx; las pruebas funcionan.
`npm audit` también informó una vulnerabilidad alta preexistente en la dependencia
transitiva `source-map-js` (<1.2.2, GHSA-68fv-2mgg-jv7q). No se actualizaron
dependencias compartidas en este cambio; queda pendiente su revisión antes de producción.
No había navegador conectado disponible en CUA, por lo que falta inspección visual
interactiva. No se afirma validación visual ni finalización para producción.

Para los otros integrantes: actualizar la rama una vez integrado el PR, ejecutar
`alembic upgrade head` y `python -m app.pos.seed`; las dependencias de producción
no cambiaron. Revisar especialmente modelos, main, permisos, navegación y cliente
HTTP compartidos. No se modificaron las ramas de otros integrantes.

Pendientes: integrar E2-H3 y E8 cuando existan, revisión visual, revisión de otro
integrante y commit/PR. La rama local estaba un commit detrás de origin/Proyecto
(eliminación documental de .gitkeep) al iniciar; no se hizo pull ni push.
No confundir registrar pago/reembolso con cobro bancario automático ni emisión tributaria.
