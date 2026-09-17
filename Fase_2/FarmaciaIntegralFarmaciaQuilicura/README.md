# SIGFQ — E1-H1 y E1-H2: acceso y usuarios internos

Implementación de E1-H1 sobre el frontend existente React + TypeScript + Vite.
El login mantiene su diseño y utiliza FastAPI para autenticar usuarios activos.
E1-H2 agrega gestión de usuarios con JSON temporal, autorización de administrador
y menú compartido. Ver [implementación, contratos y pruebas de E1-H2](docs/E1-H2.md).

## Estructura inspeccionada

- Frontend en la raíz: `src/main.tsx` → `App.tsx` → `routes/AppRouter.tsx`.
- React Router ya instalado; rutas `/login`, `/admin/branches` y `/admin/inventory`.
- Login en `src/pages/e1-access-users-branches/auth/LoginPage.tsx`.
- Sucursales en la carpeta hermana `branches/`, con datos y acciones de demostración.
- Inventario en `src/pages/e3-inventory/`, también preexistente.
- Identidad visual en `src/assets/`, estilos globales en `src/styles/global.css`
  y estilos de Sprint 1 en `src/pages/e1-access-users-branches/sprint-one.css`.
- `static/`, `.vscode/`, configuración TypeScript, ESLint, Vite y dependencias npm existentes.
- Antes de E1-H1, `backend/` estaba vacío. No había modelo User, ORM, base de datos,
  variables de autenticación, servicio API ni infraestructura de pruebas frontend.

## Flujo implementado

1. El usuario ingresa correo y contraseña en el formulario existente.
2. La validación HTML comprueba campos obligatorios y formato básico de correo.
3. `LoginPage.submit` evita envíos duplicados y activa el estado de carga.
4. `login.api.ts` envía JSON a `POST /api/auth/login` mediante `fetch`.
5. Durante desarrollo, Vite reenvía `/api` a FastAPI en `127.0.0.1:8000`.
6. FastAPI valida el cuerpo, aplica los límites de intentos y busca el correo normalizado en el repositorio local.
7. Argon2 verifica la contraseña; luego se exige `is_active=true`.
8. Si el correo no existe, igualmente se realiza una verificación Argon2 auxiliar.
9. Antes de alcanzar el límite, cualquier credencial incorrecta o cuenta inactiva recibe el mismo 401 y mensaje:
   **Correo o contraseña incorrectos.** No se revela qué dato falló.
10. Si el acceso es válido, el backend firma un JWT y lo entrega mediante una cookie
    `sigfq_session` HttpOnly, SameSite=Strict, con duración limitada y ruta `/api`.
11. El JSON contiene solamente `{ user: { id, email }, expires_at }`.
    El token no se expone a JavaScript, localStorage ni sessionStorage.
12. React navega a `/session`: contenido vacío dentro del menú compartido, con «Cerrar sesión».
13. `RequireAuth` consulta `GET /api/auth/me` antes de mostrar las rutas internas.
    FastAPI comprueba firma, algoritmo, emisor, destinatario y expiración del JWT,
    comprueba que el identificador de sesión siga registrado, busca nuevamente al usuario y confirma que siga activo.
14. Al recargar se repite `/me`; la cookie la conserva y envía el navegador.
    También se revalida al recuperar el foco y cada 60 segundos.
15. Al expirar, un temporizador inutiliza el acceso en React. Un 401/403 de `/me`
    devuelve al login; el backend elimina la cookie en los 401.
    Una falla de conexión oculta el contenido y permite reintentar la validación.
16. «Cerrar sesión» llama a `POST /api/auth/logout`: revoca la sesión en backend,
    elimina la cookie y regresa a `/login`. Una copia del JWT también queda invalidada.
    Si falla la conexión, se informa el error y no se presenta el cierre como exitoso.

`RequireAuth` verifica autenticación, no implementa roles ni permisos de E1-H3.
Las pantallas de sucursales e inventario conservan sus comportamientos de prototipo.
El prototipo de inventario se conserva en `/prototypes/inventory`; `/admin/inventory`
ahora muestra una sección vacía del menú. El texto «Administrador de ejemplo» de sucursales sigue siendo parte de ese diseño,
no un rol concedido por el backend. Sus enlaces «Volver al inicio de sesión» solamente
navegan. El cierre real está en la cabecera del layout compartido. E1-H2 verifica
el rol Administrador en backend, adicionalmente a la autenticación.

## Límites y cierre de sesión solicitados

- Máximo **8 fallos por correo en una ventana de 15 minutos**, sin distinguir si existe.
  El octavo fallo responde 429. Los aciertos no cuentan como fallos, pero no borran fallos previos.
- Máximo **40 solicitudes válidas de login por IP en 15 minutos**, incluyendo aciertos,
  para limitar intentos que cambian de correo. Las solicitudes bloqueadas no alargan la espera.
