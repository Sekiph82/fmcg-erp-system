# Runtime Startup Report

Investigated: 2026-05-17

## Symptoms

- `db`: healthy, `redis`: healthy
- `backend`: container up, UNHEALTHY — `curl http://localhost:8000/live` → empty reply
- Inside container: `urllib.request.urlopen('http://localhost:8000/live')` → `ConnectionRefusedError: [Errno 111] Connection refused`
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

## Root Cause

**`--reload` + Docker volume mount on Windows Docker Desktop (WSL2)**

With `--reload`, uvicorn spawns a parent reloader process and a child worker:
- Parent: monitors file changes via `watchfiles`, logs "Started reloader process"
- Child: imports `app.main`, binds port 8000, logs "Started server process"

On Windows Docker Desktop with a host-mounted volume (`./backend:/app`), the `watchfiles` Rust `notify` backend detects file system events on the WSL2-bridged volume. These events can fire immediately after child startup (before the child finishes importing all 100+ endpoint modules and binding port 8000). The parent kills the child on each event and respawns — creating an infinite kill/respawn loop where the child never survives long enough to bind.

ConnectionRefusedError (not "connection closed") confirms port 8000 was **never bound** — the child is killed during the import phase, before uvicorn calls `socket.bind()`.

## Secondary Issue

`.env.development` was missing `INITIAL_ADMIN_PASSWORD`. The `seed_admin()` call in the FastAPI lifespan raises `RuntimeError("INITIAL_ADMIN_PASSWORD is required...")` which is caught in a try/except — server still starts, but no admin user is seeded. Login would be impossible on first run.

## Files Changed

### `backend/Dockerfile.dev` — removed `--reload`

```diff
-CMD ["sh", "-c", "python scripts/dev_migrate.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
+CMD ["sh", "-c", "python scripts/dev_migrate.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"]
```

`--reload` is not reliable with Docker volume mounts on Windows. For hot reload during development, restart the container instead, or run `uvicorn` directly on the host.

### `.env.development` — added missing seeding fields

Added `INITIAL_ADMIN_PASSWORD`, `SEED_INITIAL_ADMIN`, `SEED_DEMO_DATA`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_FULL_NAME`, `DEMO_USER_PASSWORD` — copied from `.env.development.example`.

## Verification Steps

After pulling this change, rebuild and restart:

```bash
docker compose --env-file .env.development down
docker compose --env-file .env.development up --build -d
# Wait ~30s, then:
docker compose --env-file .env.development ps
curl http://localhost:8000/live
docker inspect fmcg-erp-system-main-backend-1 --format="{{json .State.Health}}"
```

Expected:
- `backend` status: `healthy`
- `curl` returns: `{"status":"ok"}`
- Health state: `Status: "healthy"`
- `frontend` starts automatically once backend is healthy

## If the Issue Persists

If removing `--reload` does not fix it, run the import diagnostic inside the container:

```bash
docker compose --env-file .env.development exec backend sh -c \
  "python -X faulthandler -c 'import app.main; print(\"IMPORT_OK\")'"
```

A crash here (not `IMPORT_OK`) means one of the 100+ endpoint modules fails to import. The traceback will identify the exact module.
