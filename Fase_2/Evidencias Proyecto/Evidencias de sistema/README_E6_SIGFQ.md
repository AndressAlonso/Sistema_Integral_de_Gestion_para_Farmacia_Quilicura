# SIGFQ - Resumen de implementación de la Épica 6

## 1. Propósito de este documento

Este documento entrega el contexto técnico y funcional necesario para que otra IA, desarrollador o integrante del equipo pueda continuar trabajando en el proyecto **Sistema Integral de Gestión para Farmacia Quilicura (SIGFQ)** sin perder el estado actual de la implementación.

El documento describe:

- Qué se implementó en la Épica 6.
- Qué historias están terminadas.
- Qué funcionalidad permanece bloqueada.
- Qué archivos y módulos fueron incorporados.
- Cómo ejecutar el sistema localmente.
- Cómo funciona la autenticación de clientes y personal interno.
- Cómo funciona el catálogo, carrito e invitado.
- Qué migración se agregó.
- Qué pruebas fueron ejecutadas.
- Qué observaciones técnicas siguen pendientes.
- Dónde está publicada la rama de trabajo.

> **Importante:** E6-H1, E6-H2, E6-H3 y E6-H4 están implementadas. E6-H5 tiene una base frontend preparada, pero permanece bloqueada hasta que E7-H1 implemente pedidos online reales.

---

## 2. Repositorio y rama

Repositorio remoto:

```text
https://github.com/AndressAlonso/Sistema_Integral_de_Gestion_para_Farmacia_Quilicura.git
```

Rama con la implementación de la Épica 6:

```text
feat/e6-ecommerce-jesus
```

Commit principal:

```text
fcd575d feat(E6): implementar ecommerce del Sprint 3
```

La rama fue publicada en GitHub, pero **no se fusionó con `main`**. La rama `main` debe permanecer sin cambios hasta que el equipo decida integrar E6.

Para obtener la rama:

```powershell
git fetch origin
git switch feat/e6-ecommerce-jesus
```

Para incorporar el commit en otra rama sin modificar `main`:

```powershell
git fetch origin
git switch NOMBRE_DE_LA_RAMA_DESTINO
git cherry-pick fcd575d
```

Antes de usar `cherry-pick`, se recomienda revisar manualmente los archivos compartidos indicados en la sección de integración.

---

## 3. Tecnologías principales

### Frontend

- React
- TypeScript
- Vite
- React Router
- Vitest
- jsdom
- React Testing Library

### Backend

- FastAPI
- Python 3.12
- SQLAlchemy
- Pydantic
- PostgreSQL
- Alembic
- Argon2 mediante `pwdlib`
- JWT

### Infraestructura local

- PostgreSQL 18 en Docker.
- FastAPI ejecutado localmente desde PowerShell.
- React/Vite ejecutado localmente desde PowerShell.
- Docker Compose completo no es la modalidad vigente de ejecución.

---

## 4. Estado de las historias de la Épica 6

### E6-H1 - Catálogo online y disponibilidad por sucursal

**Estado: finalizada.**

Incluye:

- Catálogo público sin necesidad de iniciar sesión.
- Búsqueda de productos.
- Selección y consulta por sucursal.
- Ficha pública de producto.
- Imagen pública del producto.
- Precio actual.
- Categoría y descripción.
- Disponibilidad informativa por sucursal.
- Productos con receta visibles.
- Productos con receta identificados como compra presencial.
- Productos con receta sin acción para agregarlos al carrito.

Rutas frontend:

```text
/tienda
/tienda/productos/:productId
```

Endpoints principales:

```text
GET /api/ecommerce/branches
GET /api/ecommerce/products
GET /api/ecommerce/products/{product_id}
GET /api/ecommerce/products/{product_id}/image
```

Regla informativa original de disponibilidad:

```text
stock_fisico - stock_reservado
```

La disponibilidad del catálogo es informativa y no garantiza por sí sola que todas las unidades puedan comprarse en línea.

---

### E6-H2 - Registro e inicio de sesión de clientes

**Estado: finalizada.**

Incluye:

