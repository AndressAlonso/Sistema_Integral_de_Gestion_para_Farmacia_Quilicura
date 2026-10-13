# SIGFQ — instalación y estado actual

Sistema Integral de Gestión para Farmacia Quilicura. Plataforma web con React, TypeScript y Vite, backend FastAPI y base de datos PostgreSQL centralizada.

La rama de integración es **`Proyecto`**. La aplicación se encuentra en:

```text
Fase_2/Evidencias Proyecto/Evidencias de sistema/FarmaciaIntegralFarmaciaQuilicura
```

Para instalar o actualizar, sigue la [guía de instalación y actualización](docs/ACTUALIZACION_PROYECTO.md). La carpeta de la aplicación contiene `package.json`, `src` y `backend`; no utiliza una carpeta `frontend` separada.

## Alcance implementado

La versión incorpora los flujos operativos de E1 a E6 y la creación de pedidos con reserva de **E7-H1**. El dashboard y los pagos, preparación y retiro de las historias siguientes permanecen pendientes.

| Área | Funcionalidades disponibles |
|---|---|
| Acceso y usuarios | Inicio y cierre de sesión, cuentas internas, roles, permisos y asignación de sucursal. Administración de roles y permisos desde la interfaz. |
| Sucursales | Creación, edición, activación y desactivación controlada. Conservación de relaciones e historial. |
| Catálogo | Productos, categorías, códigos de barras, imágenes, publicación online y condición de receta. Precio base con historial de cambios. |
| Promociones | Porcentaje o precio final fijo, por producto o categoría. Se aplica la promoción vigente que produzca el menor precio final, sin acumular descuentos. |
| Inventario | Stock físico, reservado y disponible; lotes, vencimientos, FEFO, movimientos y aviso de stock bajo por producto y sucursal. |
| Transferencias | Solicitud con reserva, autorización, rechazo antes del despacho, salida física, tránsito y recepción. Validación de conflictos del lote destino. |
| Mercadería y ajustes | Entradas con respaldo documental y ajustes de cantidades con motivo, valor anterior, valor nuevo y responsable. |
| POS y caja | Ventas con promociones, comprobantes internos, efectivo, débito, crédito y transferencia. Apertura, cierre, indicadores, anulaciones y devoluciones. |
| Tienda online | Catálogo, disponibilidad, registro de clientes, compra como invitado, carrito, sucursal de retiro e historial privado de pedidos web. |
| E7-H1 | Pedido persistido con reserva por lote, datos del invitado asociados al pedido, reintentos sin duplicación y protección transaccional contra sobreventa. |

## Reglas de los flujos actuales

- **Disponible = físico − reservado.** Crear un pedido o solicitar una transferencia reserva unidades sin realizar todavía una salida física.
- Al despachar una transferencia se descuenta el físico del origen y se libera su reserva. Al recibir se incorpora el stock al destino.
- Los lotes vencidos no se utilizan para ventas ni salidas. Habilitar un lote no cambia su vencimiento ni agrega unidades.
- Un retiro de unidades vencidas se registra como ajuste con motivo; el lote y su historial se conservan.
- Los productos sujetos a receta pueden consultarse online, pero su compra es presencial. El backend valida la restricción.
- El POS requiere una caja abierta. El pago presencial por transferencia se registra después de comprobar el abono; no verifica automáticamente el banco y no aumenta el efectivo esperado.
- Los descuentos de las ventas se muestran en POS, comprobantes y caja. El descuento ya está incluido en el total y no se resta otra vez al cerrar caja.
- Las operaciones importantes muestran su efecto antes del botón final de confirmación. Editar los datos de una recepción o devolución exige confirmar nuevamente.
- Comprar como invitado requiere nombre y correo. No crea una cuenta ni incorpora el pedido al historial de otro cliente por coincidencia de correo.
- Los pedidos nuevos quedan **Pendientes de pago**. En esta etapa no generan una venta online, un cobro ni una salida física.

## Presentación y navegación