- `Retry-After` indica los segundos hasta que se libere un cupo; la interfaz muestra
  los minutos de espera redondeados hacia arriba. Los bloqueos son temporales.
- Las reservas de intentos usan un bloqueo de concurrencia: llamadas paralelas no superan la cuota.
- Cada JWT tiene un `jti` aleatorio. `/me` exige que esté en el registro de sesiones activas.
- **Estado temporal en memoria, un solo proceso FastAPI:** reiniciar o recargar el backend
  cierra todas las sesiones y reinicia los límites. No ejecutar con múltiples workers.
  Al definir PostgreSQL se deberá trasladar este estado a persistencia compartida.
  No se creó una base de datos en esta ampliación.
- El límite por IP usa la dirección que proporciona el servidor. Al desplegar detrás
  de proxies, configurar explícitamente cuáles son confiables; no confiar en cabeceras
  de IP enviadas libremente por clientes. En el proxy local varios clientes pueden compartir IP.

Cerrar una pestaña no cierra la sesión. La cookie persistente puede sobrevivir al cierre
del navegador, dentro de sus 9 horas de validez desde el login. «Cerrar sesión» la invalida de inmediato
en el servidor; otras pestañas lo detectan al consultar `/me` (foco, recarga o revisión periódica).
HTTPS puede configurarse también localmente con un certificado confiable; no exige hosting.
Esta configuración de desarrollo continúa utilizando HTTP y `COOKIE_SECURE=false`.

## Archivos creados

| Archivo | Propósito |
| --- | --- |
| `backend/app/__init__.py` | Define el paquete del backend. |
| `backend/app/main.py` | Fábrica FastAPI, inicio del repositorio, CORS, errores seguros y rutas. |
| `backend/app/config.py` | Variables de entorno y validación de configuración. |
| `backend/app/auth/__init__.py` | Define el módulo de autenticación E1-H1. |
| `backend/app/auth/routes.py` | Contratos públicos, login y validación de sesión `/me`. |
| `backend/app/auth/security.py` | Argon2 y generación/verificación del JWT. |
| `backend/app/auth/state.py` | Límites concurrentes y registro temporal de sesiones activas. |
| `backend/app/auth/users.py` | Modelo interno y adaptador local temporal de usuarios. |
| `backend/app/seed_dev.py` | Crea dos cuentas locales de prueba sin sobrescribir archivos existentes. |
| `backend/tests/test_auth.py` | Pruebas de aceptación y seguridad de E1-H1. |
| `backend/requirements.txt` | Dependencias de ejecución con las versiones directas verificadas. |
| `backend/requirements-dev.txt` | Dependencias de pruebas y linter. |
| `backend/.env.example` | Plantilla sin clave real. |
| `src/pages/e1-access-users-branches/auth/login.api.ts` | Cliente HTTP tipado y mensajes de error seguros. |
| `src/pages/e1-access-users-branches/auth/RequireAuth.tsx` | Comprobación y recuperación de sesión para las rutas internas. |
| `src/pages/e1-access-users-branches/auth/LogoutButton.tsx` | Cierre de sesión reutilizable; sustituye la antigua SessionPage. |
| `src/layouts/AdminLayout.tsx` | Menú y cabecera compartidos; `/session` conserva contenido vacío. |

Durante la preparación local se generan `backend/.venv/`, `backend/.env` y
`backend/data/users.json`; están excluidos de Git. El último contiene hashes, nunca
contraseñas en texto plano. `.env` contiene una clave privada aleatoria no versionada.

## Archivos modificados

| Archivo | Cambio y motivo |
| --- | --- |
| `src/pages/e1-access-users-branches/auth/LoginPage.tsx` | Reemplaza el selector de escenarios simulados por la API real; añade carga, errores y bloqueo de envíos repetidos. Mantiene diseño, logo y campos existentes. |
| `src/pages/e1-access-users-branches/sprint-one.css` | Elimina únicamente las tres reglas del selector de demostración retirado. |
| `src/routes/AppRouter.tsx` | Protege las rutas internas mediante el componente de autenticación. |
| `vite.config.ts` | Proxy `/api` y puerto 5173 fijo para una conexión local consistente. |
| `eslint.config.js` | Evita que ESLint recorra el entorno virtual Python. |
| `.gitignore` | Excluye secretos, usuarios locales, entorno virtual y cachés Python. |
| `README.md` | Documenta el funcionamiento, las decisiones y los pasos para reproducirlo. |

## Cómo funciona el frontend

Al abrir `/login`, `LoginPage` consulta primero `/api/auth/me`. Si la sesión sigue
vigente, redirige a `/session` sin pedir credenciales nuevamente. Mientras consulta,
muestra «Verificando sesión…». Sin sesión válida muestra el formulario; si falla la
conexión, informa el error. Las otras rutas internas mantienen su validación en
`RequireAuth`; iniciar sesión no concede permisos por rol todavía.

