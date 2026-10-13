# Instalar o actualizar SIGFQ

Estas instrucciones corresponden a la rama **`Proyecto`**, con creación de pedidos y reservas de E7-H1. Los pagos Flow y el proceso de preparación y retiro todavía están pendientes.

Trabaja desde la carpeta que contiene `package.json`:

```text
Fase_2/Evidencias Proyecto/Evidencias de sistema/FarmaciaIntegralFarmaciaQuilicura
```

El frontend utiliza `src` y el backend está en `backend`. No hay una carpeta `frontend` separada.

## Requisitos

- Node.js compatible con las dependencias del proyecto: 20.19.x o una versión desde 22.12.0 que satisfaga sus requisitos.
- Python 3.12 y PowerShell.
- PostgreSQL disponible. Para la instalación local mediante contenedor, Docker Desktop y Docker Compose.
- Git, si se actualizará mediante `git pull`.

## Actualizar una instalación existente

1. Detén las terminales de Vite y FastAPI.
2. Si utilizas Git, actualiza la rama desde la raíz del repositorio:

```powershell
git switch Proyecto
git pull --ff-only origin Proyecto
```

Si Git informa cambios locales o divergencia, conserva y resuelve esos cambios antes de continuar. No uses `reset` para descartarlos.

Si utilizas una descarga ZIP, selecciona primero la rama `Proyecto` en GitHub. Conserva tu configuración privada y los datos locales al reemplazar el código de la aplicación.

3. Conserva `.env`, `backend/.env`, la base PostgreSQL y los archivos locales de imágenes. No sustituyas tu configuración por los ejemplos ni generes otra clave JWT al actualizar.
4. Desde la carpeta de la aplicación, instala las dependencias del frontend:

```powershell
npm.cmd ci
```

5. Inicia PostgreSQL. Para la base definida en `compose.yaml`, desde la carpeta de la aplicación:

```powershell
docker compose up -d db
docker compose ps db
```

Este procedimiento ejecuta FastAPI y Vite en terminales locales; utiliza Compose para el servicio `db`.

6. Desde `backend`, actualiza dependencias y aplica todas las migraciones:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
```

La revisión actual es **`0018_pedidos_reservas`**. Incorpora pedidos online, detalles y reservas por lote después de `0017_promociones`. Las migraciones conservan los datos existentes; no recrean la base. No utilices `alembic stamp` para saltarlas ni elimines el volumen de PostgreSQL.

7. Inicia los servicios como se indica en la sección de arranque. Las cuentas existentes conservan sus contraseñas y asignaciones.

## Primera instalación

### Obtener el código

Selecciona la rama `Proyecto` al descargar el ZIP o clónala:

```powershell
git clone --branch Proyecto https://github.com/AndressAlonso/Sistema_Integral_de_Gestion_para_Farmacia_Quilicura.git
```

Entra en la carpeta de la aplicación indicada al comienzo, no solamente en la raíz del repositorio.

### Preparar PostgreSQL

Desde la carpeta de la aplicación:

```powershell
Copy-Item .env.example .env
```

Edita el archivo nuevo y configura `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `POSTGRES_PORT`. Los valores del ejemplo son únicamente para desarrollo; utiliza una contraseña propia.

Con Docker Desktop iniciado:

```powershell
docker compose up -d db
docker compose ps db
```

El puerto local predeterminado es `5433`. Si ya tienes PostgreSQL, utiliza tu instancia y configura su conexión en el backend.

### Preparar FastAPI

```powershell
Set-Location backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Completa `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` en este `backend/.env` con la misma conexión de PostgreSQL. Para el contenedor local, el host es `127.0.0.1` y el puerto predeterminado es `5433`.

Genera y guarda una clave JWT local solo para esta instalación nueva:

```powershell
.venv\Scripts\python.exe -c "from dotenv import set_key; import secrets; set_key('.env', 'JWT_SECRET_KEY', secrets.token_urlsafe(48))"
```

Mantén orígenes explícitos en `CORS_ORIGINS`. `COOKIE_SECURE=false` corresponde al desarrollo mediante HTTP local; un despliegue HTTPS debe configurar `COOKIE_SECURE=true`.

Aplica las migraciones:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

### Crear las cuentas de demostración

Solo para una base nueva de desarrollo, desde `backend`:

```powershell
$demoPassword = Read-Host "Contraseña para las cuentas de demostración, mínimo 12 caracteres" -AsSecureString
$env:DEMO_PASSWORD = [System.Net.NetworkCredential]::new('', $demoPassword).Password
$env:APP_ENV = "local"
try {
    .venv\Scripts\python.exe -m app.seed
} finally {
    Remove-Item Env:DEMO_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue
    Remove-Variable demoPassword -ErrorAction SilentlyContinue
}
```

El seed crea las cuentas faltantes descritas en el [README](../README.md), sus roles y las sucursales iniciales. No carga los productos, ventas ni datos manuales de otro integrante. No restablece contraseñas ni asignaciones existentes.

En una base nueva, crea productos y registra mercadería desde la aplicación para probar inventario y ventas.

### Preparar el frontend

Regresa a la carpeta de la aplicación:

```powershell
Set-Location ..
npm.cmd ci
```

## Arrancar la aplicación

En una terminal, desde `backend`:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

En otra terminal, desde la carpeta que contiene `package.json`:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

| Acceso | Dirección |
|---|---|
| Tienda, página inicial | `http://127.0.0.1:5173/tienda` |
| Personal interno | `http://127.0.0.1:5173/login` |
| Documentación de la API | `http://127.0.0.1:8000/docs` |

