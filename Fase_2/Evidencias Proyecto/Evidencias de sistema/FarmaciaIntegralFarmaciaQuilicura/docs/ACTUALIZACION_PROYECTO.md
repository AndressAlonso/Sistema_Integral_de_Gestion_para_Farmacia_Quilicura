# Instalar o actualizar SIGFQ

La aplicación web se ejecuta desde esta carpeta, donde se encuentra package.json. No hay una carpeta frontend separada. Requiere Node.js compatible con Vite, Python 3.12 y PostgreSQL.

## Actualizar una instalación existente

1. Detener las terminales de Vite y FastAPI.
2. Actualizar la rama Proyecto con git pull --ff-only desde la raíz del repositorio. Si Git informa cambios locales o divergencia, resolverlos antes de continuar; no usar reset para descartarlos.
3. Conservar los archivos .env privados y la base PostgreSQL existente. La descarga no incluye contraseñas ni datos.
4. Desde la carpeta de la aplicación, ejecutar:

```powershell
npm.cmd ci
```

5. Desde backend, con PostgreSQL iniciado:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m alembic upgrade head
```

La revisión 0017_promociones crea la tabla de promociones; no recrea la base ni elimina inventario, usuarios o ventas. No usar alembic stamp para omitir migraciones ni borrar volúmenes de Docker.

6. Iniciar el backend desde backend:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

7. En otra terminal, desde la carpeta de la aplicación:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abrir http://127.0.0.1:5173/tienda. El personal utiliza /login. Las cuentas existentes se conservan.

## Primera instalación

- Descargar o clonar la rama Proyecto.
- Copiar los ejemplos .env.example a .env y configurar valores propios; no publicar esos archivos.
- Para usar PostgreSQL de compose.yaml, iniciar Docker Desktop y ejecutar docker compose up -d db desde esta carpeta. Configurar backend/.env con la misma base, usuario, contraseña y puerto 5433.
- Crear el entorno desde backend con py -3.12 -m venv .venv; instalar requirements-dev.txt y ejecutar alembic upgrade head como arriba.
- Generar JWT_SECRET_KEY con al menos 32 bytes aleatorios (por ejemplo, .venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))") y colocarla en backend/.env.
- Solo en una base nueva de desarrollo: definir DEMO_PASSWORD con una contraseña propia en la terminal y ejecutar .venv\Scripts\python.exe -m app.seed desde backend para crear las cuentas de prueba descritas en el README. No ejecutar seeds para reemplazar usuarios o contraseñas de una instalación existente.
- Instalar el frontend con npm.cmd ci e iniciar backend y frontend según los pasos anteriores.

## Comportamiento incluido

- Promociones porcentuales o de precio final fijo por producto o categoría; no se acumulan y se aplica la de menor precio final. Se muestran en catálogo, carrito y ventas.
- Inventario con físico, reservado y disponible; mínimo por producto y sucursal.
- Lotes vencidos no se utilizan para salidas. La habilitación manual requiere motivo y queda auditada; no altera cantidades.
- Ajustes permiten reducir unidades de lotes o productos deshabilitados, incluidos vencidos, conservando su estado e historial y protegiendo reservas. El retiro físico se registra con la cantidad final y el motivo.
- Transferencias validan conflictos conocidos de lote destino antes de solicitar o despachar y vuelven a comprobar al recibir. Los cambios posteriores en destino pueden exigir revisión en recepción.
- Paginación de listados y mejoras de presentación. Cada fila de lotes corresponde a producto, lote y sucursal.

## Límites actuales

La creación real de pedidos online, pagos y retiro de E7 siguen pendientes. El historial online y la persistencia de datos de invitado dependen de esos pedidos. No se debe interpretar el checkout previo como una compra completada. La app móvil requiere verificación con un dispositivo real.

## Comprobaciones realizadas

Frontend instalado mediante npm.cmd ci: lint, 59 pruebas y build correctos. Backend: 456 pruebas con rollback sobre la base de trabajo, conservando exactamente sus datos. Instalación nueva: todas las migraciones y 468 pruebas, incluidas las de concurrencia, aprobadas en una base temporal aislada que se eliminó al terminar. Ruff aprobado en los archivos Python incluidos. El build mantiene un aviso de tamaño de paquete superior a 500 kB.
