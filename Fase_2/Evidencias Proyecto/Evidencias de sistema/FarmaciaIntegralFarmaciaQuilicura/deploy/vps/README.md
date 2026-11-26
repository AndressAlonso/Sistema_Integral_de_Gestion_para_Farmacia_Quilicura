# VPS de pruebas SIGFQ

Dominio: https://sigfq.duckdns.org. Base inicial: commit 7049398.

Este despliegue utiliza datos ficticios y Mercado Pago de prueba. El modo
production de FastAPI protege cookies y desactiva el simulador; no habilita
cobros reales en Mercado Pago. La compra completa sigue pendiente de validar.

Desde la carpeta web:

```sh
bash deploy/vps/compose.sh config --quiet
bash deploy/vps/compose.sh build
bash deploy/vps/compose.sh up -d
bash deploy/vps/compose.sh ps -a
bash deploy/vps/compose.sh exec api python bootstrap_admin.py
```

Las migraciones se ejecutan antes de iniciar la API. El servicio migrate termina
con código 0; es normal que no quede ejecutándose. Solo web publica puertos
80/443. PostgreSQL y API se comunican por la red privada de Compose.
La comprobación interna de API valida HTTP, no sustituye las pruebas de DB.

Se requiere DNS A hacia la IPv4 del VPS y entrada TCP 80/443 tanto en Hostinger
como en el firewall del servidor. No configurar AAAA salvo IPv6 correctamente
enrutada hacia el mismo VPS. El certificado se obtiene automáticamente.

Configuración privada: /opt/sigfq/private/vps.env (permiso 600). No está en Git
ni en las imágenes. JWT y contraseña DB se generan una sola vez. No cambiarlos
sin un procedimiento de rotación, especialmente DB_PASSWORD tras inicializar DB.
No publicar la salida de `config` sin --quiet, porque puede contener secretos.

Los volúmenes pgdata, media y caddy_data persisten datos, fotos y certificados.
NO ejecutar `down -v`, pues eliminaría esos volúmenes.

Para activar pagos después de comprobar web y acceso interno, editar vps.env:
MP_ACCESS_TOKEN=credencial del vendedor de prueba
MP_WEBHOOK_SECRET=secreto de la aplicación
MP_CHECKOUT_ENABLED=true
MP_EXPIRATION_ENABLED=true

Actualizar Webhooks/Pagos de Mercado Pago:
https://sigfq.duckdns.org/api/payments/mercadopago/webhook

Después: `bash deploy/vps/compose.sh up -d api` (restart no relee variables).
No usar cuentas de producción. No abrir varios workers del vencimiento.

Backups, antes de migraciones o actualizaciones:

```sh
mkdir -p /opt/sigfq/backups
chmod 700 /opt/sigfq/backups
bash deploy/vps/compose.sh exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > /opt/sigfq/backups/sigfq.dump
chmod 600 /opt/sigfq/backups/sigfq.dump
bash deploy/vps/compose.sh exec -T api tar -czf - -C /app/media . > /opt/sigfq/backups/media.tar.gz
chmod 600 /opt/sigfq/backups/media.tar.gz
```

Usar nombres nuevos por fecha para conservar respaldos anteriores; copiar
respaldos fuera del VPS. Los respaldos contienen datos privados.

Después de la puesta en marcha, guardar estos archivos de despliegue en Git.
Nunca agregar vps.env ni archivos dump al repositorio.
