# SIGFQ - Estado general de la versión actual

## 1. Propósito

Este documento consolida el estado técnico y funcional actual del **Sistema Integral de Gestión para Farmacia Quilicura (SIGFQ)**. Está dirigido a integrantes del equipo, revisores y asistentes de IA que necesiten comprender qué se implementó, qué se corrigió, cómo ejecutar el sistema y qué queda pendiente antes de construir una versión integrada definitiva.

Este README no reemplaza la documentación detallada de cada épica. Su objetivo es ofrecer una visión centralizada y actualizada.

---

## 2. Repositorio, rama y estado de Git

Repositorio remoto:

```text
https://github.com/AndressAlonso/Sistema_Integral_de_Gestion_para_Farmacia_Quilicura.git
```

Rama publicada con la versión documentada aquí:

```text
feat/e6-ecommerce-jesus
```

La rama se encuentra publicada y sincronizada con GitHub. No fue fusionada con `main`.

Commits principales de la rama:

```text
d5ba5e4  fix(E4): hacer reproducible la sincronización de permisos
5ff683c  fix(E3-H4): corregir rangos de alertas de vencimiento
0f6875f  Add files via upload
fcd575d  feat(E6): implementar ecommerce del Sprint 3
```

El commit `0f6875f` agregó la documentación técnica `README_E6_SIGFQ.md`.

### Regla de integración

No fusionar directamente esta rama con `main` sin revisión del equipo. Los archivos compartidos pueden entrar en conflicto con otras épicas o ramas en desarrollo.

---

## 3. Arquitectura y tecnologías

### Arquitectura

El sistema utiliza un **monolito modular**. Cada dominio organiza rutas, servicios, repositorios, esquemas y modelos relacionados.

Flujo general del backend:

```text
Rutas HTTP
→ Servicio de aplicación
→ Repositorio PostgreSQL
→ Modelos SQLAlchemy
→ PostgreSQL
```

### Frontend

- React
- TypeScript
- Vite
- React Router
- CSS
- Vitest
- jsdom
- React Testing Library

### Backend

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Pydantic 2
- PostgreSQL
- Alembic
- JWT
- Argon2 mediante `pwdlib`

### Entorno local

- PostgreSQL ejecutado en Docker.
- FastAPI ejecutado localmente.
- React/Vite ejecutado localmente.

Contenedor local utilizado:

```text
sigfq-local-db-1
```

Puerto PostgreSQL local:

```text
127.0.0.1:5433
```

---

## 4. Estado resumido de las épicas

### Épica 1: identidad, usuarios, roles y sucursales

Estado general: **funcional**.

Incluye:

- Inicio y cierre de sesión del personal interno.
- Sesiones persistidas mediante cookie y JWT.
- Creación, edición, activación y desactivación de usuarios internos.
- Gestión de roles y permisos.
- Asignación de sucursal a usuarios internos.
- Gestión administrativa de sucursales.
- Protección de rutas frontend y endpoints backend.

Rutas principales:

```text
/login
/admin/users
/admin/branches
/session
```

Observación:

La ruta `/session` funciona como página de entrada al panel interno, pero actualmente no tiene un componente de resumen o dashboard. Muestra el encabezado y el menú, dejando el área central vacía.

---

### Épica 2: catálogo, precios y productos con receta

Estado general: **parcialmente funcional**.

Implementado:

- Gestión de categorías.
- Gestión de productos.
- Ingreso y validación de SKU y códigos de barra únicos.
- Actualización de precio base.
- Consulta de historial de precios.
- Imágenes de productos.
- Indicador de producto con receta.
- Restricción de compra online para productos con receta.

Ruta administrativa principal:

```text
/admin/products
```

Pendiente conocido:

#### E2-H3: promociones

La opción de Promociones existe en la navegación, pero todavía no cuenta con una implementación funcional completa que incluya:

- Modelo de promociones.
- Migración.
- Endpoints.
- Motor de descuentos.
- Pantalla funcional.
- Pruebas.

Esta pendiente es conocida por el equipo y otro integrante se encuentra trabajando en ella.