- Registro de clientes.
- Inicio de sesión de clientes.
- Consulta de sesión.
- Cierre de sesión.
- Sesiones múltiples por cliente.
- Contraseñas almacenadas con Argon2.
- Correo normalizado y único entre clientes.
- Estado compartido de sesión en React.
- Encabezado dinámico con nombre y cierre de sesión.
- Separación completa entre clientes y personal interno.

Rutas frontend:

```text
/tienda/registro
/tienda/iniciar-sesion
```

Endpoints:

```text
POST /api/customers/register
POST /api/customers/login
GET  /api/customers/me
POST /api/customers/logout
```

#### Separación de autenticaciones

Personal interno:

```text
Entidad: UsuarioInterno
Cookie: sigfq_session
Audiencia JWT: sigfq-internal
Ruta frontend: /login
```

Clientes:

```text
Entidad: Cliente
Cookie: sigfq_customer_session
Audiencia JWT: sigfq-customers
Ruta frontend: /tienda/iniciar-sesion
```

Reglas importantes:

- Un error 401 de cliente no elimina la cookie interna.
- El logout de cliente no cierra la sesión del personal.
- Un token interno no funciona como token de cliente.
- Un token de cliente no funciona como token interno.
- No se almacenan tokens en `localStorage` ni `sessionStorage`.
- La sesión compartida se mantiene en memoria mediante `CustomerSessionProvider`.

---

### E6-H3 - Continuación como invitado

**Estado: finalizada dentro del alcance aprobado.**

Incluye:

- Continuación desde el carrito sin una cuenta de cliente.
- Solicitud exclusiva de nombre y correo electrónico.
- Validación temporal del invitado.
- Revalidación completa del carrito.
- Revisión temporal de producto, precio, cantidad, total y sucursal.

Ruta frontend:

```text
/tienda/invitado
```

Endpoint:

```text
POST /api/ecommerce/guest/validate
```

Reglas importantes:

- No solicita contraseña.
- No solicita teléfono.
- No solicita dirección.
- No crea una cuenta automáticamente.
- No consulta si el correo corresponde a una cuenta existente.
- No vincula pedidos por coincidencia de correo.
- Nombre y correo permanecen únicamente en memoria de React.
- Nombre y correo desaparecen al recargar.
- El carrito y la sucursal sí permanecen porque pertenecen al estado del carrito.
- No crea pedidos, pagos, reservas, movimientos ni transferencias.

---

### E6-H4 - Carrito y sucursal de retiro

**Estado: finalizada.**

Incluye:

- Agregar productos habilitados para venta online.
- Cambiar cantidades.
- Quitar productos.
- Contador del carrito.
- Selección de sucursal de retiro.
- Persistencia temporal del carrito en `sessionStorage`.
- Revalidación de precios y disponibilidad en backend.
- Cálculo de subtotales y total con `Decimal`.
- Disponibilidad local y global.
- Aviso de transferencia cuando la sucursal seleccionada no tiene stock local suficiente, pero sí existe stock global.

Ruta frontend:

```text
/tienda/carrito
```

Endpoint:

```text
POST /api/ecommerce/cart/validate
```

Contenido permitido en `sessionStorage`:

```json
{
  "version": 1,
  "items": [
    {
      "product_id": "uuid",
      "quantity": 1
    }
  ],
  "pickup_branch_id": "uuid-o-null"
}
```

No se almacenan en `sessionStorage`:

- Tokens.
- Precios.
- Totales.
- Disponibilidad.
- Nombre del invitado.
- Correo del invitado.
- Datos personales.

Límites implementados:

```text
Máximo 50 productos distintos.
Máximo 99 unidades por línea.
```

Reglas importantes:

- El navegador no envía precios ni totales confiables.
- El backend consulta `precio_actual` y recalcula todo.
- Productos con receta se rechazan en frontend y backend.
- Productos inactivos o no publicados se rechazan.
- Una sucursal inactiva no puede usarse para retiro.
- La validación no descuenta stock.
- La validación no crea reservas.
- La validación no crea movimientos.
- La validación no crea transferencias.
- La validación no crea pedidos.
- “Requiere transferencia” no promete retiro inmediato.

