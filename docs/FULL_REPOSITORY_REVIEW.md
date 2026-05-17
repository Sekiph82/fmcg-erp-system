# Full Repository Review

**Date:** 2026-05-17  
**Reviewer:** Claude (senior architect, security auditor, backend/frontend/DevOps/DB/QA perspective)  
**Scope:** Full repository — `fmcg-erp-system-main`  
**Git status:** Clean (0 uncommitted changes)  
**Alembic:** At head (`20260516_0060`), single head, 80 total migrations

---

## 1. Executive Summary

The FMCG ERP is a substantial full-stack enterprise system with a FastAPI backend, Next.js 14 frontend, PostgreSQL 16, Redis, and Docker Compose for both dev and production. The system has undergone recent hardening (security audit cleared), page consolidation (D=0 duplicate UI pages), and runtime startup stabilization.

**Current state: Runnable locally, NOT production-ready.**

The system can be started locally using `start-dev.bat` and all core flows work (login, dashboard, RBAC). However, several architectural constraints make production deployment risky without additional work: the migration chain cannot bootstrap a fresh production database, there are unbounded list queries across 35+ CRUD files, 2FA OTP delivery is an unimplemented TODO, and the production first-deploy procedure is undocumented and untested.

No HIGH security findings from the prior audit remain open. One new CRITICAL finding was discovered and fixed in this session (`UserRead.email: EmailStr` causing `/auth/me` 500 on `.local` TLD emails).

---

## 2. Current Project Health Score

| Category | Score | Notes |
|----------|-------|-------|
| **Backend code quality** | 7/10 | Solid structure, good auth, unbounded queries in CRUD |
| **Frontend code quality** | 8/10 | Clean build, TypeScript passes, cookie auth correct |
| **Security** | 7/10 | Good auth hardening, 2FA OTP not wired, default SECRET_KEY in dev |
| **Database/migrations** | 5/10 | Works via workaround; production fresh deploy broken |
| **DevOps/Docker** | 8/10 | Dev startup solid, prod well-configured, outdated comments |
| **Tests** | 6/10 | 35+ test files but no integration tests with real DB |
| **Documentation** | 8/10 | Extensive docs folder, README good |
| **Production readiness** | 4/10 | NOT ready — see critical issues |
| **Local dev experience** | 8/10 | start-dev.bat works, login works, demo users seed |

**Overall: 6.7/10 — Good foundation, significant gaps before production.**

---

## 3. Critical Issues

### C1. Production Fresh-Database Deploy Is Broken

**Severity:** CRITICAL  
**Files:** `backend/Dockerfile.prod`, `backend/scripts/dev_migrate.py`, `backend/alembic/versions/`

**Problem:** `docker-compose.prod.yml` runs `alembic upgrade head` on startup. Migration `3c45d9071c98` (the base migration) tries to `ALTER TABLE sales_orders` — a table that doesn't exist on a fresh DB. The subsequent migration `a1b2c3d4e5f6` creates tables with FK references to `users`, `suppliers`, `products` etc. — also never created by any migration. Alembic was introduced after the initial schema existed.

**Result:** Any first-ever production deployment will fail at container startup. There is no documented bootstrap procedure for production.

**Fix required (manual decision):**
Option A (Recommended): Create a `scripts/prod_bootstrap.py` that runs `create_all()` + `stamp head` once, guarded by an explicit `BOOTSTRAP_PRODUCTION=true` flag and a DB emptiness check. Document in `docs/DEPLOYMENT.md`.
Option B: Export the current dev schema as SQL and apply it manually before Alembic takes over.

**Do NOT:** Run `dev_migrate.py` in production (it has explicit production guard, but the architecture issue remains).

---

### C2. `UserRead.email: EmailStr` Fails on `.local` TLD Emails (FIXED THIS SESSION)

**Severity:** CRITICAL → FIXED  
**File:** `backend/app/schemas/user.py`  
**Fix applied:** `UserRead.email` overridden to `str`. Pydantic's `EmailStr` re-validates stored data on read; `admin@erp.local` was rejected because `.local` is a reserved TLD. Output schemas should not re-validate stored data.

---