Brecha menor:

- Se validan códigos de barra únicos, pero no se confirmó una función de generación automática de códigos.

---

## 5. Épica 3: gestión de inventario

Estado general: **funcional, con una corrección reciente en E3-H4**.

Ruta principal:

```text
/admin/inventory
```

Prefijo de API:

```text
/api/inventory
```

La interfaz se divide en cuatro pestañas:

1. Disponibilidad.
2. Lotes.
3. Vencimientos.
4. Historial de movimientos de stock.

### E3-H1: inventario por producto y sucursal

Cada registro representa:

```text
Producto + Sucursal
```

Información principal:

- Stock físico.
- Stock reservado.
- Stock disponible.
- Stock mínimo.
- Estado del stock.
- Producto y sucursal.

Fórmula:

```text
stock_disponible = stock_fisico - stock_reservado
```

Reglas:

- El stock físico no puede ser negativo.
- El stock reservado no puede ser negativo.
- El reservado no puede superar al físico.
- El mínimo no puede ser negativo.

Endpoint:

```text
GET /api/inventory
```

Brecha menor conocida:

- No se confirmó un filtro específico por categoría en la pantalla de inventario.

### E3-H2: lotes y FEFO

Incluye:

- Registro y consulta de lotes.
- Número de lote único dentro de cada inventario.
- Fecha de vencimiento.
- Cantidad por lote.
- Estado activo o inactivo.
- Orden por vencimiento.
- Regla FEFO: primero en vencer, primero en salir.

Endpoints:

```text
GET  /api/inventory/lots
GET  /api/inventory/{inventory_id}/lots
POST /api/inventory/lots
```

### E3-H3: stock mínimo

Estados:

```text
DISPONIBLE
BAJO
SIN_STOCK
```

Reglas:

```text
Si stock_disponible = 0 → SIN_STOCK
Si stock_minimo > 0 y stock_disponible <= stock_minimo → BAJO
En cualquier otro caso → DISPONIBLE
```

Endpoint:

```text
PATCH /api/inventory/{inventory_id}/minimum
```

Permiso:

```text
inventario.configurar_minimo
```

### E3-H4: movimientos y alertas de vencimiento

Incluye:

- Modelo `MovimientoInventario`.
- Registro de valores anteriores y resultantes.
- Cambios de stock físico y reservado.
- Usuario, motivo y referencia.
- Consulta por inventario, producto, sucursal, tipo y fecha.

Endpoint:

```text
GET /api/inventory/movements
```

#### Corrección reciente de vencimientos

Se corrigió la clasificación tanto en backend como en frontend.

Clasificación vigente:

```text
Fecha anterior a hoy → Vencido
Vence hoy            → Vencido
1 a 15 días          → Crítico
16 a 30 días         → Próximo a vencer
Más de 30 días       → Sin alerta
```

Casos límite verificados:

```text
-1 días → Vencido
 0 días → Vencido
 1 día  → Crítico
15 días → Crítico
16 días → Próximo a vencer
30 días → Próximo a vencer
31 días → Sin alerta
60 días → Sin alerta
61 días → Sin alerta
```

El código técnico `SEGUIMIENTO` se conserva por compatibilidad, pero se presenta como **Sin alerta** en la interfaz.

Con `include_expired=false`:

- Se excluyen lotes vencidos antes de hoy.
- Se excluyen lotes que vencen hoy.
- Se incluyen lotes que vencen desde mañana.
- Se respeta el período máximo consultado.

Endpoint:

```text
GET /api/inventory/expiration-alerts
```

Pruebas incorporadas:

- 12 pruebas backend aprobadas.
- 8 pruebas frontend aprobadas.
- Build frontend aprobado.

Commit:

```text
5ff683c fix(E3-H4): corregir rangos de alertas de vencimiento
```

Archivos principales de la corrección:

```text
backend/app/inventory/repository.py
backend/tests/test_inventory_expiration_alerts.py
src/pages/e3-inventory/ExpirationAlertsPanel.tsx
src/pages/e3-inventory/ExpirationAlertsPanel.test.tsx
```

Observación futura:

