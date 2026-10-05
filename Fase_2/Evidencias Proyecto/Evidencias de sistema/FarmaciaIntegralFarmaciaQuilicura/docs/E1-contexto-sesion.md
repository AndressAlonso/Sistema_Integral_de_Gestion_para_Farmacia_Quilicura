# E1-H1, E1-H3 y E1-H4: navegación y contexto de sesión

## Contrato compatible ampliado

POST `/api/auth/login` mantiene el request `{ "email": "...", "password": "..." }`.
GET `/api/auth/me` sigue requiriendo la cookie de sesión. Ambos conservan
`user.id`, `user.email`, `user.name`, `user.permissions` y `expires_at`, y añaden:

```json
{
  "user": {
    "branch_id": "UUID de la sucursal asignada",
    "branch_name": "Nombre de la sucursal"
  }
}
```

El fragmento muestra solo los campos nuevos. No cambian estados HTTP ni cookies.
La sucursal se consulta en PostgreSQL, no se acepta desde el cliente al autenticar
ni se fija dentro del JWT. `/me` devuelve la asignación actual sin exigir nuevo login.
React la conserva en `AuthSession`, disponible por el contexto del router; la
validación existente la actualiza al recargar, recuperar foco y cada 60 segundos.
Las operaciones futuras deben obtener su contexto desde backend, sin confiar en
un identificador enviado por el navegador.

No se modificó el esquema ni se crearon migraciones. Los consumidores existentes
que toleran campos adicionales mantienen compatibilidad. Este frontend requiere
el backend actualizado; reiniciar FastAPI al aplicar estos cambios.

## Navegación y autorización

Resumen continúa siendo la entrada temporal para cualquier usuario autenticado.
Usuarios requiere `usuarios.gestionar`; Sucursales, `sucursales.gestionar`;
Inventario, `inventario.consultar` (su pantalla sigue pendiente).
Las pantallas futuras se conservan en blanco y se muestran por los roles
acordados, sin crear permisos de otras épicas:

| Rol | Pantallas en blanco adicionales |
| --- | --- |
| ADMINISTRADOR | Productos, Transferencias, Pedidos Online, POS / Ventas, Caja, Promociones, Auditoría, Reportes |
| VENDEDOR_CAJERO | POS / Ventas, Caja |
| ENCARGADO_INVENTARIO | Transferencias (además de Inventario por su permiso) |
| ENCARGADO_PEDIDOS | Pedidos Online |
| QUIMICO_FARMACEUTICO | Productos |
| SOCIO | Auditoría, Reportes |

Login y `/me` entregan `user.roles` desde PostgreSQL para esta navegación. Si hay
varios roles, se combinan los accesos. Esto no concede permisos operativos ni
implementa otras épicas; sus operaciones futuras deberán autorizarse en backend.

Menú y acceso por URL dentro del layout comparten el mismo control; una ruta sin
permiso redirige a Resumen. La autorización real de las operaciones sigue en
FastAPI. Los permisos efectivos son la unión de los permisos de los roles,
según la decisión confirmada; no hay permisos individuales por usuario.

## Verificación

Pruebas backend: login y `/me` entregan la sucursal; cambiar la asignación mediante
la API se refleja en la misma sesión sin cambiar permisos ni extender expiración.
Se ejecutan también suite existente, Ruff, ESLint y compilación TypeScript/Vite.
La prueba manual de interfaz y revisión de otro integrante quedan en espera por
instrucción del usuario; no se consideran realizadas.
