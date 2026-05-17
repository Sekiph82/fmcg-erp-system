# FMCG ERP System

Enterprise ERP/MES platform for FMCG factory operations, inventory, production, procurement, sales, finance, quality, utilities, reporting, and AI-assisted optimization.

## Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, async SQLAlchemy, asyncpg |
| Frontend | Next.js 14, TypeScript, Tailwind |
| Database | PostgreSQL 16 |
| Cache | Redis |
| Container | Docker Compose |

## Local Development

### Prerequisites

- Docker Desktop
- Docker Compose

### Windows start

```bat
copy .env.development.example .env.development
start-dev.bat
```

The batch file starts Docker Desktop when needed, starts PostgreSQL, Redis, backend, and frontend, then opens the login page.

### Manual Docker start

```bash
copy .env.development.example .env.development
docker compose --env-file .env.development up --build
```

On macOS/Linux use:

```bash
cp .env.development.example .env.development
docker compose --env-file .env.development up --build
```

## Local URLs

- Frontend login: http://localhost:3000/login
- Backend health: http://localhost:8000/health
- Backend docs: http://localhost:8000/docs
- Compose status: `docker compose --env-file .env.development ps`

## Development Login

Default credentials (set in `.env.development.example` and copied to `.env.development`):

| Field    | Value              |
| -------- | ------------------ |
| Username | `admin`            |
| Password | `Admin1234!`       |

**Important:** Login checks the PostgreSQL database, not the `.env.development` file directly. The password in `.env.development` is only used when the admin user is first created, or when `SYNC_INITIAL_ADMIN_PASSWORD=true` (the default in `.env.development.example`).

With `SYNC_INITIAL_ADMIN_PASSWORD=true`, the backend re-hashes the admin password from `INITIAL_ADMIN_PASSWORD` on every startup, so the DB always matches the env file in development.

If you started the project before this flag existed (old DB with a different password), run the manual reset:

```bat
docker compose --env-file .env.development exec backend python scripts/reset_dev_admin_password.py
```

Other useful commands:

```bat
:: Start
start-dev.bat

:: Smoke test login
test-login.bat

:: Reset local admin password manually
docker compose --env-file .env.development exec backend python scripts/reset_dev_admin_password.py

:: Full local DB reset (destroys all local data)
docker compose --env-file .env.development down -v
docker compose --env-file .env.development up --build
```

## Smoke Checks

```bash
docker compose --env-file .env.development exec backend python -c "import app.main; print('backend import ok')"
curl -i http://localhost:8000/health
curl -I http://localhost:3000/login
curl -i -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=bad&password=bad"
```

The bad-login check should return `401`. It should not return an empty response.

## Environment Files

- `.env.development.example` is the committed template for local development.
- `.env.production.example` is the committed template for production deployment.
- `.env.development` and `.env.production` are local secrets files and must stay uncommitted.

Important local settings:

- `SEED_DEMO_DATA=false` by default.
- `INITIAL_ADMIN_PASSWORD` is required before the first admin user can be created.
- `AUTH_RETURN_TOKEN_IN_BODY=false` because auth uses HttpOnly cookies.
- `AUTO_CREATE_TABLES=false`; schema changes should go through Alembic migrations.

## Production

Production uses separate Dockerfiles and Compose:

```bash
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
```

Production guards reject unsafe defaults such as demo seed data, default secrets, insecure auth cookies, and a missing initial admin password.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment, migration, backup, Redis, and database exposure notes.

## Project Structure

```text
backend/                 FastAPI application
frontend/                Next.js application
docker-compose.yml       Development Compose file
docker-compose.prod.yml  Production Compose file
.env.development.example Development environment template
.env.production.example  Production environment template
```