---

### E6-H5 - Historial de pedidos online

**Estado: bloqueada por E7-H1. No finalizada.**

Se preparó únicamente la base frontend:

- Ruta protegida para clientes.
- Enlace “Mis pedidos” visible solo con sesión de cliente.
- Componentes de presentación.
- Tipos del contrato futuro.
- Servicio futuro no invocado.
- Estados visuales para sesión requerida y funcionalidad pendiente.

Ruta preparada:

```text
/tienda/mis-pedidos
```

Con sesión se muestra:

```text
El historial estará disponible cuando se habilite la creación de pedidos online.
```

Sin sesión se muestra acceso requerido.

No se implementó:

- Endpoint temporal de historial.
- Lista ficticia de pedidos.
- Pedidos simulados.
- Estado vacío falso.
- Persistencia de pedidos.
- Asociación automática por correo.

E6-H5 debe integrarse únicamente después de que E7-H1 implemente pedidos online reales.

---

## 5. Estructura principal de archivos

### Frontend de E6

```text
src/pages/e6-ecommerce/
├── components/
│   ├── AddToCartButton.tsx
│   ├── BranchSelector.tsx
│   ├── CartContinuation.tsx
│   ├── CartItem.tsx
│   ├── CartProvider.tsx
│   ├── CustomerAuthForm.tsx
│   ├── CustomerSessionProvider.tsx
│   ├── GuestForm.tsx
│   ├── GuestProvider.tsx
│   ├── OrderHistoryItem.tsx
│   ├── OrderHistoryList.tsx
│   ├── OrderHistoryState.tsx
│   ├── ProductCard.tsx
│   └── PublicHeader.tsx
├── hooks/
│   ├── useCart.ts
│   ├── useCustomerSession.ts
│   └── useGuest.ts
├── layouts/
│   └── EcommerceLayout.tsx
├── pages/
│   ├── CartPage.tsx
│   ├── CustomerLoginPage.tsx
│   ├── CustomerRegisterPage.tsx
│   ├── GuestContinuationPage.tsx
│   ├── OnlineCatalogPage.tsx
│   ├── OrderHistoryPage.tsx
│   └── ProductDetailPage.tsx
├── services/
│   ├── cart.api.ts
│   ├── catalog.api.ts
│   ├── customers.api.ts
│   ├── guest.api.ts
│   └── order-history.api.ts
├── tests/
│   └── customer-session.test.tsx
├── types/
│   ├── cart.ts
│   ├── catalog.ts
│   ├── customer.ts
│   ├── guest.ts
│   └── order-history.ts
├── cart.css
├── customer-auth.css
├── ecommerce.css
├── guest.css
├── order-history.css
├── public-header.css
└── E6-H5.md
```

### Backend de clientes

```text
backend/app/customers/
├── __init__.py
├── models.py
├── repository.py
├── routes.py
├── schemas.py
├── security.py
├── service.py
└── sessions.py
```

### Backend ecommerce

```text
backend/app/ecommerce/
├── __init__.py
├── repository.py
├── routes.py
├── schemas.py
├── service.py
├── cart/
│   ├── __init__.py
│   ├── repository.py
│   ├── routes.py
│   ├── schemas.py
│   └── service.py
└── guest/
    ├── __init__.py
    ├── routes.py
    └── schemas.py
```

### Pruebas backend de E6

```text
backend/tests/test_e6_catalog.py
backend/tests/test_e6_customers.py
backend/tests/test_e6_cart.py
backend/tests/test_e6_guest.py
```

### Migración

```text
backend/migrations/versions/0012_clientes.py
```

### Documentación

```text
docs/E6-H1-catalogo-online.md
src/pages/e6-ecommerce/E6-H5.md
```

---

## 6. Migración 0012_clientes

La migración depende de:

```text
0011_evento_auditoria
```

Crea las tablas:

```text
cliente
sesion_cliente
```

### Tabla `cliente`

Campos principales:

