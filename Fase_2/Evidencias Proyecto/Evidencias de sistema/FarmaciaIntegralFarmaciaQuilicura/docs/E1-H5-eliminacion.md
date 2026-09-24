# E1-H5: eliminación inmediata y mejoras de sucursales

Ampliación autorizada: eliminación definitiva con confirmación del UUID.
La desactivación existente sigue disponible para conservar registros.
No hay plazo de recuperación, papelera ni eliminación programada.

## Contrato agregado

- Método y ruta: `POST /api/branches/{id}/delete`.
- Autenticación: cookie de sesión existente.
- Permiso: `sucursales.gestionar`, comprobado en backend.
- JSON: `{"confirmation_id":"UUID de la sucursal"}`.
- Éxito: `204`, sin cuerpo.
- Errores: `401` sin sesión, `403` sin permiso/origen no permitido,
  `404` inexistente, `409` usuarios o referencias asociadas,
  `422` confirmación inválida o diferente, `500` error genérico.

La eliminación bloquea la fila dentro de una transacción, comprueba usuarios
activos e inactivos y conserva las restricciones FK existentes. No elimina
usuarios en cascada. Las referencias de futuros módulos también deben usar
restricciones apropiadas para conservar su historial.

No se modificó el esquema ni se crearon migraciones. No se implementó auditoría;
su integración queda pendiente del módulo correspondiente. El borrado libera
el código único del registro eliminado; la desactivación conserva ese código.

## Interfaz

- Filtro inicial Activas, con opciones Todas e Inactivas.
- Dos tarjetas informativas sencillas: Activas e Inactivas, con recuentos globales.
  El selector Estado (Todas, Activas, Inactivas) es el único control de estado.
- Todos los diálogos ocupan el 98% del ancho y alto de pantalla, centrados y con contenido de ancho legible,
  desplazamiento interno y acciones al pie. Comparten el estilo `app-modal` con usuarios.
- Eliminación muestra nombre, código y UUID completo. El botón solo se habilita
  con la confirmación exacta; backend vuelve a comprobarla.
- Las respuestas de sucursales agregan `can_delete` (booleano calculado, sin columna
  nueva). Eliminar se muestra solo si es verdadero. Actualmente la relación que
  impide eliminar es usuario-sucursal, incluyendo usuarios inactivos. El listado y
  la eliminación reutilizan esa comprobación; futuros módulos deberán ampliar
  ambos al introducir nuevas dependencias. Las FK permanecen como protección final.
  Si una asignación posterior provoca un 409 al eliminar, la interfaz retira la acción.
- Código sugerido al crear a partir del nombre, o de la dirección si falta nombre.
  Se normaliza a mayúsculas sin acentos, con sufijos cuando ya existe en la lista.
  Es editable, no cambia automáticamente en edición y no modifica el UUID.
  La sugerencia no reserva el código: la validación y UNIQUE del backend/BD
  siguen resolviendo conflictos concurrentes al guardar.

## Comprobación

`npm.cmd run lint` y `npm.cmd run build` desde la raíz.
Desde backend, con PostgreSQL local y configuración existente:

```powershell
$env:SIGFQ_TEST_ROLLBACK = '1'
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check app tests
Remove-Item Env:SIGFQ_TEST_ROLLBACK
```

Las pruebas de eliminación crean registros ficticios en transacciones revertidas.
Cubren borrado de sucursales vacías activas/inactivas, confirmación incorrecta,
usuarios asociados activos/inactivos, repetición, autorización y origen.

Verificación del 23 de septiembre de 2026: 131 pruebas aprobadas, sin omisiones;
dos avisos de deprecación de dependencias. ESLint, Ruff y build/TypeScript aprobados.
La revisión visual interactiva en navegador queda pendiente.

Para probar manualmente, crear una sucursal ficticia sin usuarios, abrir Eliminar,
comprobar que un UUID diferente no habilita el botón, escribir el UUID mostrado
y confirmar. La fila debe desaparecer y los contadores deben actualizarse.
Usar solo registros descartables: el borrado es definitivo.
# Ficha de sucursal y reactivación

La tabla abre la ficha al pulsar el nombre; las acciones están dentro del modal.
Editar conserva el formulario y sus validaciones. Activar/desactivar requieren
confirmación; eliminar conserva la confirmación mediante ID y `can_delete`.
Confirmar estado/eliminación no guarda los cambios pendientes del formulario.

`POST /api/branches/{id}/activate`: sin cuerpo, con cookie y permiso
`sucursales.gestionar`; devuelve 200 con BranchResponse. Errores 401, 403 y 404.
Reactivar es idempotente y no cambia datos ni estado de los usuarios asignados.
No se modificó el esquema ni se crearon migraciones. Se mantienen los bloqueos
existentes de desactivación y eliminación. Los contratos anteriores no cambian.
# Usuarios asignados (E1-H4/E1-H5)

La ficha tiene un panel desplegable de consulta con buscador por nombre/correo,
filtro de estado y lista de nombre, correo, roles y estado. Consulta al abrir y
vuelve a consultar al cerrar/abrir; no cambia asignaciones ni edita usuarios.

`GET /api/branches/{id}/users`: cookie y permiso `sucursales.gestionar`, sin body.
200: `{ "users": [{ "id": "UUID", "name": "...", "email": "...",
"roles": ["Nombre del rol"], "is_active": true }] }`.
Incluye activos e inactivos únicamente de la sucursal solicitada; una lista vacía
es válida. Errores 401, 403, 404 y 422 para UUID inválido.
No expone hashes, sesiones ni datos de otras sucursales. Se reutiliza la FK
existente: no se modificó el esquema ni se crearon migraciones.
El listado y las respuestas de sucursal incluyen `assigned_users_count`: total
de usuarios asignados, activos e inactivos. Se calcula desde la relación existente
y se muestra en una columna de la tabla; no se persiste un contador nuevo.
