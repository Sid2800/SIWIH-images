# Despliegue de SIWIH Images

Este servicio conserva dos elementos inseparables:

- Los metadatos en la base MySQL `siwi_image`.
- Los archivos y miniaturas bajo `MEDIA_ROOT`.

Un respaldo o una restauracion debe incluir ambos elementos.

## 1. Preparacion

1. Desplegar un commit revisado de la rama aprobada, nunca una carpeta con
   cambios locales.
2. Crear un entorno virtual con Python 3.12 e instalar `requirements.txt`.
3. Copiar `.env.example` a `/etc/siwi-images.env`, completar sus valores reales
   y protegerlo con permisos `600`. El archivo no debe vivir en Git.
4. Crear los directorios persistentes y asignarlos al usuario del servicio:

```bash
sudo install -d -o siwi-images -g siwi-images /data/media/images
sudo install -d -o siwi-images -g siwi-images /var/lib/siwi-images/staticfiles
sudo install -d -o siwi-images -g siwi-images /var/log/siwi-images
```

Si el servidor mantiene temporalmente el usuario `sid280`, sustituir
`siwi-images` por ese usuario. Para produccion se recomienda una cuenta de
servicio sin acceso interactivo.

## 2. Verificacion previa

```bash
set -a
source /etc/siwi-images.env
set +a

python manage.py check
python manage.py check --deploy
python manage.py test api_images --settings=siwi_image.test_settings
python manage.py migrate --plan
python manage.py collectstatic --noinput
```

En un dominio interno, `check --deploy` puede conservar únicamente la
advertencia `security.W021`: no se activa HSTS preload porque los dominios
internos no pertenecen a la lista publica de precarga de los navegadores.

Antes de migrar, guardar un respaldo consistente:

```bash
mysqldump --single-transaction --routines --triggers siwi_image \
  > siwi_image_antes_despliegue.sql
tar -C /data/media -czf siwi_images_media_antes_despliegue.tar.gz images
```

No ejecutar `flush`, `truncate` ni eliminar `media/` durante un despliegue.
Las tablas y carpetas de RX y usuarios comparten este servidor.

## 3. Migracion

```bash
python manage.py migrate
python manage.py showmigrations api_images
```

Las migraciones de Equipos esperadas son:

- `0003_imagendispositivo`
- `0004_fichabajadispositivo`

## 4. Gunicorn con systemd

Ejemplo de `/etc/systemd/system/siwi-images.service`:

```ini
[Unit]
Description=Gunicorn SIWIH Images
After=network.target mysql.service
RequiresMountsFor=/data/media/images

[Service]
Type=simple
User=siwi-images
Group=siwi-images
WorkingDirectory=/opt/siwih-images
EnvironmentFile=/etc/siwi-images.env
ExecStart=/opt/siwih-images/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    siwi_image.wsgi:application
Restart=on-failure
RestartSec=5
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Aplicar y comprobar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now siwi-images
sudo systemctl status siwi-images --no-pager
journalctl -u siwi-images -n 100 --no-pager
```

`runserver` se usa unicamente para desarrollo y demostraciones.

## 5. Proxy y archivos

Nginx debe:

- Enviar la API a `http://127.0.0.1:8000`.
- Servir `/media/` desde `/data/media/images/`.
- Servir `/static-images/` desde el `STATIC_ROOT` configurado.
- Permitir cuerpos de 20 MB (`client_max_body_size 20m`) para admitir una
  imagen de 15 MB junto con la envoltura multipart.
- Conservar `Host`, `X-Forwarded-For` y `X-Forwarded-Proto`.
- Aceptar conexiones solo desde SIWIH principal o desde la subred interna
  autorizada. `/media/` no debe publicarse en Internet.
- Restringir `/api_images/admin/` a la red de administracion.
- Limitar intentos contra `/api_images/api/token/` para reducir ataques de
  fuerza bruta.

El JWT es una credencial reutilizable durante su vigencia. En produccion la
conexion entre SIWIH principal y Nginx debe usar HTTPS. HTTP sin cifrado solo
es admisible en una red privada dedicada, filtrada por firewall y aprobada por
el responsable de infraestructura; la LAN general del hospital no basta.

Ejemplo orientativo de Nginx (se deben sustituir dominio, IP y certificados):

```nginx
limit_req_zone $binary_remote_addr zone=siwi_images_token:10m rate=5r/m;

server {
    listen 443 ssl;
    server_name imagenes.siwih.local;

    ssl_certificate /etc/ssl/siwi-images/fullchain.pem;
    ssl_certificate_key /etc/ssl/siwi-images/privkey.pem;
    client_max_body_size 20m;

    location = /api_images/api/token/ {
        allow IP_SIWIH_PRINCIPAL;
        deny all;
        limit_req zone=siwi_images_token burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api_images/admin/ {
        allow SUBRED_ADMINISTRACION;
        deny all;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api_images/ {
        allow IP_SIWIH_PRINCIPAL;
        deny all;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media/ {
        allow IP_SIWIH_PRINCIPAL;
        deny all;
        alias /data/media/images/;
        try_files $uri =404;
    }

    location /static-images/ {
        alias /var/lib/siwi-images/staticfiles/;
        try_files $uri =404;
    }
}
```

SIWIH principal debe usar en `IMAGE_SERVER_URL` la direccion interna estable
del proxy, no un tunel SSH ni `127.0.0.1:8001`.

## 6. Prueba de humo

La ruta de salud no requiere JWT y no expone datos:

```bash
curl --fail http://127.0.0.1:8000/api_images/health/
```

Debe responder `{"estado":"ok"}`. Luego se comprueba, con la cuenta de
servicio de SIWIH principal, la obtencion del JWT y una consulta de imagenes.
No es necesario crear registros ficticios en produccion.

## 7. Operacion

- Rotar `/var/log/siwi-images/siwi_images.log` con `logrotate`.
- Vigilar espacio libre en el volumen de `MEDIA_ROOT` y en MySQL.
- Respaldar diariamente MySQL y `MEDIA_ROOT` bajo la misma ventana de tiempo.
- Mantener el usuario JWT sin permisos de administrador y con una contrasena
  exclusiva del servicio.
- Cambiar inmediatamente la credencial si aparece en una terminal compartida,
  captura o repositorio.

Ejemplo de `/etc/logrotate.d/siwi-images`:

```text
/var/log/siwi-images/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 siwi-images siwi-images
}
```

## 8. Vuelta atras

Si falla la aplicacion, restaurar primero el commit anterior y reiniciar
Gunicorn. No revertir migraciones ni borrar archivos automaticamente. Si hubo
escrituras nuevas, evaluar juntos el respaldo de MySQL y el de `MEDIA_ROOT`
antes de restaurarlos para no desincronizar registros y archivos.
