# E9-H1 y E9-H3 — Dashboard operativo

## Acceso

Ruta web: `/admin/dashboard`. Resumen redirige al dashboard para Administrador
y Socio; otros usuarios conservan accesos a sus secciones autorizadas.
La API `GET /api/dashboard` exige sesión interna activa y uno de estos roles.
No requiere nuevas tablas ni migraciones.

## Indicadores y fuentes

- **Ventas registradas:** suma de `Venta.total` (descuentos ya aplicados), POS
  y online. No se suman pedidos ni pagos aparte; se evita duplicar la venta web.
- **Cantidad:** registros de venta del período.
- **Ticket promedio:** importe registrado / cantidad; cero cuando no hay ventas.
- **Reversas registradas:** anulaciones y devoluciones de `ReversaVenta`,
  por fecha de la reversa y sucursal de la venta original.
- **Balance:** ventas del período menos reversas del período. Puede ser negativo
  si se devuelven ventas anteriores. No representa utilidad ni saldo de caja.
- **Gráficos:** importe diario, distribución por medio de pago, ventas por
  sucursal y cinco productos con más unidades vendidas. Estos gráficos y el
  ticket promedio muestran ventas antes de reversas.
- **Stock bajo:** registros producto/sucursal de productos activos donde
  físico menos reservado es menor o igual al mínimo. No cuenta un mismo producto
  de dos sucursales como una sola alerta. Muestra hasta cinco prioridades.
- **Próximos a vencer:** lotes activos con unidades, que vencen en 1–30 días
  desde hoy en Chile. 1–15 días se destacan como críticos. Se cuentan aparte
  los lotes vencidos (fecha menor o igual a hoy); no se mezclan con los próximos.
- **Movimientos:** cantidad de registros y variación física/reservada por tipo
  dentro del período y sucursal seleccionados.

Los pagos online reembolsados, contracargados o en revisión no son una reversa
POS automática. El dashboard refleja las ventas y reversas efectivamente
registradas; esos pagos requieren conciliación del módulo de pagos. Esta
limitación se explica en «¿Cómo se calcula?».

## Filtros

Sucursales como botones visibles, sin selector desplegable; Todas consolida.
Períodos: Hoy, últimos 7 días incluyendo hoy, Este mes hasta hoy y Personalizado.
Las selecciones se aplican inmediatamente; el rango personalizado aplica sus dos
fechas juntas. Dashboard permite hasta 366 días. Las fechas incluyen ambos
extremos, interpretados en America/Santiago, con límites UTC para la consulta.
El backend valida fechas, UUID, rol y sesión.

Auditoría reutiliza los mismos controles, conserva Todo el historial y sus
consultas existentes. Cambiar filtros reinicia la paginación a uno.

**Inventario actual:** no se presenta una foto histórica inexistente. Stock y
vencimientos responden a sucursal y se identifican como «Ahora». El período
se aplica a ventas, reversas, movimientos y auditoría. El UI muestra esta
distinción explícitamente.

## Interacción y verificación

- Curva consultable por mouse, toque y teclado; flechas recorren los días.
- Barras de sucursal aplican ese filtro; botones de medio de pago muestran
  proporciones. Alertas alternan stock / vencimiento sin navegar.
- Estados de carga, error con reintento y ausencia de datos. Se descartan
  respuestas tardías de consultas anteriores.
- Diseño adaptable, foco visible y animaciones que respetan movimiento reducido.
- Pruebas frontend cubren filtros, validaciones, permisos, respuestas tardías,
  errores, vacíos, gráficos y auditoría.
- Pruebas backend de agregación usan tablas efímeras reducidas y conversión
  chilena equivalente: no sustituyen comprobar migraciones en PostgreSQL.
  `test_dashboard_postgres.py` verifica fechas y sucursal sobre PostgreSQL
  mediante el fixture local con rollback (`SIGFQ_TEST_ROLLBACK=1`).

No se despliega al VPS ni se alteran datos para probar la interfaz.
