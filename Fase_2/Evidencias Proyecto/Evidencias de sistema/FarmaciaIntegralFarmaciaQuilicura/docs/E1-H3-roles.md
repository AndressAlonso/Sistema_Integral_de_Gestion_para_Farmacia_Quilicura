# E1-H3: catálogo de roles y asignación explicada

Catálogo autorizado el 24 de septiembre de 2026:

| Código | Nombre | Permisos registrados actualmente |
| --- | --- | --- |
| ADMINISTRADOR | Administrador | usuarios.gestionar, roles.gestionar, sucursales.gestionar, inventario.consultar |
| VENDEDOR_CAJERO | Vendedor / Cajero | Pendientes de sus módulos |
| ENCARGADO_INVENTARIO | Encargado de inventario | inventario.consultar |
| ENCARGADO_PEDIDOS | Encargado de pedidos | Pendientes de sus módulos |
| QUIMICO_FARMACEUTICO | Químico farmacéutico | Pendientes de sus módulos |
| SOCIO | Socio | Pendientes de sus módulos |

El permiso de consulta de inventario ya existía, pero no representa un módulo
operativo finalizado. Se muestra como «Módulo pendiente». Los otros tres permisos
existentes protegen gestión de usuarios, asignación de roles y gestión de sucursales.
No se implementó CRUD de permisos, POS, ventas, caja, catálogo, pedidos ni auditoría.

## Persistencia y compatibilidad

No se modificó el esquema. Se reutilizan rol, permiso, rol_permiso y usuario_rol.
La carga renombra ADMIN a ADMINISTRADOR y OPERADOR a ENCARGADO_INVENTARIO,
conservando UUID, relaciones y permisos previos. No cambia contraseñas, correos,
estado ni sucursal. Crea los otros cuatro roles. Si existe simultáneamente el
código viejo y el nuevo, aborta la transacción para evitar una fusión no autorizada.

La descripción acordada se mantiene en `app/role_catalog.py`, sin añadir columnas.
Los permisos que entrega la API se leen de PostgreSQL; no se calculan por nombre
en React. La carga es idempotente y conserva permisos personalizados existentes.

Desde backend, con el `.env` del entorno correcto:

```powershell
.venv/Scripts/python.exe -m app.role_catalog
```

Es una actualización de datos explícita, no una migración estructural. Cada
integrante debe aplicar el código y esta carga al mismo tiempo, reiniciando FastAPI;
versiones antiguas que dependen de ADMIN/OPERADOR deben actualizarse. El seed de
desarrollo reutiliza la misma carga para no volver a crear códigos antiguos.

## Contrato y frontend

GET /api/users conserva su estructura y añade a cada elemento de `roles`:

```json
{
  "description": "Responsabilidad acordada del rol",
  "permissions": [
    {"code": "usuarios.gestionar", "description": "Gestionar usuarios internos", "implemented": true}
  ]
}
```

Crear/editar sigue enviando `role_ids` UUID. El contexto de sucursal añadido
posteriormente a login y `/me` se documenta en `E1-contexto-sesion.md`.
Los arrays de códigos de rol ahora usan los nombres nuevos. La protección del
último administrador y el contador del frontend utilizan ADMINISTRADOR.

El formulario muestra seis tarjetas seleccionables, descripción y permisos
configurados con su disponibilidad. Los roles se pueden combinar: sus permisos
se suman. Se mantiene una sola sucursal por usuario. Una descripción de alcance
no concede permisos futuros ni sustituye la autorización del backend.

Decisión confirmada: los permisos del usuario se asignan mediante sus roles.
No se requiere selección independiente de permisos por usuario para este alcance.

## Verificación

Las pruebas con rollback cubren conservación de IDs/asignaciones, repetición de
la carga, conflicto de códigos y creación/login/autorización para los seis roles.
Se conserva la prueba que impide eliminar al último administrador activo.

Para probar manualmente: abrir Usuarios, Nuevo usuario o Editar, revisar las
tarjetas y seleccionar roles. Guardar y comprobar sus nombres en la tabla.
