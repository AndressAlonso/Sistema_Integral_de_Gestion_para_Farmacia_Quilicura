# SIGFQ: autenticación, usuarios y sucursales con PostgreSQL

Sistema Integral de Gestión para Farmacia Quilicura.

Esta versión integra las historias E1-H1, E1-H2, E1-H4 y E1-H5 del Sprint 1:

- Autenticación de usuarios internos.
- Persistencia de sesiones.
- Gestión de usuarios.
- Asignación y reasignación de sucursales.
- Gestión de sucursales.
- Autorización mediante roles y permisos.

El frontend utiliza React, TypeScript y Vite. El backend utiliza FastAPI y PostgreSQL.

No existe persistencia JSON activa.

La gestión de sucursales fue incorporada en la rama `Proyecto` mediante el commit:

```text
53253e0 feat: implementar gestion y asignacion de sucursales
```

Para los contratos técnicos anteriores de autenticación y usuarios, consulta el [informe técnico E1-H2](docs/E1-H2l actual

El Sprint 1 cuenta actualmente con las siguientes funcionalidades:

### E1-H1: autenticación

- Inicio de sesión con correo y contraseña.
- Contraseñas protegidas mediante Argon2id.
- Sesiones persistidas en PostgreSQL.
- Cookie de sesión segura para el entorno configurado.
- Cierre de sesión.
- Consulta de sesión actual mediante `/api/auth/me`.
- Bloqueo de acceso para usuarios inactivos.
- Revocación de sesiones al desactivar usuarios.
- Validación de permisos en cada operación protegida.

### E1-H2: gestión de usuarios

- Listado de usuarios internos.
- Búsqueda y filtros.
- Creación de usuarios.
- Edición de nombre, correo, roles y sucursal.
- Desactivación lógica de usuarios.
- Validación de correos duplicados.
- Asignación de roles existentes.
- Asignación de sucursales activas.
- Protección de operaciones mediante permisos.

### E1-H4: asignación de usuarios a sucursales

- Selección de sucursal al crear un usuario.
- Visualización de la sucursal actual al editar.
- Reasignación hacia otra sucursal activa.
- Exclusión de sucursales inactivas en nuevas asignaciones.
- Rechazo de sucursales inexistentes o inactivas desde FastAPI.
- Conservación del UUID, contraseña, roles y permisos al cambiar de sucursal.
- Persistencia de la reasignación en PostgreSQL.

Cambiar la sucursal de un usuario modifica únicamente su contexto para futuras operaciones.

Los futuros módulos de ventas, cajas, pedidos, inventario y transferencias deberán almacenar directamente la sucursal en la que ocurrió cada operación. No deberán reconstruir el contexto histórico utilizando solamente la sucursal actual del usuario.

### E1-H5: gestión de sucursales

La ruta administrativa `/admin/branches` utiliza información real de PostgreSQL.

Permite:

- Listar sucursales activas e inactivas.
- Crear sucursales.
- Editar código, nombre y dirección.
- Desactivar sucursales.
- Buscar por código, nombre o dirección.
- Filtrar por estado.
- Consultar indicadores de sucursales activas, inactivas, registradas y disponibilidad.
- Mantener visibles las sucursales inactivas para consultas administrativas e históricas.

FastAPI aplica estas validaciones:

- El código de sucursal debe ser único.
- Un código continúa reservado aunque la sucursal esté inactiva.
- Una sucursal con usuarios activos asignados no puede desactivarse.
- Una sucursal inactiva no puede asignarse a usuarios.
- Los campos nulos, vacíos o adicionales son rechazados.
- Las actualizaciones vacías son rechazadas.
- Las operaciones requieren el permiso `sucursales.gestionar`.

El antiguo prototipo `branches.mock.ts` fue eliminado.

## Regla general de desactivación

La implementación utiliza desactivación lógica:

```text
Desactivar no significa eliminar.
```

Cuando un usuario o una sucursal se desactiva:

- El registro permanece en PostgreSQL.
- El UUID se conserva.
- Las relaciones históricas permanecen.
- La entidad deja de estar disponible para nuevas operaciones.
- No se ejecuta una eliminación física.

### Usuario inactivo

Un usuario inactivo:

- Conserva su cuenta e historial.
- No puede iniciar una sesión nueva.
- Tiene sus sesiones vigentes revocadas.
- No puede realizar nuevas operaciones.
- Continúa disponible para reportes y consultas históricas.

### Sucursal inactiva

Una sucursal inactiva:

- Conserva su UUID.
- Conserva su código, nombre y dirección.
- Continúa visible en la administración.
- Mantiene reservado su código.
- No puede asignarse a usuarios nuevos.
- No puede utilizarse para reasignar usuarios.
- No debe utilizarse en nuevas operaciones.
- Continúa disponible para futuras consultas históricas.

Para desactivar una sucursal con usuarios activos, primero se debe:

1. Reasignar los usuarios a otra sucursal activa, o
2. Desactivar los usuarios correspondientes.

No se realiza una reasignación automática.

## Base de datos

Se reutiliza el esquema de la revisión Alembic `0001_acceso`.

Las principales tablas utilizadas son:

```text
usuario_interno
rol
permiso
usuario_rol
rol_permiso
sucursal
sesion_interna
```

Se conservan:

- UUID.
- Relaciones.
- Restricciones.
- Claves foráneas.
- Migraciones existentes.

No se incorporó persistencia JSON.

No se importaron cuentas desde archivos JSON ni se restablecieron contraseñas existentes.

La instancia local verificada utiliza PostgreSQL en el contenedor:

```text
sigfq-local-db-1
```

Puerto local:

```text
127.0.0.1:5433
```

El backend obtiene la conexión desde:

```text
backend/.env
```

Variables utilizadas:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES
COOKIE_SECURE
APP_ENV
DEMO_PASSWORD
```

El archivo `backend/.env` no debe versionarse.

## Datos iniciales locales

El seed local garantiza dos sucursales base en una base nueva.

### Sucursal principal

```text
Código: LOCAL-01
Nombre: Sucursal Quilicura
Dirección: Avenida principal 100, Quilicura
Estado: Activa
```

### Sucursal inactiva de demostración

```text
Código: LOCAL-02
Nombre: Sucursal Norte
Dirección: Avenida norte 200, Quilicura
Estado: Inactiva
```

Los usuarios base se asignan inicialmente a `LOCAL-01`.

El seed garantiza los siguientes permisos:

```text
usuarios.gestionar
roles.gestionar
sucursales.gestionar
inventario.consultar
```

El rol `ADMIN` recibe los permisos administrativos correspondientes.

Si el rol ya existe, el seed agrega únicamente los permisos obligatorios que falten. No elimina permisos personalizados.

El seed:

- Crea los registros base que no existan.
- Conserva usuarios existentes.
- Conserva sucursales existentes.
- Conserva contraseñas existentes.
- Conserva asignaciones existentes.
- No elimina datos manuales.
- Puede ejecutarse nuevamente sin duplicar los registros base.

Los datos manuales almacenados en PostgreSQL local no se incluyen en Git ni se comparten automáticamente con otros integrantes.

## Instalación y ejecución en PowerShell

### 1. Instalar dependencias del frontend

Desde la raíz del proyecto:

```powershell
npm.cmd ci
```

### 2. Preparar el backend

```powershell
Set-Location backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 3. Preparar variables de entorno

Conserva `backend/.env` si ya existe.

Solo en un checkout nuevo:

```powershell
Copy-Item .env.example .env
```

Genera una clave JWT local:

```powershell
.venv\Scripts\python.exe -c "from dotenv import set_key; import secrets; set_key('.env','JWT_SECRET_KEY',secrets.token_urlsafe(48))"
```

Completa las variables `DB_*` con la conexión local existente.

Configuración local recomendada:

```text
ACCESS_TOKEN_EXPIRE_MINUTES=540
COOKIE_SECURE=false
```

`COOKIE_SECURE=false` corresponde únicamente al desarrollo mediante HTTP local.

Un entorno HTTPS debe utilizar:

```text
COOKIE_SECURE=true
```

### 4. Iniciar PostgreSQL

Si el contenedor local existente está detenido:

```powershell
docker start sigfq-local-db-1
```

También puedes comprobar su estado desde la raíz del proyecto:

```powershell
docker compose ps
```

PostgreSQL debe aparecer como `healthy`.

### 5. Iniciar FastAPI

Desde `backend/`:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Swagger estará disponible en:

```text
http://127.0.0.1:8000/docs
```

### 6. Iniciar Vite

En otra terminal, desde la raíz del frontend:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

Abrir:

```text
http://127.0.0.1:5173/login
```

Usa el mismo host de manera consistente para que las cookies funcionen correctamente.

No mezcles en una misma sesión:

```text
localhost
127.0.0.1
```

## Cuentas locales de demostración

En la instancia local preparada mediante el seed:

### Administrador

```text
Correo: interno@farmacia.cl
Contraseña: valor configurado en DEMO_PASSWORD
Rol: ADMIN
Estado: Activo
Sucursal: LOCAL-01
```

### Operador

```text
Correo: operador@farmacia.cl
Contraseña: valor configurado en DEMO_PASSWORD
Rol: OPERADOR
Estado: Activo
Sucursal: LOCAL-01
```

### Usuario inactivo

```text
Correo: inactivo@farmacia.cl
Contraseña: valor configurado en DEMO_PASSWORD
Rol: OPERADOR
Estado: Inactivo
Sucursal: LOCAL-01
```

En la instancia local utilizada durante el desarrollo se verificó:

```text
interno@farmacia.cl
Local-SIGFQ-2026!
```

Esta contraseña es únicamente una referencia del entorno local utilizado durante las pruebas.

En otra instalación se debe utilizar el valor de `DEMO_PASSWORD` configurado para ese entorno. Las contraseñas no son universales y no deben incorporarse al código fuente.

## Pruebas manuales recomendadas

### Autenticación

1. Iniciar sesión con una cuenta activa.
2. Consultar la sesión actual.
3. Cerrar sesión.
4. Intentar iniciar sesión con una cuenta inactiva.
5. Confirmar que una sesión revocada no pueda reutilizarse.

### Usuarios

1. Crear un usuario con una sucursal activa.
2. Recargar la página.
3. Modificar nombre o correo.
4. Intentar utilizar un correo duplicado.
5. Reasignar el usuario a otra sucursal activa.
6. Confirmar que la reasignación permanezca después de recargar.
7. Desactivar el usuario.
8. Confirmar que sus sesiones sean revocadas.
9. Confirmar que el usuario no pueda volver a iniciar sesión.

### Sucursales

1. Crear una sucursal.
2. Recargar la página.
3. Confirmar que el registro permanezca.
4. Editar código, nombre o dirección.
5. Intentar utilizar un código duplicado.
6. Desactivar una sucursal sin usuarios activos.
7. Confirmar que permanezca visible como inactiva.
8. Intentar asignar la sucursal inactiva a un usuario.
9. Intentar desactivar una sucursal con usuarios activos asignados.
10. Confirmar que FastAPI bloquee la operación.

## Verificaciones automatizadas

Desde la raíz:

```powershell
npm.cmd run lint
npm.cmd run build
```

Después:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m ruff check app tests
$env:SIGFQ_TEST_ROLLBACK = "1"
.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
Remove-Item Env:SIGFQ_TEST_ROLLBACK
Set-Location ..
```

Las pruebas requieren:

- Variables `DB_*` válidas en `backend/.env`.
- Pos*greSQL local activo.
- Esquema exi*tente.
- Una*instancia de desarrollo, nunca*producción.

La variable:

```*ext*SIGFQ_TEST_ROLLBACK=1
``*

habil*ta expresamente las pruebas contra*PostgreSQL local.

Las pruebas:

-*Cre*n datos ficticios.
- Trab*jan dentro de transacciones.
* Util*zan puntos*de guardado.
* Revierten los cambios al terminar*cada caso.
- No ejecutan migracion*s.
- No ejecutan DDL.
- No*ejecutan el seed.
- No*modific*n permanentemente las cuentas loca*es.

Sin `SIG*Q_TEST_ROLLBACK=1`, las*pruebas de PostgreSQL se omiten. U* resultado con pruebas omitidas no*equivale a una validación completa*

## Resultado de*verificaciones

La integración act*al fue validada con:

- *21 pruebas automatizadas aprobadas*
- 37 pruebas específicas de gesti*n de sucursales.
- 5*pruebas*nuevas para asignación y reasignac*ón de usuarios.
- Ruff sin errores*
- TypeScript aprobado.
- Build de*producción aprobado.
- Validación *anual de creación, edición y desac*ivación de sucursales.
- Validació* manual de persistencia después de*recargar.
- Validación manual de r*asignación de usuarios.
- Validaci*n de códigos duplicados.
- Validac*ón de sucursales activas, inactiva* e inexistentes.
- Validación de r*vocación de sesiones.

Pytest mues*ra dos advertencias de deprecación*correspondientes a Starlette y Any*O. Estas advertencias no represent*n fallos funcionales del SIGFQ.

#* Límites*actuales y decisiones pendientes

*## Protección del último administr*dor

Todavía falta decidir si se d*be impedir:

- Des*ctivar al último administrador act*vo.
- Q*itarle su rol administrativo.
- Q*itarle los permisos de*gestión.
- De*ar el*sistema sin una cuenta capaz de ad*inistrar usuarios, roles y sucursa*es.

Esta protección requiere*una*regla formal del equipo, valid*ción transaccional en*FastAPI y pruebas automatizadas.

*## Reactivación de usuarios

No ex*ste una opción de reactivación de *suarios.

El equipo debe definir:
*- Quién puede reactivar.
- Qué per*iso se requiere.
- Si debe comprob*rse que la sucursal continúe activ*.
- Si deben revisarse roles y per*isos.
- Si se requiere restablecer*la contraseña.
- Cómo se registra *a acción en auditoría.

### Reacti*ación de sucursales

No existe*una opción de reactivación de sucu*sales.

El equipo debe definir:

-*Quién puede reactivar.
- Qué permi*o se requiere.
- Si se conserva el*mismo código.
- Qué valid*ciones operativas deben realizarse*
- Si*se debe confirmar la dirección.
- *ómo se registra la acción en audit*ría.

Mientras no exista*esta regla, las sucursales inactiv*s permanecen inactivas y sus códig*s continúan reservados.

### Desac*ivación de todos los usuarios

Act*almente se pueden*desactivar todos los usuarios de u*a sucursal.

El equipo debe decidi* si una sucursal activa*deberá mantener al menos un*usuario activo asignado.

También *ebe definirse la protección del úl*imo administrador activo del siste*a.

### Eliminación física

No exi*te eliminación física de usuarios *i sucursales.

Mientras no exista *na regla formal, se mantiene única*ente la desactivación lógica.

Ant*s de permitir una eliminación físi*a deben evaluarse:

- Claves forán*as.
- Sesiones.
- Ventas.
- Cajas.*- Inventario.
- Pedidos.
- Transfe*encias.
- Movimientos.
- Auditoría*.
- Reportes históricos.

### Caja* pedidos, transferencias e inventa*io

Cuando existan los módulos cor*espondientes, deberá definirse si *na sucursal puede desactivarse mie*tras tenga:

- Cajas abiertas.
- P*didos pendientes.
- Transferencias*activas.
- Stock físico.
- Stock r*servado.
- Retiros pendientes.
- R*cepciones sin finalizar.
- Otras o*eraciones en curso.

Estas validac*ones deberán implementarse en Fast*PI, no solamente en React.

### Au*itoría

No existe todavía auditorí* persistente.

Cuando se implement*, deberían registrarse:

-*Desactivación o eventual reactivac*ón de usuarios.
- Cambio de sucurs*l.
- Cambio de roles y permisos.
-*Desactivación o eventual reactivac*ón de sucursales.
- Usuario*responsable de la acción.
- Fecha*y hora.
* Estado anterior.
- Estado nuevo.
* Motivo, cuando corresponda.

### *tros límites

- Los límites*de login permanecen en memoria de *n solo proceso.
- Se recomienda ut*lizar un solo worker hasta incorpo*ar almacenamiento distribuido para*estos límites.
- No existe todavía*cambio de contraseña.
- No existe *ecuperación de contraseña.
- No ex*ste CRUD administrativo de roles y*permisos desde la interfaz.
- Las*pantallas de inventario continúan *iendo prototipos hasta implementar*sus módulos reales.

## Regla para*módulos futuros

Cada servicio que*util*ce una sucursal en una nueva opera*ión debe validar:

```text
sucursa*.activa == true
```

No se debe de*ender únicamente de que React ocul*e una sucursal inactiva.

Esta reg*a deberá*aplicarse en los futuros módulos d*:

- Punto*de*venta.
- Caja.
- Inventario.
- Ped*dos.
- Transferencias.
- Recepción*
- Retiro.
- Ajustes.
- Scanner.

*# Flujo de trabajo recomendado

Pa*a nuevas funcionalidades:

1. Crea* una rama específica.
2. Implement*r un cambio de alcance acotado.
3.*Agregar pruebas.
4. Ejecutar*Ruff, lint y build.
5.*Crear un commit descriptivo.
6. Su*ir la rama.
7.*Crear un*Pull Request hacia `Proyecto`.
8.*Documentar las*reglas implementadas y pendientes.*9. Integrar solamente cuando no ex*stan conflictos.
````*