- `id` UUID.
- `nombre` obligatorio.
- `correo` normalizado y único.
- `password_hash` obligatorio.
- `activo` booleano.
- `creado_en` con zona horaria.

### Tabla `sesion_cliente`

Campos principales:

- `id` UUID.
- `cliente_id` FK hacia `cliente`.
- `token_hash` único.
- `creada_en`.
- `expira_en`.
- `revocada_en` nullable.

`cliente_id` tiene índice normal, no único. Esto permite varias sesiones por cliente.

El downgrade elimina primero `sesion_cliente` y luego `cliente`. Ejecutar el downgrade elimina los datos almacenados en esas tablas.

La base local utilizada durante el desarrollo quedó en:

```text
0012_clientes (head)
```

---

## 7. Ejecución local

### 7.1 PostgreSQL

Contenedor esperado:

```text
sigfq-local-db-1
```

Comprobar:

```powershell
docker ps
docker exec sigfq-local-db-1 pg_isready -U sigfq -d sigfq
```

Resultado esperado:

```text
/var/run/postgresql:5432 - accepting connections
```

Puerto local:

```text
127.0.0.1:5433 -> 5432
```

### 7.2 Backend

Desde la carpeta del proyecto:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Si no se activa el entorno, puede ejecutarse directamente:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### 7.3 Frontend

Desde la raíz del proyecto:

```powershell
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Aplicación:

```text
http://127.0.0.1:5173
```

Catálogo:

```text
http://127.0.0.1:5173/tienda
```

---

## 8. Variables de entorno

No se deben subir archivos `.env`.

El backend necesita, entre otras, las variables locales equivalentes a:

```env
JWT_SECRET_KEY=VALOR_PRIVADO
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=540
COOKIE_SECURE=false
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=sigfq
DB_USER=sigfq
DB_PASSWORD=VALOR_PRIVADO
```

No copiar secretos desde conversaciones, documentación o commits. Generar valores locales propios cuando corresponda.

---

## 9. Pruebas y validaciones realizadas

### Frontend

- 7 pruebas frontend de regresión aprobadas.
- Build de Vite aprobado.
- ESLint aprobado para los archivos de E6.
- Prueba de sesión compartida aprobada.
- Logout sincronizado sin recargar.

### Backend

- 111 pruebas aprobadas con PostgreSQL real y rollback.
- 1 prueba deseleccionada relacionada con generación SQL de migración.
- Ruff aprobado en las pruebas E6.
- Compilación Python aprobada.

### Casos validados

- Catálogo público.
- Productos activos y publicados.
- Producto con receta excluido del carrito.
- Registro de cliente.
- Correo duplicado normalizado.
- Login válido e inválido.
- Sesiones múltiples.
- Logout de cliente sin afectar sesión interna.
- Carrito persistente.
- Cantidades máximas.
- Revalidación de precio.
- Disponibilidad local y global.
- Aviso de transferencia.
- Sucursal inactiva.
- Invitado en memoria.
- Ausencia de escrituras en inventario durante validaciones.
- E6-H5 sin solicitudes a endpoints inexistentes.

Para pruebas backend seguras:

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
python -m pytest tests/test_e6_catalog.py tests/test_e6_customers.py tests/test_e6_cart.py tests/test_e6_guest.py tests/test_auth.py -q
```

No ejecutar la prueba concurrente de E4 sobre una base local con datos importantes.

---

## 10. Diseño y experiencia de usuario

Se incorporó el logo existente:

```text
src/assets/logo-farmacia-quilicura.jpg
```

Se mantuvo una identidad visual basada en:

- Blanco.
- Verde.
- Morado.
- Gris claro.
- Bordes suaves.
- Sombras discretas.
- Diseño adaptable.

El encabezado público muestra según el estado:

### Sin sesión

- Catálogo.
- Carrito.
- Crear cuenta.
- Iniciar sesión.
- Acceso interno separado.

### Con sesión

- Catálogo.
- Carrito.
- Nombre del cliente.
- Mis pedidos.
- Cerrar sesión.
- Acceso interno separado.

“Mis pedidos” aparece únicamente con una sesión válida de cliente.

---