## 4. High-Priority Issues

### H1. 2FA OTP Delivery Is a TODO — Feature Works But OTP Never Sent

**Severity:** HIGH  
**File:** `backend/app/api/v1/endpoints/auth.py` line ~109  
**Code:**
```python
challenge_code = totp_utils.generate_otp()
# TODO: dispatch OTP via notification service
```
TOTP (authenticator app) works because the user already has the secret. SMS/Email 2FA generates a code but never sends it. Users enabled on SMS/Email 2FA cannot complete login.

**Fix:** Wire the challenge code into the notification service or email endpoint. Until then, document that only TOTP 2FA is functional; disable SMS/Email 2FA options in the UI if not wired.

---

### H2. Unbounded List Queries in 35+ CRUD Files

**Severity:** HIGH  
**Files:** 35 CRUD files in `backend/app/crud/` call `.scalars().all()` without pagination guards  
**Examples:** `audit.py:56`, `boiler.py:87`, `chemical_treatment.py:105,211,422`, `delivery.py:25,105`, `esg.py:33,112,164...`

**Risk:** For small factories this is fine. Under load (1M+ rows in audit or ESG tables), list endpoints will OOM the backend container (memory limit: 1GB).

**Fix:** Add `limit: int = 500, offset: int = 0` parameters and `.limit(limit).offset(offset)` to all unbounded list queries. Also add export streaming for bulk data endpoints.

---

### H3. `get_db` Dependency Has No Rollback on Exception

