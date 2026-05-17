# Deployment Guide

## Quick Reference

| Task | Command |
|------|---------|
| Dev start | `docker compose up` |
| Prod start | `docker compose -f docker-compose.prod.yml up -d` |
| Run migrations | `docker exec <backend_container> alembic upgrade head` |
| Health check | `curl http://localhost:8000/live` |
| DB readiness | `curl http://localhost:8000/ready` |
| ERP audit | `python scripts/erp-health-audit.py` |

---

## Environment Files

### Required files

| File | Purpose | How to create |
|------|---------|---------------|
| `.env.development` | Dev runtime config | Copy `.env.development.example` and fill |
| `.env.production` | Prod runtime config | Copy `.env.production.example` and fill ALL secrets |

### Required production secrets (non-negotiable)

```
SECRET_KEY=<64+ char random string>        # REQUIRED — app crashes if default
INITIAL_ADMIN_PASSWORD=<strong password>   # REQUIRED if SEED_INITIAL_ADMIN=true
POSTGRES_USER=<db user>
POSTGRES_PASSWORD=<strong password>
POSTGRES_DB=fmcg_erp
```

### Production must-set flags

```
ENVIRONMENT=production
AUTH_COOKIE_SECURE=true
PASSWORD_REQUIRE_SPECIAL=true
SEED_DEMO_DATA=false
```

The application validates these at startup and **refuses to start** if production guards fail.

---

## Development Startup

```bash
# 1. Copy env file
cp .env.development.example .env.development
# Edit .env.development — no secrets required for dev

# 2. Start all services
docker compose up

# 3. Services
#   backend: http://localhost:8000
#   frontend: http://localhost:3000
#   docs:     http://localhost:8000/docs
```

Migrations run automatically via `scripts/dev_migrate.py` on backend startup.

---

## Production Startup

### First-time setup (fresh/empty database)

Migration `20260517_0000` (squashed baseline) is the chain root. `alembic upgrade head`
works on a completely empty database — `prod_bootstrap.py` is no longer needed for
first deploys.

```bash
# 1. Create production env file with real secrets
cp .env.production.example .env.production
# Fill in ALL secrets — see "Required production secrets" above

# 2. Build images
docker compose -f docker-compose.prod.yml build

# 3. Start only database and redis (do NOT start backend yet)
docker compose -f docker-compose.prod.yml up -d db redis

# 4. Wait for DB to be healthy
docker compose -f docker-compose.prod.yml ps  # check db is "healthy"

# 5. Run migrations on empty DB (creates all 650+ tables via squashed baseline)
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 6. Start all services
docker compose -f docker-compose.prod.yml up -d

# 7. Verify health
curl http://localhost:8000/live    # → {"status":"ok"}
curl http://localhost:8000/ready   # → {"status":"ok","database":"connected"}
```

### Subsequent deployments

```bash
# 1. Pull/build new image
docker compose -f docker-compose.prod.yml build backend frontend

# 2. Run migrations (safe — Alembic is idempotent)
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 3. Replace running containers (zero-downtime with a load balancer)
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
```

---

## Database Migration Procedure

Migrations use Alembic. In production, never call `create_all` directly — the only
exception is `scripts/prod_bootstrap.py` which is explicitly guarded and runs only
on a completely empty database (see First-time setup above).

```bash
# Check current revision
alembic current

# Show pending migrations
alembic history --indicate-current

# Apply all pending migrations
alembic upgrade head

# Apply one step
alembic upgrade +1

# Downgrade one step (test before production use)
alembic downgrade -1
```

**Multi-replica warning:** if you run multiple backend replicas, ensure only one
runs `alembic upgrade head` at startup. Use a separate migration job or an
advisory lock strategy. The current prod Dockerfile runs migrations inside the
`CMD` — this is safe for single-replica but risky for simultaneous scaling.

---

## Rollback Procedure

### Code rollback

```bash
# Tag before every production deploy
git tag release-$(date +%Y%m%d-%H%M)

# Roll back to previous tag
git checkout <previous-tag>
docker compose -f docker-compose.prod.yml build backend frontend
# If schema changed, run downgrade first:
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
```