## 11. Archivos compartidos que requieren atención al integrar

Los principales archivos que podrían entrar en conflicto con otras épicas son:

```text
src/routes/AppRouter.tsx
backend/app/main.py
backend/migrations/env.py
package.json
package-lock.json
```

Al integrar con E5 u otra rama:

- No reemplazar estos archivos completos sin revisar.
- Conservar rutas y routers de ambas épicas.
- Conservar todos los modelos registrados en Alembic.
- Revisar que la cadena de migraciones siga siendo lineal.
- Revisar que no exista otra migración con identificador `0012`.
- Ejecutar build y pruebas después de resolver conflictos.

La rama E6 se puede integrar mediante `cherry-pick` del commit `fcd575d`, pero los conflictos en archivos compartidos deben resolverse manualmente.

---

## 12. Observaciones técnicas pendientes

No impiden conservar la rama E6, pero deben considerarse:

### Pendiente antes de despliegue público

- Limitación de intentos de registro.
- Limitador compartido si se usan varios workers.
- Cookies seguras bajo HTTPS.
- Configuración real de VPS.
- Revisión de secretos.
- Logging seguro.

### Mejoras futuras

- Paginación del catálogo.
- Optimización de recorridos de inventarios y lotes.
- Evitar validación duplicada al agregar al carrito.
- Limpieza menor de CSS sin uso.
- Pruebas frontend adicionales.
- División del bundle por rutas si el proyecto crece.

### Preexistente y fuera de E6

- Compose completo contiene referencias desactualizadas.
- README general del repositorio está desactualizado.
- Existen observaciones globales de lint en E3.
- La prueba concurrente de E4 puede dejar datos si se interrumpe.

---

## 13. Archivos que no deben subirse

El `.gitignore` incluye `*.dump`.

No subir:

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

Los respaldos locales utilizados durante el desarrollo fueron movidos fuera del proyecto.

---

## 14. Reglas para continuar el desarrollo

Una nueva IA o desarrollador debe respetar lo siguiente:

1. No marcar E6-H5 como finalizada hasta que exista E7-H1.
2. No crear pedidos ficticios.
3. No vincular invitados a clientes por coincidencia de correo.
4. No confiar en precios o totales enviados por el navegador.
5. No reservar stock durante la edición del carrito.
6. No mezclar autenticación de clientes con personal interno.
7. No guardar tokens en almacenamiento web.
8. No modificar E5 sin autorización.
9. No ejecutar migraciones destructivas sin respaldo y revisión.
10. No ejecutar seeds sobre datos reales sin autorización.
11. Mantener el frontend de E6 en `src/pages/e6-ecommerce/`.
12. Mantener `customers` separado de `UsuarioInterno`.
13. Mantener el historial bloqueado hasta la persistencia real de pedidos.
14. Solicitar aprobación antes de modificar archivos compartidos.

---

## 15. Próximo paso recomendado

El siguiente paso técnico es E7-H1:

```text
Creación transaccional de pedidos online y reserva de stock.
```

E7-H1 deberá:

- Volver a validar carrito, precio y disponibilidad.
- Crear un pedido real.
- Crear detalles históricos del pedido.
- Asociar el cliente desde la sesión, no desde el navegador.
- Mantener `cliente_id = null` para invitados.
- Reservar stock transaccionalmente.
- Asignar lotes mediante una regla definida, por ejemplo FEFO.
- Manejar concurrencia.
- Dejar datos históricos de productos, precios y sucursal.
- Proporcionar el endpoint real que E6-H5 consultará.

Solo después de E7-H1 debe completarse E6-H5.

---

## 16. Resumen para otra IA

El ecommerce SIGFQ está implementado en la rama:

```text
feat/e6-ecommerce-jesus
```

Commit:

```text
fcd575d
```

Estado:

```text
E6-H1: finalizada
E6-H2: finalizada
E6-H3: finalizada
E6-H4: finalizada
E6-H5: bloqueada por E7-H1
```

La rama no está mezclada con `main`. Cualquier integración debe realizarse en otra rama, revisando manualmente los archivos compartidos y la cadena Alembic.
