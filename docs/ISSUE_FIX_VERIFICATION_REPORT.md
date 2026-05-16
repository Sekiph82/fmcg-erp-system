# Issue Fix Verification Report

Generated: 2026-05-16

---

## A. Database / Performance

| # | Issue | Status | File | Fix Implemented |
|---|-------|--------|------|-----------------|
| 1 | Missing async pool configuration | **FIXED** | `backend/app/db/session.py` | Added pool_size, max_overflow, pool_recycle, pool_timeout, pool_pre_ping from settings |
| 2 | Missing pool pre-ping and recycle | **FIXED** | `backend/app/db/session.py` | pool_pre_ping and pool_recycle added |
| 3 | Missing connection/statement timeout | **PARTIALLY FIXED** | `backend/app/core/config.py` | pool_timeout added; statement-level timeout (asyncpg `server_settings` param) left for manual PostgreSQL config: `statement_timeout=30s` via `postgresql.conf` or `ALTER ROLE` |
| 4 | Unbounded list queries in CRUD/service | **PARTIALLY FIXED** | Multiple CRUD files | Finance CRUD fixed; 52 remaining CRUD unbounded queries documented in `docs/AUTOMATED_HEALTH_AUDIT.md` |
| 5 | `list_coa` no limit | **FIXED** | `backend/app/crud/finance.py:22` | Added limit/offset params (default 500, max 1000) |
| 6 | `list_production_cost_entries` no limit | **FIXED** | `backend/app/crud/finance.py:234` | Added limit/offset params |
| 7 | `list_product_costs` no limit | **FIXED** | `backend/app/crud/finance.py:261` | Added limit/offset params |
| 8 | `list_budgets` no limit | **FIXED** | `backend/app/crud/finance.py:299` | Added limit/offset params |
| 9 | Other list_* without limits | **OPEN** | Various CRUD files | 52 HIGH findings in audit report; priority: procurement.py, sales.py, quality.py, role.py |
| 10 | with_for_update in cash balance update | **FIXED** | `backend/app/crud/finance.py:148,178` | Replaced with atomic `UPDATE ... SET current_balance = current_balance + delta` |
| 11 | Row-lock balance update risks | **FIXED** | `backend/app/crud/finance.py` | Atomic SQL UPDATE eliminates row-lock + Python race |
| 12 | Non-bulk insert loops | **FIXED** | `backend/app/crud/finance.py:71,317` | `db.add_all()` for JournalLine and BudgetLine |
| 13 | Missing indexes | **FIXED** | `backend/alembic/versions/20260516_0060_performance_indexes.py` | 35 indexes via idempotent Alembic migration |
| 14 | Lack of streaming for large exports | **OPEN** | — | Not implemented; large export endpoints should use `StreamingResponse` + cursor iteration |
| 15 | Lack of caching for stable reference data | **OPEN** | — | Not implemented; recommend Redis or TTL cache for COA, products, currencies |

## B. Backend Startup / Routing

| # | Issue | Status | File | Fix Implemented |
|---|-------|--------|------|-----------------|
| 16 | `import app.models` loads all models at startup | **CONFIRMED OK** | `backend/app/main.py:28` | Required for Alembic metadata; already lazy at import time; acceptable |
| 17 | Dynamic route registration fragility | **CONFIRMED OK** | — | Static router.include_router pattern; not fragile |
| 18 | Too many modules imported at startup | **CONFIRMED OK** | — | No lazy-load framework; acceptable at this scale |
| 19 | Module registry stub control | **CONFIRMED OK** | — | All modules are real, not stubs |
| 20 | Health check opens DB every call | **FIXED** | `backend/app/main.py` | `_db_health_cache` with 8s TTL; `/live` has zero DB cost |
| 21 | `import time` inside middleware | **FIXED** | `backend/app/main.py` | Moved to module-level import |
| 22 | Blocking observability on request path | **CONFIRMED OK** | `backend/app/core/observability.py` | `record_request` uses in-memory `Counter` with `threading.Lock`; non-blocking |
| 23 | Missing request timeout middleware | **OPEN** | — | No timeout middleware; recommend `asyncio.wait_for` wrapper or `uvicorn --timeout-keep-alive` |
| 24 | Missing rate limiting for expensive endpoints | **PARTIALLY FIXED** | — | AI rate limits exist; general API rate limiting documented but not enforced per-endpoint |

## C. Docker / DevOps

| # | Issue | Status | File | Fix Implemented |
|---|-------|--------|------|-----------------|
| 25 | Dev compose lacks resource limits | **FIXED** | `docker-compose.yml` | Added `deploy.resources.limits` for all services |
| 26 | Prod compose lacks resource limits | **FIXED** | `docker-compose.prod.yml` | Added limits+reservations for all services |
| 27 | DB/Redis ports exposed in production | **CONFIRMED OK** | `docker-compose.prod.yml` | DB and Redis have no `ports:` mapping — only backend/frontend exposed |
| 28 | Dev Dockerfiles use dev servers | **CONFIRMED OK** | `backend/Dockerfile.dev` | --reload is correct for dev; prod uses gunicorn |
| 29 | Alembic as production schema mechanism | **CONFIRMED OK** | `backend/Dockerfile.prod` | CMD runs `alembic upgrade head` before gunicorn |
| 30 | `create_all` not in production | **CONFIRMED OK** | `backend/app/main.py:38` | Guarded: `if ENVIRONMENT == "development" and AUTO_CREATE_TABLES` |
| 31 | Migration race with multiple replicas | **OPEN** | — | Single replica assumed; multi-replica needs advisory lock or separate migration job |
| 32 | CI workflow exists | **CONFIRMED OK** | `.github/workflows/ci.yml` | Full backend+frontend+docker CI exists |
| 33 | .gitignore excludes generated files | **NEEDS VERIFY** | `.gitignore` | Not reviewed in this pass; verify excludes .next, __pycache__, *.pyc, .env |
| 34 | Deployment docs | **OPEN** | — | No `docs/DEPLOYMENT.md`; recommended |

