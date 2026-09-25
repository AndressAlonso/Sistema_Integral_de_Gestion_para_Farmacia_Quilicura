# E1-H3: gestor de roles dentro de Usuarios

## Alcance acordado

Crear roles, cambiar su nombre y seleccionar permisos existentes. No elimina
roles ni crea permisos arbitrarios. Reutiliza `rol`, `permiso`, `rol_permiso`
y `usuario_rol`, UUID y restricciones existentes. **No se modificó el esquema**
ni se crearon migraciones. No hay dependencias nuevas.

Usuarios → Gestionar roles abre un modal al 98% con buscador y lista a la
izquierda; nombre, código y permisos agrupados por módulo a la derecha.
El código se sugiere al escribir el nombre, puede ajustarse al crear y es
inmutable después. Su unicidad se comprueba en PostgreSQL. El nombre no requiere
ser único. Un rol puede tener cero permisos; la interfaz lo advierte.

Se muestra el número de usuarios asignados (activos e inactivos) y se pide
confirmar si una edición los afecta. Al cambiar de rol o cerrar se avisa si hay
cambios sin guardar. Tras guardar se actualizan las opciones en Usuarios.
Los permisos pendientes se identifican como tales: marcarlos no implementa
funciones de otras épicas. Los permisos desconocidos para este catálogo se
presentan conservadoramente como pendientes, manteniendo su configuración.

## Contratos nuevos

Los tres endpoints requieren cookie válida y los permisos `usuarios.gestionar`
y `roles.gestionar`. Este último ahora autoriza crear/configurar roles además
de asignarlos. Los contratos anteriores de usuarios y login no cambian.

| Método | Ruta | Entrada | Éxito |
| --- | --- | --- | --- |
| GET | /api/users/roles | Sin cuerpo | 200: roles y permisos disponibles |
| POST | /api/users/roles | code, name, permission_ids | 201: rol creado |
| PATCH | /api/users/roles/{id} | name, permission_ids, revision | 200: rol actualizado |

Ejemplo de creación:

```json
{"code":"SUPERVISOR","name":"Supervisor","permission_ids":[]}
```

Cada rol responde `id`, `code`, `name`, `permission_ids`, `users_count` y
`revision`. Los permisos disponibles responden `id`, `code`, `description`,
`implemented` y `module`. Los IDs son UUID.

`revision` es una huella del código, nombre, permisos y cantidad de usuarios;
se envía al editar y se valida en backend. No requiere una columna. Si cambió
la configuración o cantidad de asignaciones desde la lectura, se rechaza y
se solicita recargar. No pretende detectar intercambios de usuarios que
mantengan la misma cantidad ni sustituye un historial de auditoría.

Errores: 401 sin sesión; 403 sin permisos/origen no permitido; 404 rol inexistente;
409 código duplicado/reservado, edición desactualizada o pérdida del último
gestor activo; 422 datos inválidos, permisos inexistentes/duplicados o código
alterado al editar. `ADMIN` y `OPERADOR` quedan reservados por compatibilidad.

## Seguridad y persistencia

El servicio verifica los permisos actuales del actor dentro de la transacción.
Las escrituras usan el bloqueo transaccional existente de acceso para coordinarse
con cambios de rol, estado y eliminación de usuarios. El backend comprueba que
la edición de permisos deje al menos una cuenta activa que reúna ambos permisos
de gestión, incluyendo permisos heredados de varios roles. Si falla, se revierte
el nombre y los permisos junto con toda la operación.

La protección aquí cubre ediciones de roles; no amplía las reglas anteriores
de desactivación o retirada de roles desde la ficha de usuario.
Los endpoints protegidos consultan permisos efectivos actuales en PostgreSQL:
los cambios aplican sin nuevo login. El menú se actualiza al validar `/me`.

La navegación general no se modifica. Los accesos a pantallas en blanco que
dependen de códigos predefinidos (p. ej. POS para VENDEDOR_CAJERO) conservan esa
regla; crear un rol personalizado no le copia esos accesos visuales.

## Carga inicial y coordinación del equipo

`app/role_catalog.py` crea roles ausentes con sus permisos iniciales. Cuando un
rol ya existe conserva nombre y permisos, incluso si un administrador los quitó.
La compatibilidad de códigos legados se mantiene. `app/seed.py` utiliza la misma
función sin cambios. No es necesario volver a ejecutar el seed para usar el gestor.

Los siguientes módulos pueden agregar permisos a su catálogo, pero no deben
suponer que repetir el seed los asignará a roles existentes: esas asignaciones
se gestionan explícitamente. Los cambios al catálogo común deben coordinarse.
No se tocaron main.py, modelos, router general, estilos globales ni dependencias.

## Verificación

`tests/test_roles.py` cubre creación, asignación y cambio de permisos sobre sesión
existente; autorización; datos inválidos; duplicados; código inmutable; conflictos
de edición/asignación; protección del último gestor y rollback; origen de la
petición; conservación de cambios al repetir la carga inicial.

Desde `backend` (PowerShell, base local con migración existente aplicada):

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check app tests
```

Desde la raíz del frontend: `npm.cmd run lint` y `npm.cmd run build`.
Las pruebas usan datos ficticios con rollback, sin borrar cuentas reales.
Revisión manual y revisión del equipo continúan pendientes según lo acordado.

Para probar: abrir Usuarios → Gestionar roles, crear Supervisor con permisos,
asignarlo a un usuario de prueba desde su ficha, volver al gestor y editar sus
permisos. Revisar cantidad afectada y confirmar. Otro integrante debe actualizar
su rama y reiniciar FastAPI; no debe ejecutar migraciones ni cambiar `.env`.
