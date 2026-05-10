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

## Smoke Checks

Run these after startup:

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