La clasificación continúa implementada tanto en backend como en frontend. Ambos lados usan ahora los mismos límites, pero una mejora futura podría centralizar el cálculo en el backend.

---

## 6. Épica 4: operaciones de inventario y transferencias

Estado general: **funcional**.

La implementación funcional fue realizada previamente por otro integrante. La corrección reciente no reimplementó E4, sino que hizo reproducible la sincronización de sus permisos.

Ruta principal:

```text
/admin/transfers
```

Las siguientes funciones están integradas en la misma pantalla:

### E4-H1: solicitud de transferencia

- Sucursal de origen.
- Sucursal de destino.
- Productos y cantidades.
- Validación de disponibilidad.
- Reserva por lote.
- Asignación FEFO.

Endpoint:

```text
POST /api/transfers
```

### E4-H2: aprobación y rechazo

- Aprobación administrativa.
- Rechazo y liberación de reserva.
- Control de permisos.

Endpoints:

```text
POST /api/transfers/{transfer_id}/approve
POST /api/transfers/{transfer_id}/reject
```

### E4-H3: despacho y recepción

- Despacho desde la sucursal de origen.
- Descuento de stock físico.
- Liberación de reserva.
- Estado en tránsito.
- Confirmación física de recepción.
- Incorporación en la sucursal destino.

Endpoints:

```text
POST /api/transfers/{transfer_id}/dispatch
POST /api/transfers/{transfer_id}/receive
```

### E4-H4: recepción de mercadería

- Proveedor.
- Documento.
- Productos.
- Lotes.
- Fechas de vencimiento.
- Unidades recibidas.
- Incorporación de existencias.

Endpoint:

```text
POST /api/goods-receipts
```

### E4-H5: ajustes manuales

- Selección de inventario y lote.
- Cantidad anterior y final.
- Diferencia calculada.
- Justificación obligatoria.
- Protección de stock reservado.

Endpoint:

```text
POST /api/inventory-adjustments
```

Brecha menor:

- El motivo del ajuste se ingresa como texto libre obligatorio. La planificación original menciona tipos o selección de motivos.

### Permisos reproducibles de E4

Una base nueva configura correctamente los roles base. Sin embargo, una base existente creada antes de E4 podía incorporar los permisos sin completar sus vínculos con roles anteriores.

Se agregó un comando único, aditivo e idempotente:

```powershell
python -m app.role_catalog --reconcile-e4
```

El comando configura:

#### `ADMINISTRADOR`

```text
transferencias.consultar
transferencias.solicitar
transferencias.autorizar
transferencias.despachar
transferencias.recibir
inventario.registrar_entrada
inventario.ajustar
```

#### `ENCARGADO_INVENTARIO`

```text
transferencias.consultar
transferencias.solicitar
transferencias.despachar
transferencias.recibir
inventario.registrar_entrada
inventario.ajustar
```

`ENCARGADO_INVENTARIO` no recibe `transferencias.autorizar`.

Garantías:

- No elimina personalizaciones.
- No reemplaza roles.
- No modifica `usuario_rol`.
- No duplica permisos ni vínculos.
- Puede ejecutarse varias veces.
- No depende del orden de varios seeds.
- Ante un conflicto de autorización no permitido, hace rollback.

Validación realizada:

- 10 pruebas unitarias aprobadas.
- Ruff aprobado.
- Ejecución real idempotente confirmada en PostgreSQL local.
- Resultado real: 0 permisos y 0 vínculos nuevos en una base ya sincronizada.
- Se confirmó que ninguna de las 24 tablas públicas cambió de contenido.

Commit:

```text
d5ba5e4 fix(E4): hacer reproducible la sincronización de permisos
```

Archivos principales:

```text
backend/app/role_catalog.py
backend/tests/test_role_catalog.py
README.md
```

---

## 7. Épica 6: ecommerce

Estado general: **E6-H1 a E6-H4 finalizadas; E6-H5 bloqueada por E7-H1**.

Rutas públicas principales:

```text
/tienda
/tienda/productos/:productId
/tienda/registro
/tienda/iniciar-sesion
/tienda/carrito
/tienda/invitado
/tienda/mis-pedidos
```

