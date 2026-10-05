# E1-H2: eliminación informada de cuentas

Decisión autorizada: una cuenta creada por error puede borrarse definitivamente
aunque tenga sesiones, siempre que no existan otras referencias que lo impidan. No hay recuperación.
La asignación sigue siendo de una sola sucursal por usuario.

## API

`POST /api/users/{id}/delete`, con cookie de sesión y permiso `usuarios.gestionar`.
Entrada: `{"confirmation_email":"correo@farmacia.cl"}`.
Éxito: 204 sin cuerpo. Errores: 401 sesión inválida, 403 permiso/origen,
404 usuario inexistente, 409 impedimento, 422 confirmación inválida/diferente.
Se normalizan espacios externos y mayúsculas del correo.

El listado agrega `can_delete` y `deletion_block_reason`, calculados para el actor.
Las respuestas de creación/edición/desactivación conservan un valor seguro falso;
React actualiza el listado después de guardar para recuperar la elegibilidad actual.
No se cambió el contrato de autenticación.

## Protecciones

- No eliminar la propia cuenta.
- No desactivar la propia cuenta: backend responde 409 y conserva la sesión;
  la ficha oculta esa acción para el usuario autenticado.
- No eliminar al último usuario activo con rol `ADMINISTRADOR`.
- Se borran las sesiones activas, vencidas y revocadas del usuario dentro de la misma transacción. Si el borrado falla, todo se revierte.
- Las claves foráneas permanecen como protección adicional para registros asociados.
- La eliminación y los cambios de roles/estado del repositorio usan un bloqueo
  transaccional compartido para serializar la comprobación de administradores.
- Se bloquea la fila del usuario y se comprueban las condiciones al borrar.
- Las asignaciones usuario-rol se retiran dentro de la misma transacción;
  no se eliminan roles ni sucursales.

No se modificó el esquema ni se crearon migraciones. No se implementó auditoría.
La protección del último administrador se aplica a esta operación de eliminación;
las reglas adicionales de desactivación o retirada del rol no se ampliaron.
Futuros módulos de historial deberán ampliar la elegibilidad y conservar sus FK.

## Interfaz

La tabla abre la ficha pulsando el nombre y no tiene columna de acciones.
La ficha permite editar y acceder a las confirmaciones de activar/desactivar/eliminar.
Solo se muestra Eliminar para cuentas elegibles; las restantes muestran el motivo.
El diálogo identifica nombre, correo y UUID, explica la irreversibilidad y ofrece
Desactivar como alternativa. Es obligatorio escribir el correo antes de confirmar.
El backend vuelve a validar si cambió la situación desde que se cargó la página.

Activación: `POST /api/users/{id}/activate`, sin cuerpo, con cookie y permiso
`usuarios.gestionar`. Responde 200 con `UserResponse`; errores 401, 403 y 404.
Reutiliza el estado existente, sin migración. No revive sesiones revocadas.
La activación/desactivación es independiente de los cambios sin guardar del
formulario; confirmar una acción no guarda esos campos.

## Pruebas

`tests/test_user_deletion.py` cubre borrado de cuenta sin uso, confirmación inválida,
autoeliminación, sesiones previas, último ADMIN activo, autorización y origen.
Utiliza fixtures PostgreSQL con rollback; no borra cuentas reales. Prueba eliminación con sesiones abiertas y revocadas, invalidación del token y conservación de sesiones de otros usuarios.

Desde backend:

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider
Remove-Item Env:SIGFQ_TEST_ROLLBACK
```

Para probar manualmente, crear una cuenta ficticia e iniciar sesión con ella para generar historial.
Abrir Eliminar, verificar el bloqueo con un correo diferente y confirmar con el
correo mostrado. Usar solo cuentas descartables.