`LoginPage.tsx` usa `visible` para mostrar/ocultar contraseña, `loading` para el botón
y `error` para el aviso accesible (`role="alert"`). `sending`, un `useRef`, bloquea
un segundo envío incluso antes del siguiente render. Los inputs permanecen como
formulario no controlado: `FormData` captura sus valores durante `submit`.
La contraseña no se almacena en ningún almacenamiento del navegador.

`login.api.ts` centraliza las peticiones, incluye cookies y aplica un tiempo máximo
de espera de 10 segundos. Traduce 400, 401, 403, 422, 429 y errores del servidor a mensajes
comprensibles sin mostrar el cuerpo técnico del error. También controla respuestas
inesperadas. El backend devuelve 422 para cuerpos inválidos y 401 para acceso rechazado;
403 para origen de login no autorizado; CORS puede devolver 400 en un preflight rechazado.

`RequireAuth.tsx` mantiene exclusivamente la información pública obtenida de `/me`.
No considera auténtico a un usuario por un booleano guardado en React. Antes de mostrar
`Outlet` exige una respuesta válida del backend y muestra el estado de verificación.
El acceso exitoso se anuncia con un estado accesible y la navegación a `/session`.

## Seguridad y decisiones técnicas

- **Hashing:** Argon2id convierte la contraseña en una representación no reversible
  con una sal aleatoria. `pwdlib` verifica una contraseña contra el hash guardado.
  Una filtración del archivo de datos no entrega directamente las contraseñas.
- **Token:** PyJWT firma un comprobante temporal de identidad. Contiene solamente
  `sub` (ID), `jti` (sesión), `iat`, `exp`, `iss` y `aud`. Un JWT está firmado, no cifrado; por eso no
  contiene contraseñas, hashes ni información de perfil innecesaria.
- **Expiración:** por defecto 9 horas (540 minutos) desde el login, sin renovación automática. Esta expiración
  corresponde exclusivamente al login; no altera las reglas de QR de otras historias.
- **Cookies:** HttpOnly impide leer el JWT desde JavaScript. SameSite=Strict y la
  comprobación del encabezado Origin del login limitan peticiones desde otros sitios.
  El frontend y `/api` deben servirse bajo el mismo sitio; Vite lo resuelve en desarrollo.
- **Entorno:** la clave no tiene valor por defecto y debe tener al menos 32 bytes.
  El algoritmo permitido es HS256; cambiarlo requiere una decisión explícita de código.
  Usa `COOKIE_SECURE=true` y HTTPS para un despliegue real. `false` permite HTTP local.
- **Persistencia:** no se introdujo otra base de datos. `LocalUserRepository` es un
  adaptador de desarrollo que lee `data/users.json` y valida datos y duplicados.
  Falla al iniciar si falta el archivo; no crea cuentas silenciosamente. Más adelante
  debe reemplazarse por un repositorio PostgreSQL que conserve `by_email` y `by_id`.
  No es una solución de persistencia de producción ni un CRUD de usuarios.
- **Alcance:** no se implementaron registro, recuperación, roles, sucursales, inventario
  ni ninguna otra funcionalidad. Las rutas internas existentes se protegen para E1-H1.
  Cada futuro endpoint de negocio deberá validar sesión y sus permisos en backend.
- **Pruebas frontend:** no había infraestructura; no se añadieron dependencias de UI.
  Se verificaron TypeScript, ESLint, build y el recorrido HTTP por Vite. La comprobación
  visual interactiva en navegador queda pendiente porque la herramienta no tenía un
  navegador conectado.

Referencias técnicas: [seguridad con JWT y hashing en FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).

## Ejecutar en Windows PowerShell

Requisitos: Python 3.12 y una versión de Node compatible con el Vite del proyecto.
Las comprobaciones se ejecutaron con Python 3.12 y las dependencias npm existentes.
No es necesario activar el entorno virtual ni cambiar la política de ejecución.

### A. Instalar backend y configurar datos locales (una sola vez)

Desde la raíz del proyecto:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Set-Location backend

# Crear .env solamente si todavía no existe; nunca imprimir la clave.
if (-not (Test-Path .env)) {
    $authSecret = & .venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
    (Get-Content .env.example -Raw).Replace('JWT_SECRET_KEY=', 'JWT_SECRET_KEY=' + $authSecret) |
        Set-Content -Encoding utf8 .env
}