### E6-H1: catálogo online

Incluye:

- Catálogo público.
- Búsqueda.
- Ficha de producto.
- Imagen, categoría, descripción y precio.
- Disponibilidad por sucursal.
- Productos con receta visibles, pero sin compra online.

Endpoints:

```text
GET /api/ecommerce/branches
GET /api/ecommerce/products
GET /api/ecommerce/products/{product_id}
GET /api/ecommerce/products/{product_id}/image
```

### E6-H2: clientes y sesiones

Incluye:

- Registro.
- Inicio de sesión.
- Consulta de sesión.
- Cierre de sesión.
- Contraseñas Argon2.
- Sesiones múltiples.
- Correo normalizado y único.
- Separación entre autenticación interna y autenticación de clientes.

Endpoints:

```text
POST /api/customers/register
POST /api/customers/login
GET  /api/customers/me
POST /api/customers/logout
```

Cookies separadas:

```text
Personal interno → sigfq_session
Clientes         → sigfq_customer_session
```

### E6-H3: invitado

Incluye:

- Nombre y correo.
- Validación temporal.
- Revalidación del carrito.
- Datos personales mantenidos solo en memoria.

Endpoint:

```text
POST /api/ecommerce/guest/validate
```

No crea cuentas, pedidos, pagos, reservas ni transferencias.

### E6-H4: carrito y sucursal de retiro

Incluye:

- Agregar y quitar productos.
- Cambiar cantidades.
- Contador.
- Sucursal de retiro.
- Persistencia temporal en `sessionStorage`.
- Revalidación de precios y disponibilidad en backend.
- Cálculo de subtotales y total.
- Disponibilidad local y global.
- Aviso de transferencia cuando corresponde.

Endpoint:

```text
POST /api/ecommerce/cart/validate
```

Límites:

```text
Máximo 50 productos distintos.
Máximo 99 unidades por línea.
```

No se guardan en almacenamiento web:

- Tokens.
- Precios confiables.
- Totales confiables.
- Disponibilidad.
- Nombre o correo del invitado.

### E6-H5: historial de pedidos

Estado: **bloqueada por E7-H1**.

Se preparó:

- Ruta protegida.
- Enlace Mis pedidos.
- Componentes de presentación.
- Tipos del contrato futuro.
- Estado visual de funcionalidad pendiente.

No se implementó:

- Persistencia de pedidos.
- Endpoint real de historial.
- Pedidos ficticios.
- Asociación por coincidencia de correo.

Commit principal:

```text
fcd575d feat(E6): implementar ecommerce del Sprint 3
```

Documentación:

```text
Fase_2/Evidencias Proyecto/Evidencias de sistema/README_E6_SIGFQ.md
```

---

## 8. Migraciones

Migraciones principales existentes:

```text
0001_acceso
0002_catalogo
0003_producto_imagen
0004_inventario
0005_lotes
0006_stock_minimo
0007_movimientos_inventario
0008_recepcion_mercaderia
0009_transferencias
0010_ajustes_inventario
0011_evento_auditoria
0012_clientes
```

Estado esperado de la versión actual:

```text
0012_clientes (head)
```

Comprobación:

```powershell
cd backend
python -m alembic current
python -m alembic heads
```

No ejecutar downgrades o migraciones destructivas sin respaldo y autorización.

---

## 9. Instalación y ejecución local

### 9.1 Clonar y seleccionar la rama

```powershell
git clone https://github.com/AndressAlonso/Sistema_Integral_de_Gestion_para_Farmacia_Quilicura.git SIGFQ-GIT
cd SIGFQ-GIT
git switch feat/e6-ecommerce-jesus
```

### 9.2 Frontend

Desde la carpeta de la aplicación:

```powershell
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Aplicación:

```text
http://127.0.0.1:5173
```

Tienda:

```text
http://127.0.0.1:5173/tienda
```

### 9.3 Backend

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Crear localmente `backend/.env` a partir de `backend/.env.example`. No subir secretos.

Iniciar:

```powershell
python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### 9.4 PostgreSQL y permisos E4