### Database rollback

Each Alembic migration has a `downgrade()` function.

```bash
# Downgrade to a specific revision
alembic downgrade <revision_id>

# Show revision IDs
alembic history
```

---

## Backup and Restore

### Backup

```bash
# Full DB dump
docker exec <db_container> pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Compressed
docker exec <db_container> pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore

```bash
# Stop backend to prevent writes during restore
docker compose -f docker-compose.prod.yml stop backend

# Restore
cat backup.sql | docker exec -i <db_container> psql -U $POSTGRES_USER $POSTGRES_DB

# Start backend
docker compose -f docker-compose.prod.yml start backend
```

---

## Health Endpoints

| Endpoint | Purpose | Touches DB |
|----------|---------|-----------|
| `GET /live` | Kubernetes liveness probe — is process alive | No |
| `GET /ready` | Kubernetes readiness probe — is DB connected | Yes (cached 8s) |
| `GET /health` | Legacy health endpoint | Yes (cached 8s) |
| `GET /metrics` | In-memory request metrics | No |

Healthcheck in Docker Compose uses `/live` to avoid DB dependency for liveness.

---

## Network / Port Exposure

### Development (`docker-compose.yml`)

| Port | Service | Exposed |
|------|---------|---------|
| 5432 | PostgreSQL | Yes (dev host only) |
| 6379 | Redis | Yes (dev host only) |
| 8000 | Backend | Yes |
| 3000 | Frontend | Yes |

### Production (`docker-compose.prod.yml`)

| Port | Service | Exposed |
|------|---------|---------|
| 5432 | PostgreSQL | **No** — internal network only |
| 6379 | Redis | **No** — internal network only |
| 8000 | Backend | Yes (put behind reverse proxy in prod) |
| 3000 | Frontend | Yes |

---

## Resource Limits

Both compose files specify `deploy.resources.limits`. Docker Compose V2 respects
these on Linux with cgroup v2. On Windows/macOS Docker Desktop they may be
informational only — verify with `docker stats` after startup.

Production limits (from `docker-compose.prod.yml`):

| Service | CPU | Memory |
|---------|-----|--------|
| db | 2 vCPU | 1 GB |
| redis | 0.5 vCPU | 256 MB |
| backend | 2 vCPU | 1 GB |
| frontend | 1 vCPU | 512 MB |

Adjust per actual server specs.

---

## Running the ERP Health Audit

```bash
python scripts/erp-health-audit.py

# Custom paths
python scripts/erp-health-audit.py --root /path/to/project --output /tmp/audit.md
```

### Interpreting findings

| Severity | Meaning | Action |
|----------|---------|--------|
| HIGH | Real risk in production path | Fix before deploying |
| MEDIUM | Service-layer unbounded query or low-risk pattern | Review and add limit |
| LOW | Minor issue | Address in next sprint |
| INFO | Missing env file | Copy example and fill |

After this hardening pass: **0 HIGH, ~500 MEDIUM** (mostly service-layer computations).

---

## Known Limitations

1. **Multi-replica migration race**: The prod Dockerfile runs `alembic upgrade head`
   inside CMD. With multiple replicas, the first one to win applies the migration;
   others should succeed idempotently but may collide on schema changes. Mitigation:
   use a Kubernetes init container or a separate migration job for multi-replica setups.

2. **Single-worker Redis fallback**: If Redis is unavailable, token blocklist and rate
   limiting fall back to in-memory dicts. This is safe for single-worker but does not
   share state across workers. Use Redis in all production deployments.

3. **Request timeout**: Default is 120s (dev) / 60s (production recommended). Streaming
   endpoints (if added) must set `REQUEST_TIMEOUT_SECONDS=0` or be excluded from the
   `_NO_TIMEOUT_PATHS` set in `backend/app/main.py`.

4. **Docker resource limits on non-Swarm**: `deploy.resources` is part of the Compose
   spec V3 and is applied by Docker Compose V2 on Linux cgroup v2. On Windows/macOS
   Desktop the limits render in `config` output but enforcement may vary.