# Solicita la contraseña sin mostrarla. No sobrescribe usuarios existentes.
if (-not (Test-Path data\users.json)) {
    .venv\Scripts\python.exe -m app.seed_dev
}
```

Para reproducir las cuentas preparadas en esta implementación, introduce
`Desarrollo-E1H1!2026` cuando `seed_dev` solicite la contraseña. Es una credencial
exclusivamente de prueba y conocida; no debe utilizarse para personas ni entornos reales.
Si decides usar otra, ambas cuentas se crearán con esa contraseña.

### B. Iniciar FastAPI

Desde `backend/`:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Documentación de endpoints: `http://127.0.0.1:8000/docs`.

### C. Instalar frontend si hace falta

En otra terminal, desde la raíz:

```powershell
npm.cmd ci
```

### D. Iniciar React

Desde la raíz:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

Abrir `http://127.0.0.1:5173/login`. Mantener ambos servidores activos.
Usar consistentemente `127.0.0.1` o `localhost`; sus cookies son independientes.
Si un puerto ya está ocupado, detener la instancia anterior con Ctrl+C.

### E. Ejecutar verificaciones

Desde la raíz:

```powershell
npm.cmd run lint
npm.cmd run build
Set-Location backend
.venv\Scripts\python.exe -m ruff check app tests
.venv\Scripts\python.exe -m pytest -q
```

`npm run build` ejecuta primero `tsc -b`, luego el build de Vite.
Las pruebas usan archivos temporales y una clave exclusiva de prueba; no requieren
servidores activos, no usan las cuentas locales y no modifican `data/users.json`.

## Prueba manual de E1-H1

| Caso | Datos / acción | Resultado esperado |
| --- | --- | --- |
| Activo | `interno@farmacia.cl` / `Desarrollo-E1H1!2026` | Accede a `/session`, contenido vacío, menú y «Cerrar sesión». |
| Límite | Fallar 8 veces con el mismo correo | Mensaje de demasiados intentos con tiempo de espera. |
| Cierre | Pulsar «Cerrar sesión» y volver a `/session` | Regresa al login; no permite reutilizar la sesión. |
| Contraseña incorrecta | Mismo correo / cualquier contraseña incorrecta | Permanece en login, mensaje genérico. |
| Correo inexistente | `nadie@farmacia.cl` / contraseña de prueba | Exactamente el mismo rechazo. |
| Inactivo | `inactivo@farmacia.cl` / `Desarrollo-E1H1!2026` | Mismo rechazo; no revela el estado de la cuenta. |
| Campos vacíos o correo inválido | Enviar formulario incompleto | Validación del navegador impide el envío. |
| Recarga | F5 después del acceso válido | `/me` valida la cookie y permite continuar. |
| Acceso directo sin sesión | Abrir `/admin/branches` en ventana privada | Redirige a `/login`. |
| Backend desconectado | Detener FastAPI e intentar login | Mensaje de conexión o indisponibilidad, sin detalles técnicos. |
| Sesión expirada | Configurar `ACCESS_TOKEN_EXPIRE_MINUTES=1`, reiniciar FastAPI e iniciar sesión nuevamente | Después del minuto vuelve al login; restaurar 540 al terminar. |

También se puede comprobar la cookie por HTTP desde PowerShell, con ambos servidores activos:

```powershell
$body = @{ email = 'interno@farmacia.cl'; password = 'Desarrollo-E1H1!2026' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5173/api/auth/login `
    -ContentType 'application/json' -Body $body -SessionVariable authSession
Invoke-RestMethod -Uri http://127.0.0.1:5173/api/auth/me -WebSession $authSession
```

## Resultados verificados

- ESLint: correcto.
- TypeScript y build Vite: correctos.
- Ruff: correcto.
- Pytest: **73 pruebas aprobadas** (39 de autenticación y 34 de usuarios). Hay dos avisos de deprecación en dependencias
  (Starlette/httpx y AnyIO); no son fallos de pruebas.
- FastAPI iniciado mediante Uvicorn: correcto.
- HTTP real contra puerto 8000 y proxy 5173: acceso válido, cookie HttpOnly,
  recuperación de sesión, rechazos por contraseña/correo/inactividad y limpieza de cookie: correctos.
- Vite sirvió `/login`: HTTP 200.
- No se realizó una prueba visual interactiva en navegador.

Los 29 casos originales cubren: login válido, cuatro combinaciones de rechazo, normalización
de correo, recuperación por cookie, tres casos de token ausente/inválido, siete
variantes de claims/firma/algoritmo, desactivación posterior, cuatro cuerpos inválidos,
JSON mal formado, limpieza de sesión tras rechazo, error 500 genérico, CORS/origen,
cookie Secure, rechazo de clave débil y hashing Argon2.

Los 10 casos añadidos comprueban límites en cuentas activas/inactivas/inexistentes,
desbloqueo por tiempo, éxitos que no consumen cuota por correo, límite por IP,
concurrencia, revocación de una copia del token, cierre repetido, separación de sesiones,
rechazo de un origen externo al cerrar y no reactivación tras reiniciar.
