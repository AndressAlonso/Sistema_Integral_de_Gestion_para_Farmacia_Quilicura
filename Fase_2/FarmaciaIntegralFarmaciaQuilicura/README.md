# SIGFQ — Login y gestión de usuarios con PostgreSQL

Integración de E1-H1 y el avance E1-H2. Frontend React/TypeScript/Vite en la raíz;
backend FastAPI en backend/. No hay persistencia JSON activa.

Base de integración: origin/feat/login-postgresql, commit 83b5e73.
Avances recuperados: Proyecto, commit 62aa975.
Trabajo local: feature/E1-H1-H2-postgresql. No se hizo push ni merge a las ramas originales.

Ver [informe técnico y contratos](docs/E1-H2.md).

## Base de datos

Se reutiliza el esquema existente en la revisión Alembic 0001_acceso:
usuario_interno, rol, permiso, usuario_rol, rol_permiso, sucursal y sesion_interna.
UUID, relaciones, restricciones y migraciones se conservan. **No se modificó el esquema.**
No se importaron cuentas del JSON ni se restablecieron contraseñas existentes.

La instancia local verificada es PostgreSQL del contenedor sigfq-local-db-1,
expuesto en 127.0.0.1:5433. El backend utiliza DB_HOST, DB_PORT, DB_NAME, DB_USER y
DB_PASSWORD de backend/.env. No se versiona ese archivo.

## Instalación y ejecución — PowerShell

Desde la raíz del frontend:

```powershell
npm.cmd ci
Set-Location backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Conserva backend/.env si ya existe. Solo en un checkout nuevo:

```powershell
Copy-Item .env.example .env
.venv\Scripts\python.exe -c "from dotenv import set_key; import secrets; set_key('.env','JWT_SECRET_KEY',secrets.token_urlsafe(48))"
```

Completa DB_* con la conexión existente. Usa ACCESS_TOKEN_EXPIRE_MINUTES=540.
COOKIE_SECURE=false corresponde únicamente al HTTP local; HTTPS requiere true.

Si el contenedor local existente está detenido, desde cualquier terminal:

```powershell
docker start sigfq-local-db-1
```

Terminal 1, desde backend/:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Terminal 2, desde la raíz del frontend:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

Abrir http://127.0.0.1:5173/login. Usa el mismo host consistentemente para las cookies.
No hace falta ejecutar migraciones para esta integración sobre la base verificada.
No ejecutes compose completo: sus servicios api/web contienen referencias heredadas
que no se corrigieron en este alcance. Se verificó PostgreSQL existente + FastAPI/Vite nativos.

## Probar manualmente

En la instancia local verificada:

- Administrador: interno@farmacia.cl / Local-SIGFQ-2026!
- Operador del seed: operador@farmacia.cl.
- Cuenta inactiva del seed: inactivo@farmacia.cl.

La contraseña del administrador se comprobó por HTTP. No se cambiaron contraseñas.
En otra instancia utiliza las credenciales de su seed; las contraseñas no son universales.

Después del login aparece el menú con Resumen vacío. Usuarios permite listar, buscar,
crear, editar y desactivar. Al crear se exige sucursal y roles existentes.
El resto de las opciones del menú permanece vacío. Los prototipos anteriores siguen
en /admin/branches y /prototypes/inventory, sin funcionalidades nuevas.

Prueba crear una cuenta ficticia, recargar, editar su correo, intentar un duplicado
y desactivarla. Una cuenta activa puede iniciar sesión; tras desactivarla no puede
usar sus sesiones ni iniciar una nueva. El backend comprueba permisos en cada operación.

## Verificaciones

Desde la raíz:

```powershell
npm.cmd run lint
npm.cmd run build
Set-Location backend
.venv\Scripts\python.exe -m ruff check app tests
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Remove-Item Env:SIGFQ_TEST_ROLLBACK
```

Las pruebas requieren DB_* válidos en backend/.env y el esquema existente.
SIGFQ_TEST_ROLLBACK=1 habilita expresamente pruebas sobre una instancia de desarrollo.
Crean datos ficticios dentro de una transacción por caso y revierten todo al terminar;
los commits de los servicios quedan contenidos en SAVEPOINTs. No ejecutan DDL,
migraciones ni seeds sobre tus cuentas. No usar una conexión de producción.
Sin esa variable las pruebas de BD se omiten: un resultado con skips no equivale a
haber verificado la integración PostgreSQL.

Resultado de esta integración: **79 pruebas aprobadas**, build/TypeScript, ESLint
y Ruff correctos. Dos avisos de deprecación de Starlette/httpx y AnyIO.
HTTP real mediante Vite: login/me/usuarios 200, validación 422, logout 204 y sin sesión 401.
No se realizó prueba visual interactiva por ausencia de navegador conectado.

## Límites actuales

- Sesiones persistidas en sesion_interna: sobreviven al reinicio si no expiraron ni se revocaron.
- Límites de login (8 fallos/correo y 40 solicitudes/IP cada 15 minutos) permanecen
  en memoria de un proceso. Ejecutar un solo worker; no se añadió infraestructura distribuida.
- Usuarios con usuarios.gestionar pueden gestionar cuentas; asignar/cambiar roles
  exige además roles.gestionar.
- No hay CRUD de roles, permisos o sucursales; solo lectura de opciones existentes.
- No se añade cambio de contraseña, recuperación, reactivación, auditoría persistente
  ni otras pantallas. No hay tabla de auditoría en el esquema integrado.
- Pendiente revisión de otro integrante antes de integrar en ramas compartidas.