Verificar PostgreSQL:

```powershell
docker ps
docker exec sigfq-local-db-1 pg_isready -U sigfq -d sigfq
```

Después de preparar el esquema y los roles, ejecutar desde `backend`:

```powershell
python -m app.role_catalog --reconcile-e4
```

El comando no crea ni asigna automáticamente un usuario. El usuario debe estar activo y tener asignado `ADMINISTRADOR` o `ENCARGADO_INVENTARIO` según corresponda.

Verificación:

```text
GET /api/auth/me
http://127.0.0.1:5173/admin/transfers
```

---

## 10. Variables de entorno

No subir archivos `.env`.

Ejemplo sin secretos:

```env
JWT_SECRET_KEY=VALOR_LOCAL_PRIVADO
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=540
COOKIE_SECURE=false
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=sigfq
DB_USER=sigfq
DB_PASSWORD=VALOR_LOCAL_PRIVADO
```

No publicar contraseñas ni copiar secretos hacia README, commits o conversaciones del equipo.

---

## 11. Pruebas y validaciones relevantes

### E6

- 7 pruebas frontend aprobadas durante su implementación.
- 111 pruebas backend aprobadas con PostgreSQL y rollback durante su validación.
- Build frontend aprobado.
- ESLint y Ruff aprobados para el alcance revisado.

### Corrección E3-H4

- 12 pruebas backend aprobadas.
- 8 pruebas frontend aprobadas.
- Build frontend aprobado.
- Reglas de límites verificadas.

### Reconciliación E4

- 10 pruebas unitarias aprobadas sin PostgreSQL real.
- Ruff aprobado.
- `git diff --check` aprobado.
- Comando real ejecutado en una base sincronizada.
- Idempotencia confirmada.
- Sin modificaciones efectivas en las 24 tablas públicas.

### Observaciones

Existen advertencias preexistentes fuera del alcance de estas correcciones:

- Ruff `DTZ011` por el uso conservado de `date.today()`.
- ESLint `react-hooks/set-state-in-effect` en el panel de vencimientos.
- Algunas pruebas de integración requieren PostgreSQL de prueba con rollback.

---

## 12. Archivos que no deben subirse

```text
.env
backend/.env
.venv/
backend/.venv/
node_modules/
dist/
*.dump
__pycache__/
.pytest_cache/
.ruff_cache/
logs locales
respaldos de PostgreSQL
```

La regla `*.dump` está incorporada en `.gitignore`.

---

## 13. Archivos compartidos que requieren revisión al integrar

```text
src/routes/AppRouter.tsx
backend/app/main.py
backend/migrations/env.py
backend/app/role_catalog.py
package.json
package-lock.json
README.md
```

Al integrar:

- No reemplazar archivos completos sin comparar cambios.
- Conservar las rutas y routers de todas las épicas.
- Conservar todos los modelos registrados en Alembic.
- Verificar que no existan migraciones duplicadas.
- Ejecutar pruebas y build después de resolver conflictos.

---

## 14. Pendientes para la versión definitiva

### Pendientes funcionales principales

#### E2-H3: promociones

Pendiente conocida y actualmente trabajada por otro integrante.

Falta confirmar:

- Rama y commit.
- Modelo y migración.
- Endpoints.
- Motor de descuentos.
- Interfaz.
- Pruebas.

#### E7-H1 y flujo de pedidos

Falta implementar:

- Creación transaccional de pedidos.
- Detalles históricos del pedido.
- Asociación segura de cliente o invitado.
- Reserva transaccional de stock.
- Asignación de lotes.
- Manejo de concurrencia.
- Estados del pedido.
- Preparación y retiro.
- Pago o integración de pago.
- Liberación o consumo de reservas.

#### E6-H5: historial real

Se completará después de E7-H1. Debe consultar pedidos persistidos reales.

### Brechas y mejoras menores