Usa el mismo host durante la sesión: no alternes `localhost` y `127.0.0.1`. Tras el acceso interno, abre un módulo implementado desde el menú; Resumen todavía no tiene contenido.

## Reconciliación de permisos E4

Con las migraciones aplicadas y la conexión configurada, desde `backend`:

```powershell
.venv\Scripts\python.exe -m app.role_catalog --reconcile-e4
```

Este comando incorpora solo los vínculos obligatorios de E4 que falten y conserva permisos adicionales y asignaciones de usuarios. No modifica contraseñas, no crea usuarios y no ejecuta migraciones.

| Permiso | Administrador | Encargado de inventario |
|---|---|---|
| `transferencias.consultar` | Sí | Sí |
| `transferencias.solicitar` | Sí | Sí |
| `transferencias.autorizar` | Sí | No |
| `transferencias.despachar` | Sí | Sí |
| `transferencias.recibir` | Sí | Sí |
| `inventario.registrar_entrada` | Sí | Sí |
| `inventario.ajustar` | Sí | Sí |

Si el rol Encargado de inventario ya tiene `transferencias.autorizar`, el comando informa el conflicto y revierte la transacción. Revisa esa asignación antes de repetirlo.

Los permisos efectivos de un usuario son la unión de sus roles. Un usuario que también sea Administrador podrá autorizar por ese rol. Recarga la interfaz después de revisar permisos; el backend consulta las asignaciones actuales.

## Verificar una actualización

Desde la carpeta de la aplicación:

```powershell
npm.cmd run lint
npx.cmd vitest run --environment jsdom
npm.cmd run build
```

Para las pruebas del backend, utiliza una **base de pruebas independiente**, con las variables `DB_*` configuradas para ella y las migraciones aplicadas. No actives la suite completa sobre una base de trabajo o producción: hay pruebas de concurrencia con conexiones independientes.

Desde `backend`, una vez conectada exclusivamente la base de pruebas:

```powershell
$env:SIGFQ_TEST_ROLLBACK = "1"
$env:SIGFQ_TEST_ISOLATED = "1"
try {
    .venv\Scripts\python.exe -m alembic upgrade head
    .venv\Scripts\python.exe -m pytest tests -q
} finally {
    Remove-Item Env:SIGFQ_TEST_ROLLBACK -ErrorAction SilentlyContinue
    Remove-Item Env:SIGFQ_TEST_ISOLATED -ErrorAction SilentlyContinue
}
```

Los indicadores de pruebas no cambian por sí solos la base de destino: comprueba `DB_*` antes de ejecutar. Un resultado con pruebas omitidas no equivale a la validación completa.

En la copia publicada el 13 de octubre de 2026 pasaron **66 pruebas del frontend y 488 del backend**, con todas las migraciones en una base temporal aislada. Lint del frontend, TypeScript y compilación aprobaron. Ruff general conserva avisos previos del backend; el build informa el tamaño del paquete y pytest una deprecación de Starlette.

## Límites actuales

- E7-H1 crea pedidos y reservas, con datos de invitado e historial privado del cliente.
- El pedido queda Pendiente de pago. No se procesa Flow, no se genera una venta online y no está listo para retiro.
- La cancelación y liberación automática de reservas por pago no confirmado corresponde a E7-H2 y todavía no se ejecuta.
- Transferencias automáticas de pedidos, preparación, correo y retiro QR corresponden a E7-H3 a E7-H6.
- Resumen/dashboard, Reportes y Auditoría siguen pendientes de E9. La gestión interna de Pedidos Online se completará con las historias siguientes de E7.
- El aviso de stock bajo funciona en Inventario; mostrarlo en el dashboard está pendiente.
- El escáner móvil requiere validación con un dispositivo real.

Consulta el [README](../README.md) para las reglas operativas y el alcance completo de esta versión.
