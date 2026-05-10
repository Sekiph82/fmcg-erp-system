# Deployment Notes

This project is an ERP/MES system and should be deployed with explicit production configuration.

## Production Environment

Start from the template:

```bash
cp .env.production.example .env.production
```

Required production values:

- `SECRET_KEY`: strong random value, not the development default.
- `POSTGRES_PASSWORD`: strong database password.
- `INITIAL_ADMIN_PASSWORD`: required when the first admin user is created.
- `AUTH_COOKIE_SECURE=true`: required for HTTPS cookie auth.
- `SEED_DEMO_DATA=false`: demo users are never allowed in production.
- `REDIS_URL=redis://redis:6379/0`: Redis is required for limiter/blocklist paths.

## Startup

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
```

The backend container runs:

```bash
alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker
```

The frontend container builds the Next.js app and serves it with `npm run start`.

## Migrations

Check migration state before deployment:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic heads
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic upgrade head
```

Runtime table creation is disabled by default. `AUTO_CREATE_TABLES=true` is only for emergency local development, not production.

## Database Exposure

The production Compose file does not publish PostgreSQL to the host by default. Keep database access inside the Docker network unless an operations team explicitly provisions a secured network path.

## Backup and Restore

Backup:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore to a controlled maintenance environment first:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB" < backup.sql
```

## Health and Logs

Health endpoints expose only service status:

- Backend: `GET /health`
- API health: `GET /api/v1/health`

Logs:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f backend
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f frontend
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f db
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f redis
```