- Generación automática de códigos de barra no confirmada.
- Filtro de inventario por categoría pendiente.
- Motivos de ajuste tipificados pendientes.
- Dashboard general de `/session` pendiente.
- Posible centralización futura de la clasificación de vencimientos.
- Revisión futura de zonas horarias entre servidor y navegador.
- Paginación del catálogo público.
- Optimización de consultas de inventario y lotes.
- Mayor cobertura frontend.
- Revisión de tamaño del bundle.

### Pendientes de seguridad y despliegue

- Limitación de intentos de registro e inicio de sesión.
- Rate limiting compartido si se usan varios workers.
- Cookies seguras bajo HTTPS.
- Configuración de producción/VPS.
- Revisión de secretos.
- Logging seguro.
- Política de respaldos y recuperación.

### Pendientes documentales

El Sprint Backlog 2 presenta inconsistencias que requieren revisión:

- Fórmulas `#REF!`.
- Duración contradictoria.
- Diferencias entre detalle y resumen.
- Seguimiento diario incompatible con el total final.
- Promociones marcada como terminada antes de su implementación funcional.
- Estados deteriorados en el instructivo.

---

## 15. Guía para crear una versión integrada definitiva

No integrar directamente sobre `main`. Crear una rama específica:

```powershell
git switch main
git pull origin main
git switch -c integration/sigfq-version-definitiva
```

Después:

1. Integrar las ramas aprobadas una por una.
2. Revisar conflictos en archivos compartidos.
3. Confirmar la cadena Alembic.
4. Preparar una base de prueba limpia.
5. Ejecutar migraciones.
6. Ejecutar la sincronización de roles y permisos.
7. Ejecutar `--reconcile-e4`.
8. Ejecutar pruebas backend con rollback.
9. Ejecutar pruebas frontend.
10. Ejecutar build.
11. Probar login interno, inventario, transferencias y ecommerce.
12. Probar pedidos cuando E7 esté disponible.
13. Corregir documentación de los Sprint Backlog.
14. Abrir Pull Request para revisión.
15. Fusionar con `main` solo después de aprobación del equipo.

Ejemplo para incorporar un commit puntual:

```powershell
git cherry-pick HASH_DEL_COMMIT
```

No usar `push --force` sobre ramas compartidas.

---

## 16. Reglas para otra IA o desarrollador

1. No marcar Promociones como terminada sin evidencia funcional.
2. No marcar E6-H5 como terminada antes de E7-H1.
3. No crear pedidos ficticios para completar interfaces.
4. No vincular invitados por coincidencia de correo.
5. No confiar en precios o totales enviados por el navegador.
6. No reservar stock durante la edición del carrito.
7. No mezclar autenticación interna y de clientes.
8. No guardar tokens en almacenamiento web.
9. No modificar directamente stock sin registrar movimiento.
10. No modificar E4 funcional al ajustar permisos.
11. No ejecutar seeds o migraciones sobre datos reales sin respaldo.
12. No subir `.env`, `.dump`, `.venv`, `node_modules` ni `dist`.
13. Mantener cambios de distintas épicas en commits separados.
14. Solicitar revisión antes de integrar archivos compartidos.
15. Mantener `main` intacta hasta que exista aprobación de integración.

---

## 17. Resumen rápido

### Funcional actualmente

```text
Autenticación interna
Usuarios, roles y sucursales
Catálogo administrativo
Precios e historial
Productos con receta
Inventario multisucursal
Lotes y FEFO
Stock mínimo
Movimientos
Alertas de vencimiento corregidas
Transferencias
Recepción de mercadería
Ajustes manuales
Catálogo online
Clientes ecommerce
Carrito
Sucursal de retiro
Continuación como invitado
```

### Pendiente principal

```text
Promociones
Creación real de pedidos
Reserva transaccional para pedidos
Pago
Preparación
Retiro
Historial real de pedidos
Dashboard interno
```

### Rama actual documentada

```text
feat/e6-ecommerce-jesus
```

### Commits actuales

```text
d5ba5e4  Permisos reproducibles de E4
5ff683c  Rangos de vencimiento corregidos
0f6875f  README técnico de E6
fcd575d  Implementación de E6
```

### Estado de `main`

```text
No fusionado desde esta rama.
```
