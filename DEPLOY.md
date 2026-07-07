# HomeDrive Backend — Deploy

## Entorno de producción

- Servidor: **ironman** (`ssh c3jota@ironman` / `100.87.9.80`)
- Directorio: `~/homedrive/`
- Deploy mediante Docker Compose (imagen `homedrive-backend`)

## Estructura en el servidor

```
~/homedrive/
  docker-compose.yml   # en raíz del repo (SingleDrive/)
  .env                 # variables de entorno (no en git)
  db.sqlite3           # volumen Docker: db_data → /data/db.sqlite3
```

## Variables de entorno (`.env`)

```
DJANGO_SECRET_KEY=<50+ chars random>
ALLOWED_HOSTS=100.87.9.80,localhost,ironman,ironman.tail9ae84b.ts.net
USER_QUOTA_GB=100
PORT=80
```

## Primer despliegue

```bash
ssh c3jota@ironman
cd ~/homedrive
# Copiar .env (ver plantilla .env.example)
docker compose build
docker compose up -d
docker compose exec backend python manage.py createsuperuser
```

## Actualizar tras cambios en el backend

```bash
# Desde el Mac — rsync del código
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.env' --exclude='venv' --exclude='db.sqlite3' --exclude='media' \
  ./single-drive-be/ c3jota@ironman:~/homedrive/

# En el servidor
ssh c3jota@ironman
cd ~/homedrive
docker compose build backend worker
docker compose up -d backend worker
```

## Servicios Docker

| Servicio   | Imagen             | Función                              |
|------------|--------------------|--------------------------------------|
| `backend`  | homedrive-backend  | Django + Gunicorn en puerto 8000     |
| `worker`   | homedrive-worker   | Huey consumer (thumbnails, hashing)  |
| `frontend` | homedrive-frontend | nginx sirviendo Angular + proxy API  |

## Persistencia (volúmenes Docker)

- `db_data` → `/data/db.sqlite3` + `/data/huey.db`
- `media_files` → `/media/` (uploads y thumbnails)

## URLs de la API

- Interna (Tailscale): `http://100.87.9.80/api/v1/`
- Pública (Funnel): `https://ironman.tail9ae84b.ts.net/api/v1/`
- Admin Django: `https://ironman.tail9ae84b.ts.net/admin/`

## Logs

```bash
docker compose logs backend --tail=50 -f
docker compose logs worker --tail=50 -f
```

## Migraciones

Las migraciones corren automáticamente al arrancar el contenedor via `entrypoint.sh`.
Para lanzarlas manualmente:

```bash
docker compose exec backend python manage.py migrate
```

## Notas importantes

- `MEDIA_URL = '/uploads/'` — los archivos del usuario se sirven en `/uploads/`, NO en `/media/`
  (esto evita conflicto con la carpeta `media/` que genera el build de Angular para fonts/assets)
- El healthcheck verifica `GET /admin/login/` → 200