**Severity:** HIGH  
**File:** `backend/app/db/session.py` lines 31–37  
**Current code:**
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```
If an exception occurs mid-transaction, the session is closed without explicit rollback. SQLAlchemy async sessions do rollback on context manager exit, but the explicit `finally: close()` pattern exits without the context manager's cleanup. This can leave partial transactions.

**Fix:**
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### H4. `start-dev.bat` Line 226 Comment Is Outdated

**Severity:** HIGH (misleading for future devs, causes confusion)  
**File:** `start-dev.bat` line 226  
**Current:** `:: Brief stability pause — lets uvicorn finish any in-progress reload`  
**Problem:** `--reload` was removed from `Dockerfile.dev`. Uvicorn no longer has reload. The comment implies reload is still happening.  
**Fix:** Update to `:: Brief pause to allow uvicorn server process to fully initialize`

---

### H5. Production `alembic upgrade head` Has No Multi-Replica Safety

**Severity:** HIGH  
**File:** `backend/Dockerfile.prod`  
**Problem:** `CMD ["sh", "-c", "alembic upgrade head && gunicorn ..."]` runs migrations at startup. If 3+ replicas start simultaneously (Docker Swarm, Kubernetes), all run migrations concurrently. Alembic has advisory locks but only in newer SQLAlchemy setups.  
**Fix:** Run migration as a separate init container or pre-deploy job, not as part of the app CMD. This is standard practice for multi-replica deployments.

---

## 5. Medium-Priority Issues

### M1. `SECRET_KEY` Default in Dev (Expected but Risky if Dev .env Used in Prod)

**File:** `.env.development.example` — `SECRET_KEY=change-this-to-a-random-secret-key`  
The production guard in `config.py` correctly rejects this key when `ENVIRONMENT=production`. Risk is only if someone incorrectly sets `ENVIRONMENT=production` while using the dev env file. Production guard covers this.  
**Status:** Production guard covers. No change needed, documented for awareness.

---

### M2. DB Connection Pool Too Small for Multi-User Production

**File:** `backend/app/core/config.py`  
Dev default: `DATABASE_POOL_SIZE=5, DATABASE_MAX_OVERFLOW=10` (15 total connections).  
Prod `docker-compose.prod.yml` overrides: `DATABASE_POOL_SIZE=20, DATABASE_MAX_OVERFLOW=20` (40 total).  
For a single replica this is fine. For 2+ replicas, connection count multiplies. PostgreSQL default `max_connections=100` becomes a bottleneck at 3 replicas (3×40=120).  
**Fix:** Set `DATABASE_POOL_SIZE=10, DATABASE_MAX_OVERFLOW=10` per replica in production and ensure Postgres `max_connections` is set appropriately.

---

### M3. Request Timeout 120s Is Too Long for Production

**File:** `backend/app/core/config.py`  
`REQUEST_TIMEOUT_SECONDS: int = 120` applies to all non-health endpoints. For an ERP with large exports this may be needed for some endpoints, but it's too long as a global default.  
**Fix:** Comment in config says "recommended: 60 in production". Set `REQUEST_TIMEOUT_SECONDS=60` in `.env.production.example` and document per-endpoint timeout overrides for bulk exports.

---

### M4. Frontend 401 Interceptor Uses `window.location.href` (Hard Redirect)

**File:** `frontend/src/lib/api.ts` line 21  
```typescript
window.location.href = "/login";
```
This hard-redirect on 401 loses any form state, works inconsistently with SSR, and does not propagate through Next.js router (no route animation, no history state). During SSR `typeof window === "undefined"` guard prevents a crash but the request still fails silently.  
**Fix:** Use Next.js `router.push("/login")` via a context or singleton, or suppress the redirect for certain API calls (e.g., the initial `getMe` probe).

---

### M5. 2FA Session Token in sessionStorage

**File:** `frontend/src/context/AuthContext.tsx` lines 47–48  
```typescript
sessionStorage.setItem("2fa_session_token", res.session_token);
```
This is a short-lived temporary token for a pending 2FA challenge. Using `sessionStorage` is acceptable (not persisted across tabs, not HttpOnly but not a permanent credential). Low risk since TOTP 2FA is the only active method.  
**Status:** Acceptable for now. Document as known limitation when SMS/Email 2FA is enabled.

---

### M6. `AUTO_CREATE_TABLES` Path in `main.py` Lifespan Never Triggers

**File:** `backend/app/main.py` lines 40–48  
When `AUTO_CREATE_TABLES=true` AND `ENVIRONMENT=development`, `create_all()` is called in lifespan. But `.env.development.example` sets `AUTO_CREATE_TABLES=false`. And `dev_migrate.py` already creates tables before uvicorn starts. This path is dead code in current setup.  
**Status:** Not harmful, just unnecessary complexity. Can be removed in cleanup phase.

---

### M7. `seed_admin` Called on Every Startup (Slow for Large Permission Sets)

**File:** `backend/app/main.py` lifespan, `backend/app/db/seed.py`  
Every backend startup runs a full permission/role upsert (459 permissions × 35 roles). With `on_conflict_do_nothing` this is safe but adds ~200ms to startup time and generates significant DB load.  
**Fix:** Add a startup check: if permission count in DB matches expected count and roles are current, skip seeding. Or run seeding only on version mismatch.

---

### M8. Missing CI/CD Pipeline

No `.github/workflows/` or other CI configuration found. Without CI, there is no automated lint, type-check, test, or migration validation on PRs.  
**Fix:** Add a basic GitHub Actions workflow with: backend `python -m compileall`, `pytest`, `alembic check`; frontend `tsc --noEmit`, `npm run build`.

---

### M9. Production `docker-compose.prod.yml` Uses `env_file: .env.production` Without Fallback

**File:** `docker-compose.prod.yml`  
Both `backend` and `frontend` services reference `env_file: .env.production`. If this file is missing, docker-compose fails silently (or with a confusing error). The `db` service has NO `env_file` — it relies entirely on `${POSTGRES_USER}` variable substitution from `--env-file .env.production` CLI flag.  
**Fix:** Add `env_file: .env.production` to the `db` service in `docker-compose.prod.yml` (mirrors the dev compose pattern) OR document clearly that `--env-file .env.production` is required.

---

### M10. No Next.js Middleware for Auth Routing

No `frontend/src/middleware.ts` exists. Auth protection is handled by `ProtectedRoute` React component client-side. This means unauthenticated users see a flash of protected content before redirect. It also means SEO crawlers can reach protected pages.  
**Fix:** Add Next.js middleware to redirect unauthenticated requests to `/login` for `/dashboard/*` routes. This is a standard Next.js pattern.

---

## 6. Low-Priority Cleanup

### L1. `start-dev.bat` outdated "in-progress reload" comment (line 226)
Already noted in H4. Easy single-line fix.

### L2. `backend/app/main.py` has `AUTO_CREATE_TABLES` dead code path
The `if settings.AUTO_CREATE_TABLES` block is never reached. Can be removed to reduce confusion.

### L3. `TASKS.md` references dozens of completed tasks that are stale
Large file, not summarized. Should be archived or reset after this review.

### L4. `docs/RUNTIME_STARTUP_REPORT.md` mentions "remains" risk about production fresh deploy
This is documented but the fix is not yet in place. Track in FIX_ROADMAP.md.

### L5. `backend/alembic/versions/3c45d9071c98_initial_schema.py` uses bare `except Exception: pass`
The `try: op.create_index(...) except Exception: pass` pattern silently swallows all errors including DB connectivity failures. Should log a warning at minimum.

### L6. Module-level SAWarnings from SQLAlchemy relationship overlaps
Logged on every backend start:
```
relationship 'DimValue.children' will copy column dim_values.id to column dim_values.parent_id
```
These are warnings about `overlaps=` parameter missing on self-referential relationships. Add `overlaps="parent"` to affected relationships to silence them.

### L7. Frontend login page image uses fixed `width=64 height=64`
`frontend/src/app/login/page.tsx`: The logo uses fixed pixel dimensions without `fill`. This is correct and intentional (standalone image, not CSS-sized). The `priority` attribute is set correctly.

### L8. `backend/app/core/config.py` has `model_config` with double env_file
```python
model_config = SettingsConfigDict(env_file=(".env", ".env.development"), extra="ignore")
```
Pydantic-settings reads both `.env` and `.env.development`. In production the `.env.development` file won't exist (and `.env` will). This works but is confusing. In Docker, env vars are injected via `env_file:` in compose, so the pydantic env_file setting is irrelevant. Low risk.

### L9. `frontend/next.config.mjs` is completely empty except `output: "standalone"`
No image domains, no headers, no rewrites. For a production ERP this likely needs:
- `images.domains` or `remotePatterns` if any external images
- Security headers (though backend adds them, frontend should too for SSR pages)
- API URL rewrite to avoid CORS for production deployments with same-domain reverse proxy

### L10. Redis has no password in dev or prod compose files
Both `docker-compose.yml` and `docker-compose.prod.yml` start Redis with no authentication. For production behind a firewall this is typical but should be documented. Redis port is not exposed in prod compose (correct).

---

## 7. Exact Affected Files

| Priority | File | Issue |
|----------|------|-------|
| CRITICAL | `backend/Dockerfile.prod` | Production CMD runs alembic on fresh DB → fails |
| CRITICAL | `backend/alembic/versions/` (all) | No migration creates base tables |
| FIXED | `backend/app/schemas/user.py` | `UserRead.email: EmailStr` → changed to `str` |
| HIGH | `backend/app/api/v1/endpoints/auth.py:109` | 2FA OTP not dispatched |
| HIGH | `backend/app/crud/*.py` (35 files) | Unbounded `.all()` queries |
| HIGH | `backend/app/db/session.py:31-37` | No rollback on exception |
| HIGH | `start-dev.bat:226` | Outdated `--reload` comment |
| HIGH | `backend/Dockerfile.prod` | No multi-replica migration safety |
| MEDIUM | `frontend/src/lib/api.ts:21` | Hard redirect on 401 |
| MEDIUM | `backend/app/main.py:40-48` | Dead `AUTO_CREATE_TABLES` code path |
| MEDIUM | `backend/app/db/seed.py` | Full upsert every startup |
| MEDIUM | `docker-compose.prod.yml` | `db` service missing `env_file` |
| LOW | `backend/app/crud/chemical_treatment.py:151` | SAWarning overlaps |
| LOW | `backend/alembic/versions/3c45d9071c98_initial_schema.py` | Silent `except Exception: pass` |

---

## 8. Exact Recommended Fixes

### Fix C1: Production Bootstrap Script
Create `backend/scripts/prod_bootstrap.py`:
```python
"""
Production one-time schema bootstrap.
Run ONCE on a fresh production database before first deployment.
Guard: refuses to run if ANY tables already exist.
"""
import asyncio, sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import command
from alembic.config import Config

# ... checks DB is empty, runs create_all(), stamps head, refuses if not empty
```
Add to `docs/DEPLOYMENT.md`: "Fresh production deploy requires running prod_bootstrap.py once."

### Fix H3: Add rollback to get_db
In `backend/app/db/session.py`:
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Fix H4: Update start-dev.bat comment
Line 226: Change comment to `:: Brief pause to allow uvicorn to fully initialize`

### Fix H2: Add pagination to CRUD list functions
In each CRUD file, add `limit: int = 500, offset: int = 0` parameter and chain `.limit(limit).offset(offset)` to the select before `.all()`.

### Fix M4: Fix 401 redirect in API client
```typescript
// frontend/src/lib/api.ts
if (error.response?.status === 401 && typeof window !== "undefined") {
  // Use Next.js router, not hard location redirect
  const { default: Router } = await import("next/router");
  Router.push("/login");
}
```

### Fix M9: Add env_file to db in prod compose
```yaml
# docker-compose.prod.yml
db:
  env_file: .env.production
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
```

---

## 9. What Can Be Fixed Automatically

These can be applied directly without manual decision:

- [x] `UserRead.email: str` override — **DONE this session**
- [ ] `start-dev.bat` line 226 comment update
- [ ] `get_db` rollback on exception
- [ ] `docker-compose.prod.yml` db service `env_file`
- [ ] SAWarning overlaps on self-referential relationships
- [ ] Remove dead `AUTO_CREATE_TABLES` block from `main.py`

---

## 10. What Needs Manual Decision

- **Production bootstrap strategy**: create_all+stamp vs SQL dump vs dedicated migration job container
- **2FA OTP delivery**: which notification service to wire (email vs SMS vs Twilio)
- **Pagination defaults**: what default page size is appropriate for FMCG data volumes
- **Redis password**: whether to enable Redis AUTH in production
- **Multi-replica migration strategy**: init container vs pre-deploy script vs current single-instance assumption
- **Next.js middleware**: whether to add SSR-level auth guard or keep client-side ProtectedRoute

---

## 11. Safe Repair Order

```
Phase 0 — Immediate safe fixes (no risk)
  1. Fix start-dev.bat comment (line 226)
  2. Add rollback to get_db
  3. Add env_file to prod compose db service
  4. Fix SAWarning overlaps

Phase 1 — Database/migration hardening
  5. Write prod_bootstrap.py
  6. Update DEPLOYMENT.md with bootstrap procedure
  7. Add `alembic check` to CI
  8. Add pagination to top 10 largest list endpoints (audit, esg, field_sales, finance)

Phase 2 — Security improvements
  9. Wire 2FA OTP dispatch to email endpoint
  10. Set REQUEST_TIMEOUT_SECONDS=60 in .env.production.example

Phase 3 — Performance
  11. Paginate remaining 25 unbounded CRUD list functions
  12. Add startup seeding optimization (skip if no changes)
  13. Remove dead AUTO_CREATE_TABLES block

Phase 4 — Testing
  14. Add GitHub Actions CI workflow
  15. Add Playwright smoke tests for login, dashboard, core workspace flows

Phase 5 — Production readiness
  16. Document multi-replica migration strategy
  17. Add Next.js middleware for auth routing
  18. Review Redis password for production
```

---

## 12. Test Plan

See `docs/QA_TEST_PLAN.md` for full plan. Summary:

**Smoke tests (must pass before any deployment):**
1. `start-dev.bat` → all containers healthy
2. `test-login.bat` → admin login + `/auth/me` 200
3. Demo users (ceo, coo, cfo, cto, cmo) all login
4. Dashboard loads, no console errors
5. `/api/v1/health` returns `{"status": "ok", "database": "connected"}`

**Regression checks after any backend change:**
- `python -m compileall app -q` — no syntax errors
- `alembic check` — no unapplied migrations
- `/auth/me` returns 200 with correct user data
- Role permissions correctly gated on at least one test endpoint

---

## 13. Deployment Readiness Verdict

**Dev/local:** ✅ Ready. `start-dev.bat` works on Windows. Login works. Demo users seed correctly. All containers healthy.

**Staging:** ⚠️ Conditional. Needs a staging DB that was either cloned from dev or bootstrapped with `prod_bootstrap.py`. If staging DB is fresh, deployment will fail.

**Production (first deploy):** ❌ NOT READY. Requires:
1. Production bootstrap procedure (see C1)
2. Real `SECRET_KEY` (production guard enforces this)
3. `AUTH_COOKIE_SECURE=true` (production guard enforces this)
4. `SEED_DEMO_DATA=false` (production guard enforces this)
5. `SYNC_INITIAL_ADMIN_PASSWORD=false` (production guard enforces this)
6. Decision on multi-replica migration safety

**Production (subsequent deploys):** ✅ Ready once initial schema exists. `alembic upgrade head` applies incremental migrations correctly.

---

## 14. Production Readiness Verdict

**Score: NOT READY (4/10)**

Blockers:
1. No production first-deploy procedure
2. 2FA OTP delivery not wired (feature appears active but broken for SMS/Email users)
3. No CI/CD pipeline
4. Unbounded queries will OOM under production load
5. No multi-replica migration safety

Not blockers (guards exist):
- Default SECRET_KEY rejected by production guard
- Demo data rejected by production guard
- Insecure cookie rejected by production guard

**Timeline estimate to production-ready:** 2–3 weeks of focused work on the items in the Safe Repair Order.

---

## Backend Section

### App Startup
- Lifespan function starts reliably ✅
- Seed runs on every startup (acceptable, with upsert safety) ✅
- `/live` has no DB dependency ✅
- `/ready` checks DB with 8s TTL cache ✅
- `/health` uses same cached check ✅
- Startup errors logged but server still starts (seed failures do not block uvicorn) ✅
- Dead `AUTO_CREATE_TABLES` block in lifespan ⚠️ (never triggers, confusing)

### Database/Session
- Async SQLAlchemy with asyncpg ✅
- `pool_pre_ping=True` ✅
- Pool size 5/10 dev, 20/20 prod ✅
- No rollback on exception ❌ (see H3)
- `expire_on_commit=False` ✅ (correct for async)

### Migrations
- 80 total migrations, 1 head, linear chain after merge ✅
- Fresh DB fallback via `dev_migrate.py` (dev only, stamped, logged) ✅
- Production fresh deploy broken ❌ (see C1)
- `_ensure_reconciliation_columns` handles `must_change_password` drift ✅

### CRUD/Services
- Per-user idempotent seeding ✅
- N+1 risk in deps.py (`selectinload` used correctly for User→Roles→Permissions) ✅
- 35 CRUD files with unbounded `.all()` ❌ (see H2)
- Audit logging on login success/failure ✅
- `with_for_update` not observed in CRUD files (no optimistic locking) ⚠️

### API Endpoints
- 100+ endpoint files under `backend/app/api/v1/endpoints/` ✅
- Auth endpoints: login, logout, me, 2fa, change-password ✅
- Response schemas defined ✅
- `require_permission()` dependency factory used ✅
- Input sanitizer middleware present ✅
- Rate limiting on login (IP + username, 5 attempts, 10min window, 30min lockout) ✅

### Auth/Security
- HttpOnly cookies, `SameSite=lax` ✅
- `AUTH_COOKIE_SECURE=false` in dev, guard enforces `true` in prod ✅
- `AUTH_RETURN_TOKEN_IN_BODY=false` ✅
- Token blocklist on logout ✅
- JWT with JTI (unique token ID per issue) ✅
- TOTP 2FA implemented, SMS/Email OTP TODO ❌
- bcrypt password hashing ✅
- Production guards for: SECRET_KEY, demo data, cookie secure, SYNC_ADMIN_PASS ✅
- CORS restricted to explicit origins (no wildcard) ✅

### AI Modules
- Provider auto-detection (Anthropic → OpenAI → Gemini) ✅
- Mock mode available ✅
- `AI_MASK_EXTERNAL_CONTEXT=True`, customer/supplier names masked by default ✅
- `AI_NL_COMMAND_EXECUTION_ENABLED=false` by default ✅
- Rate limits per user per hour defined ✅
- Dry-run/approval flow not verified in this review

### Error Handling/Logging
- Structured logging with request IDs ✅
- `x-request-id` header propagated ✅
- Slow request logging at 500ms threshold ✅
- Timeout handling returns 504 with request ID ✅
- SecurityHeadersMiddleware re-raises after logging (correct) ✅

### Tests
- 35+ test files present ✅
- Security, hardening, attack simulation tests ✅
- GAP coverage tests for each module ✅
- No real DB fixture (tests appear to be mocked/structural) ⚠️
- No migration-specific tests ❌
- No startup/seeding tests ❌

---

## Frontend Section

### Routing / Page Consolidation
- 697 static pages generated (build clean) ✅
- D=0 duplicate UI pages (consolidation complete) ✅
- Build produces no errors or warnings ✅
- TypeScript type check passes clean ✅

### Navigation / Sidebar
- Sidebar uses localStorage for UI state only (collapsed, cluster, section) ✅
- No token storage in localStorage ✅
- Permission-gating via `hasPermission()` in AuthContext ✅

### Auth Frontend
- Cookie-based auth (httpOnly, no localStorage token) ✅
- `withCredentials: true` on axios ✅
- 401 response → hard `window.location.href` redirect ⚠️ (see M4)
- 2FA session token in `sessionStorage` (acceptable, short-lived) ⚠️
- ProtectedRoute component handles auth guard ✅
- No Next.js middleware for server-side auth guard ⚠️ (see M10)

### API Clients
- Axios with `withCredentials` ✅
- Base URL from `NEXT_PUBLIC_API_URL` env var ✅
- Error propagated as AxiosError (not swallowed) ✅
- Login error correctly discriminates server errors (≥500) from auth errors ✅

### Frontend Quality
- TypeScript strict mode passes ✅
- Build generates 697 pages without errors ✅
- `next.config.mjs` minimal (no custom headers, no rewrites) ⚠️

---

## DevOps Section

### Docker Dev
- No `--reload` in Dockerfile.dev CMD ✅ (fixed previously)
- Backend has `start_period: 90s` healthcheck ✅
- Frontend waits for `backend: service_healthy` ✅
- DB `env_file: .env.development` set ✅
- `pg_isready` uses correct defaults `erp_user/fmcg_erp` ✅
- Resource limits set (backend: 2CPU/1GB, frontend: 1CPU/512MB) ✅
- Volume mount `./backend:/app` enables hot code reload ✅
- `start-dev.bat` auto-starts Docker Desktop, waits for readiness ✅

### Docker Production
- Uses Gunicorn + UvicornWorker ✅
- DB and Redis NOT exposed to host ✅
- `restart: unless-stopped` on all services ✅
- Resource limits set with reservations ✅
- `env_file: .env.production` on backend and frontend ✅
- `env_file` missing on `db` service ❌ (see M9)
- Migration runs in CMD before gunicorn ❌ (not multi-replica safe, see H5)

### Compose Healthchecks
- DB: `pg_isready` with correct defaults ✅
- Redis: `redis-cli ping` ✅
- Backend: urllib to `/live` (no DB dependency) ✅
- Frontend: node `fetch` to `/login` ✅
- `start_period` appropriate for all services ✅

### CI/CD
- No CI pipeline configured ❌ (see M8)
- `test-login.bat` is a basic smoke test ✅
- `docs/DEPLOYMENT.md` exists ✅

---

## Database Section

See `docs/MIGRATION_CHAIN_REVIEW.md` for full chain analysis.

### Key Database Facts
- 637 tables in public schema ✅ (large but expected for full FMCG ERP)
- 8 users seeded (admin + 7 demo users) ✅
- 35 roles seeded ✅
- 459 permissions seeded ✅
- Alembic at head (`20260516_0060`) ✅
- Single Alembic head (no divergent branches) ✅

### Schema Health
- `access_scopes` table created by migration `20260511_0030` ✅
- `must_change_password` column on users ✅
- Performance indexes migration `20260516_0060` ✅
- No observed missing FK targets in current DB ✅
