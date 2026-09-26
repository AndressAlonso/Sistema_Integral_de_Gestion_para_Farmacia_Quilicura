# Integración en Proyecto — 26/09/2026

## Procedencia y alcance

- Proyecto: `0d7a28f` (login, usuarios, roles/permisos y sucursales).
- Catálogo: `origin/feat/e2-catalogo`, `d873d43`.
- Inventario: `origin/feat/e3-inventario-jesus`, `ff7b2d5`.
- Catálogo ya es ancestro de Inventario. El merge de Inventario incorpora ambas
  historias de Git sin modificar las ramas de origen.

Se conserva la lógica recibida de E2-H1 (categorías, productos, códigos de barras,
edición e imagen principal) y E3-H1 (consulta real de stock por producto/sucursal).
Se mantienen los contratos, protecciones y gestor de roles existentes de E1.
Esto no declara terminadas todas las HU de E2/E3: la carga operacional de stock,
lotes, FEFO, movimientos y precios/promociones no se implementan en esta integración.

## Ajustes necesarios para convivir

- `app/role_catalog.py`: Inventario figura como implementado en los permisos.
- `app/users/roles_repository.py`: agrupa el permiso de Catálogo bajo «Catálogo».
- `app/seed_e2_e3.py`: introduce `catalogo.gestionar` en Administrador únicamente
  cuando el permiso todavía no existe. Conserva nombres, UUID, permisos editados,
  usuarios, contraseñas, estados y sucursales. Repetirlo no restaura permisos retirados.
  Si el permiso ya existía sin asignación, se configura mediante el gestor de roles.
- `app/branches/repository.py`: `can_delete` contempla la nueva referencia de
  inventario. Se oculta la eliminación y se rechaza con 409, incluso sin usuarios.
  La FK original sigue protegiendo asignaciones concurrentes.
- Ajustes de imports y anotación `set[str]` para pasar Ruff, sin cambio funcional.

Los módulos originales `catalog` e `inventory` se conservaron sin reescritura.
Archivos compartidos recibidos: `main.py`, `models.py`, `role_catalog.py`,
`requirements.txt`, `AppRouter.tsx` y `adminNavigation.ts`.

## PostgreSQL

Se aplicaron, con autorización y respaldo previo, las migraciones originales:

1. `0002_catalogo`: categoria, producto y codigo_barra.
2. `0003_producto_imagen`: image_key en producto.
3. `0004_inventario`: inventario_sucursal y sus restricciones/FK.

No se creó otra migración ni se modificaron las existentes. No se recreó la base.
`alembic check` confirma que no hay operaciones de actualización pendientes.
Las imágenes se guardan en `backend/media`, no se versionan; ese directorio también
requiere respaldo cuando se utilice con datos reales.

## Actualizar un entorno existente (PowerShell)

Desde la carpeta que contiene `package.json`, con `.env` ya configurados:

```powershell
docker compose up -d db
Set-Location backend
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.seed_e2_e3
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

En otra consola, desde la carpeta de `package.json`:

```powershell
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Abrir http://127.0.0.1:5173. No se requieren nuevas variables de entorno ni cambiar
credenciales. Pillow se incorpora mediante requirements. No ejecutar seeds de
usuarios para actualizar un entorno que ya contiene cuentas.

El `compose.yaml` heredado solo se utiliza aquí para PostgreSQL. Sus servicios
API/web todavía referencian una estructura anterior; no se validó un despliegue
completo con `docker compose up`. Se verificaron FastAPI y Vite ejecutados localmente.

## Verificación

Desde backend:

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m alembic check
```

Desde la carpeta de package.json:

```powershell
npm.cmd run lint
npm.cmd run build
```

Resultado: **193 pruebas aprobadas**, Ruff/ESLint correctos y TypeScript/Vite
compilados. Las pruebas SQL usan rollback: no dejan usuarios/productos/stock ficticios.
Hay dos avisos de deprecación en dependencias del cliente de pruebas.

`tests/test_e2_e3_integration.py` verifica integración catálogo/stock, cálculo de
disponible, 401/403, restricciones de cantidades, bloqueo de eliminación de sucursal
y seed idempotente que conserva personalizaciones. Se ejecutaron también las pruebas
existentes de E1 y las pruebas recibidas de catálogo/imágenes.

Prueba HTTP con servidores reales: login, me, usuarios, roles, sucursales,
categorías, productos e inventario respondieron 200; logout 204 y me posterior 401.
Frontend respondió 200. No se realizó una revisión visual manual en navegador.

## Prueba manual y límites actuales

1. Iniciar sesión con una cuenta administradora existente.
2. Confirmar Usuarios, Roles y Sucursales; comprobar sus permisos antes de editar.
3. Abrir Productos: crear categoría/producto, editar sus datos e imagen.
4. Abrir Inventario: muestra registros de inventario existentes y sus filtros.
   Crear un producto no crea automáticamente stock; una lista vacía es válida.
5. Probar una cuenta sin permisos: no debe poder acceder a los endpoints protegidos.

Los demás integrantes deben actualizar su rama desde Proyecto, instalar dependencias,
ejecutar migraciones y el seed de permisos indicado. No deben borrar ni recrear su base.
Las ramas de Catálogo e Inventario permanecen intactas; este trabajo no incluye push.