- La ruta inicial abre la tienda: `http://127.0.0.1:5173/tienda`.
- El acceso del personal está en `http://127.0.0.1:5173/login`.
- Los listados permiten elegir 15, 25, 50 o 100 filas por página.
- Los listados administrativos adaptan su presentación al ancho disponible.
- Crear y editar promociones utiliza una misma ventana con resumen y confirmación.
- Las ventanas de categoría, cambio de precio y sucursal se ajustan al contenido.
- El formulario de usuario muestra resúmenes de los roles y permite desplegar sus permisos. Puede asignarse más de un rol; sus permisos se suman.
- Las opciones Resumen, Pedidos Online, Reportes y Auditoría del menú interno todavía no tienen contenido. El historial del cliente en **Mis pedidos** sí funciona. Después del acceso interno, utiliza el menú para abrir un módulo implementado.

## Base de datos y actualización

Las migraciones forman parte del repositorio. La revisión actual es **`0018_pedidos_reservas`**, posterior a `0017_promociones`.

Desde `backend`, con PostgreSQL iniciado y `backend/.env` configurado:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

La actualización incorpora tablas de pedidos, detalles y reservas. Conserva los registros existentes; no requiere recrear la base ni borrar el volumen de PostgreSQL.

Los archivos `.env`, contraseñas, bases de datos, imágenes cargadas por usuarios, entornos virtuales y dependencias instaladas no se comparten mediante Git. Cada instalación conserva su configuración y sus datos locales.

## Instalación local y cuentas iniciales

La guía vinculada explica la preparación de Node.js, Python 3.12, PostgreSQL, variables de entorno, migraciones y arranque de ambos servicios.

Solo en una base nueva de desarrollo, `app.seed` crea las cuentas que falten utilizando una contraseña propia configurada mediante `DEMO_PASSWORD`:

| Cuenta | Rol inicial | Estado |
|---|---|---|
| `interno@farmacia.cl` | Administrador | Activo |
| `operador@farmacia.cl` | Encargado de inventario | Activo |
| `inactivo@farmacia.cl` | Encargado de inventario | Inactivo |

Las cuentas iniciales se asignan a `LOCAL-01`. El seed crea también `LOCAL-02` como sucursal inactiva de demostración. Las instalaciones existentes pueden tener nombres, asignaciones y estados diferentes.

Las contraseñas no son universales. El seed conserva las cuentas, contraseñas y asignaciones ya existentes; no debe utilizarse para restablecerlas.

## Funcionalidades pendientes

- **E7-H2:** integración Flow, confirmación del pago, venta online única, cancelación y liberación de reservas por pago no confirmado.
- **E7-H3 a E7-H6:** transferencias automáticas asociadas a pedidos, preparación, notificaciones, QR y registro de retiro.
- **E9:** dashboard, reportes y consulta administrativa de auditoría. El aviso de stock bajo funciona en Inventario; su integración al dashboard está pendiente.
- La integración del escáner móvil requiere verificación con un dispositivo real.
- Cambio y recuperación de contraseña no están incluidos en esta versión.

**Las reservas de pedidos pendientes no se liberan automáticamente por un timeout de pago en esta versión.** Esa gestión corresponde a E7-H2. Crear un pedido todavía no equivale a una compra pagada ni lista para retiro.

La regla final para el retiro futuro es que el QR de un pedido pagado y listo para retiro no vence por el paso del tiempo.

## Verificación de esta versión

Antes de publicar la actualización del 13 de octubre de 2026 se verificó la copia preparada para GitHub:

- Instalación del frontend desde `package-lock.json` con `npm.cmd ci`.
- Lint del frontend, TypeScript y compilación aprobados.
- **66 pruebas del frontend aprobadas.**
- Todas las migraciones aplicadas y **488 pruebas del backend aprobadas** en una base temporal aislada, eliminada al terminar.
- Revisión de los archivos publicados para excluir credenciales, datos locales, cachés y herramientas de trabajo.

La revisión general de Ruff del backend conserva avisos previos de orden de importaciones y uso de fechas; no se considera completamente limpia. La compilación mantiene un aviso de tamaño del paquete y pytest informa una advertencia de deprecación de Starlette. Estos avisos no fueron fallos de las pruebas indicadas.

## Reconciliación de permisos E4

Para instalaciones existentes que necesiten incorporar permisos obligatorios de E4, consulta la sección correspondiente de la [guía de actualización](docs/ACTUALIZACION_PROYECTO.md). La reconciliación no reemplaza las migraciones ni restablece contraseñas.