## D. Security / Auth / Seed

| # | Issue | Status | File | Fix Implemented |
|---|-------|--------|------|-----------------|
| 35 | No default seeded passwords | **CONFIRMED OK** | `backend/app/core/config.py:34-35` | INITIAL_ADMIN_PASSWORD and DEMO_USER_PASSWORD default to empty string `""` |
| 36 | SEED_DEMO_DATA false by default | **CONFIRMED OK** | `backend/app/core/config.py:29` | `SEED_DEMO_DATA: bool = False` |
| 37 | Demo users impossible in production | **CONFIRMED OK** | `backend/app/core/config.py:151` | `_production_guards` raises if SEED_DEMO_DATA=true in production |
| 38 | INITIAL_ADMIN_PASSWORD required in prod | **CONFIRMED OK** | `backend/app/core/config.py:153` | Validator enforces non-empty non-CHANGE_ME password in production |
| 39 | must_change_password for initial users | **CONFIRMED OK** | `backend/alembic/versions/20260510_0700_user_must_change_password.py` | Field exists; seed should set it for demo users |
| 40 | SECRET_KEY default rejected in production | **CONFIRMED OK** | `backend/app/core/config.py:147` | Validator rejects `changeme` in production |
| 41 | AUTH_COOKIE_SECURE true in production | **CONFIRMED OK** | `backend/app/core/config.py:156` | Validator enforces `AUTH_COOKIE_SECURE=true` in production |
| 42 | HttpOnly cookies, not localStorage | **CONFIRMED OK** | `frontend/src/context/AuthContext.tsx` | No localStorage for JWT; auth via cookie set by backend |
| 43 | Token in body disabled by default | **CONFIRMED OK** | `backend/app/core/config.py:24` | `AUTH_RETURN_TOKEN_IN_BODY: bool = False` |
| 44 | CORS from env only | **CONFIRMED OK** | `backend/app/core/config.py:57-60` | `BACKEND_CORS_ORIGINS` from settings; no wildcard |
| 45 | Production no wildcard CORS | **CONFIRMED OK** | — | No `allow_origins=["*"]` pattern in codebase |
| 46 | Password policy strict in production | **CONFIRMED OK** | `backend/app/core/config.py:149` | `PASSWORD_REQUIRE_SPECIAL` enforced in production |
| 47 | Audit login/logout/security events | **NEEDS VERIFY** | — | Not reviewed; check `backend/app/api/v1/endpoints/auth.py` for audit log calls |

## E. AI Module Safety

| # | Issue | Status | File | Fix Implemented |
|---|-------|--------|------|-----------------|
| 47 | AI mock mode visible in UI | **NEEDS VERIFY** | — | Not reviewed in this pass |
| 48 | High-risk actions disabled in mock mode | **CONFIRMED OK** | `backend/app/core/config.py:109` | `AI_NL_COMMAND_EXECUTION_ENABLED: bool = False` |
| 49 | NL command execution disabled by default | **CONFIRMED OK** | `backend/app/core/config.py:109` | Default False |
| 50-56 | NL command execution safety controls | **NEEDS VERIFY** | `backend/app/services/ai*` | Not reviewed in this pass |
| 57 | AI rate limits enforced | **CONFIRMED OK** | `backend/app/core/config.py:103-104` | `AI_RATE_LIMIT_CHAT=30`, `AI_RATE_LIMIT_GENERATE=10` per hour |

## F. Frontend

| # | Issue | Status | File | Fix Implemented |
|---|-------|--------|------|-----------------|
| 58 | No JWT in localStorage/sessionStorage | **CONFIRMED OK** | `frontend/src/context/AuthContext.tsx` | 2FA session_token in sessionStorage is ephemeral (non-JWT, short-lived); no long-lived tokens |
| 59 | Permission-aware UI | **CONFIRMED OK** | `frontend/src/context/AuthContext.tsx` | hasPermission/hasModule/canPerformInScope helpers exist |
| 60-64 | Other frontend UX issues | **NEEDS VERIFY** | — | Not reviewed in this pass |

---

## Open Issues (priority order)

1. **A.9** — 52 unbounded CRUD queries remain; see `docs/AUTOMATED_HEALTH_AUDIT.md` HIGH section
2. **A.14** — Large export streaming not implemented
3. **A.15** — Reference data caching not implemented
4. **B.23** — No request timeout middleware
5. **C.31** — Multi-replica migration race not addressed
6. **C.34** — No `docs/DEPLOYMENT.md`
7. **D.47** — Auth audit logging not verified
8. **E.47-56** — AI mock mode UI + NL execution safety not verified in this pass

---

## Tests / Checks Run

- `python -m compileall backend/app/db/session.py backend/app/core/config.py backend/app/main.py backend/app/crud/finance.py` → PASS
- `python scripts/erp-health-audit.py` → 52 HIGH, 624 MEDIUM, 0 LOW findings (see `docs/AUTOMATED_HEALTH_AUDIT.md`)
- Alembic migration `20260516_0060_performance_indexes.py` — compile OK; live run blocked (Docker not running)
