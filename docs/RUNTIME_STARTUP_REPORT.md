# Runtime Startup Report

Updated: 2026-05-17

## Symptoms

- `db`: healthy, `redis`: healthy
- `backend`: container up, UNHEALTHY
- `curl http://localhost:8000/live` → empty reply
- Inside container: `urllib.request.urlopen(...)` → `ConnectionRefusedError: [Errno 111] Connection refused`
- `frontend`: never starts (depends on `backend: service_healthy`)

Backend logs showed:
```
Uvicorn running on http://0.0.0.0:8000
Started reloader process using WatchFiles
```
But NOT:
```
Started server process [PID]
Application startup complete.
```

## Root Causes (in order)

### Root Cause 1: `--reload` + Docker Volume Mount on Windows

With `--reload`, uvicorn spawns a parent reloader and a child worker. The parent monitors `./backend:/app` via `watchfiles`. On Windows Docker Desktop (WSL2), volume-mounted directories generate file system events that watchfiles detects immediately after child startup. The child is killed before it can bind port 8000 → `ConnectionRefusedError` → healthcheck fails.

**Fix**: Removed `--reload` from `backend/Dockerfile.dev` CMD, added `--log-level info`.

### Root Cause 2: Missing `INITIAL_ADMIN_PASSWORD` in `.env.development`

`.env.development` was missing seed credentials. `seed_admin()` in lifespan raised `RuntimeError` (caught, but admin user never seeded). Login impossible after first start.

**Fix**: Added `INITIAL_ADMIN_PASSWORD`, `SEED_INITIAL_ADMIN`, and related fields to `.env.development`.

### Root Cause 3: Docker Compose Variable Substitution on Windows

When running `docker compose` without `--env-file`, `${POSTGRES_USER}` etc. in `docker-compose.yml` are empty strings on Windows. PostgreSQL starts but `pg_isready -U  -d ` (empty args) returns wrong results. Services that depend on `db: service_healthy` never start.

**Root fix**: Always use `docker compose --env-file .env.development` (enforced by `start-dev.bat`). Gordon additionally added `env_file: .env.development` to the db service and created a `.env` file (gitignored) as a safety net.

**Remaining fix**: Healthcheck defaults were `${POSTGRES_USER:-postgres}` (wrong). Fixed to `${POSTGRES_USER:-erp_user}` / `${POSTGRES_DB:-fmcg_erp}`.

### Root Cause 4: Migration Chain Broken for Fresh Databases

`alembic upgrade head` fails on any fresh database. The migration chain starts with `3c45d9071c98_initial_schema.py` which adds columns to `sales_orders`, but `sales_orders` never gets created by any migration. The second migration (`a1b2c3d4e5f6`) references `users`, `suppliers`, `products` etc. via FK — also never created by migrations.

Root cause: Alembic was introduced after the initial schema was already deployed via `Base.metadata.create_all()`. No migration creates the core tables.

**Fix**: `dev_migrate.py` now:
1. Fresh DB → `create_all()` + `alembic stamp head` (DEV ONLY, logged clearly)
2. Existing Alembic-tracked DB → `alembic upgrade head`
3. Existing create_all DB (no stamp) → reconcile + stamp + done
4. Production → always `alembic upgrade head`, fail loudly

### Root Cause 5: `dev_migrate.py` Missing `import app.models`

Gordon's `create_all()` replacement did not import `app.models`. `Base.metadata` had zero business tables registered. `create_all()` created nothing. Seeding failed: `permissions` table didn't exist.

**Fix**: New `dev_migrate.py` includes `import app.models` (line 49) which registers all 100+ model classes before `Base.metadata.create_all()` is called.

## Files Changed

| File | Change | Reason |
|------|--------|--------|
| `backend/Dockerfile.dev` | Removed `--reload`, added `--log-level info` | Fixes uvicorn child kill loop on Windows volume mount |
| `.env.development` | Added `INITIAL_ADMIN_PASSWORD` and other seed fields | Enables admin seeding |
| `backend/scripts/dev_migrate.py` | Full rewrite: Alembic-first + create_all bootstrap for fresh dev DBs | Gordon's version broke Alembic and imported no models |
| `backend/alembic/versions/3c45d9071c98_initial_schema.py` | Fixed bare `except:` → `except Exception:` | Gordon's guards were correct but bare except is unsafe |
| `docker-compose.yml` | Fixed healthcheck defaults (erp_user/fmcg_erp); kept Gordon's `env_file:` on db, `start_period: 90s`, resource increases | Gordon's defaults were wrong (postgres/postgres) |

## Gordon's Changes: What Was Kept vs Reverted

| Gordon's Change | Status |
|----------------|--------|
| `env_file: .env.development` on db service in docker-compose.yml | KEPT |
| Healthcheck defaults `:-postgres` | FIXED to `:-erp_user`/`:-fmcg_erp` |
| `start_period: 90s` for backend | KEPT (appropriate for large ERP startup) |
| Backend resource limits `cpus: 2.0, memory: 1G` | KEPT for dev |
| `3c45d9071c98_initial_schema.py` conditional guards | KEPT (correct logic) |
| `3c45d9071c98_initial_schema.py` bare `except:` | FIXED to `except Exception:` |
| `dev_migrate.py` pure `create_all()` replacement | REVERTED and REWRITTEN |
| Gordon's `.env` file (copy of `.env.development`) | LEFT (gitignored, harmless) |

## Verification Steps

```bash
# Full reset (dev only — destroys local DB volume):
docker compose --env-file .env.development down -v
docker compose --env-file .env.development up --build -d

# Wait ~60s for startup, then verify:
docker compose --env-file .env.development ps
curl http://localhost:8000/live    # expect {"status":"ok"}
curl http://localhost:8000/ready   # expect {"status":"ok","database":"connected"}

# Check backend logs for:
# DEV ONLY: fresh database — creating schema from SQLAlchemy models
# Dev baseline schema created and stamped to head
# Seed completed
# Application startup complete.
```

Expected login:
- Email: `admin@erp.local`
- Password: `Admin1234!`

## Remaining Risks

1. **Production fresh deploy**: If production database has never been initialized, `alembic upgrade head` will fail (same FK chain issue). A controlled `create_all()` + stamp is needed once, then Alembic manages incrementally. Document this for the ops team.

2. **Model/migration drift**: New models added to `app.models` won't have matching migrations. Running `alembic revision --autogenerate` will show these as pending tables. Developers must generate migrations for any model changes.

3. **`start-dev.bat` stability comment**: Line 221 says "lets uvicorn finish any in-progress reload" — outdated comment now that `--reload` is removed. Harmless but misleading.

## See Also

- `docs/MIGRATION_CHAIN_REPORT.md` — full migration dependency map and chain analysis
