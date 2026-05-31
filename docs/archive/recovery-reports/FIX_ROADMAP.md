# Fix Roadmap

Date: 2026-05-17  
Source: Full Repository Review (`docs/FULL_REPOSITORY_REVIEW.md`)

---

## Phase 0 — Stop Dangerous Drift

These are documentation/tracking items, not code changes.

| Item | Priority | Risk | File(s) | Difficulty | Auto-fixable |
|------|---------|------|---------|------------|--------------|
| Document `.env` local Gemini key rotation if repo goes public | MEDIUM | LOW | `.env` | Trivial | No — user decision |
| Confirm Gordon changes were all correctly assessed (see RUNTIME_STARTUP_REPORT.md) | LOW | LOW | Multiple | None | No |
| Freeze migration chain until production bootstrap is in place | HIGH | HIGH | `alembic/versions/` | None | No — user decision |

---

## Phase 1 — Runtime Startup (All safe to apply now)

| Item | Priority | Risk | File(s) | Fix | Difficulty | Auto-fixable |
|------|---------|------|---------|-----|------------|--------------|
| Fix outdated `--reload` comment in start-dev.bat | HIGH | None | `start-dev.bat:226` | Change comment text | Trivial | ✅ Yes |
| Add rollback to `get_db` exception path | HIGH | Low | `backend/app/db/session.py` | Add `await session.rollback(); raise` in except | Trivial | ✅ Yes |
| Add `env_file: .env.production` to `db` service in prod compose | MEDIUM | None | `docker-compose.prod.yml` | Add 1 line | Trivial | ✅ Yes |
| Remove dead `AUTO_CREATE_TABLES` block from `main.py` lifespan | LOW | None | `backend/app/main.py:40-48` | Delete 8 lines | Trivial | ✅ Yes |
| Fix SAWarning on DimValue.children and CostCenter.children | LOW | None | Affected model files | Add `overlaps="parent"` | Easy | ✅ Yes |

---

## Phase 2 — Database / Migrations (Manual decision required before implementation)

| Item | Priority | Risk | File(s) | Fix | Difficulty | Decision needed |
|------|---------|------|---------|-----|------------|-----------------|
| **Write production bootstrap script** | CRITICAL | HIGH | `backend/scripts/prod_bootstrap.py` (new) | Guarded create_all + stamp for fresh production DB | Medium | **Yes — agree on approach first** |
| **Document production first-deploy procedure** | CRITICAL | HIGH | `docs/DEPLOYMENT.md` | Add section: fresh DB bootstrap steps | Easy | No — Claude can write |
| Add `alembic check` to CI | HIGH | None | `.github/workflows/` (new) | Fail CI if unapplied migrations | Medium | No |
| Multi-replica migration safety (init container) | HIGH | HIGH | `docker-compose.prod.yml`, `Dockerfile.prod` | Move migration to init container / pre-deploy script | Hard | **Yes — architecture decision** |

**Manual decision required for C1 (production bootstrap):**

Option A (Recommended): `scripts/prod_bootstrap.py` with `BOOTSTRAP_PRODUCTION=true` guard:
```python
# Checks DB is empty, runs create_all(), stamps head
# Refuses if any tables exist
# Requires explicit env var BOOTSTRAP_PRODUCTION=true
# Logs WARNING prominently
```
Run once on first production deploy:
```bash
BOOTSTRAP_PRODUCTION=true python scripts/prod_bootstrap.py
alembic upgrade head  # verify, should be no-op
```

Option B: Export dev schema as SQL dump and apply manually to production before first deploy.

Option C: Add Alembic migration that creates all base tables (complex, risky to existing DBs).

---

## Phase 3 — Security Improvements

| Item | Priority | Risk | File(s) | Fix | Difficulty | Decision |
|------|---------|------|---------|-----|------------|----------|
| Wire 2FA OTP dispatch (SMS/Email) | HIGH | Medium | `backend/app/api/v1/endpoints/auth.py:109` | Integrate email notification service | Hard | **Yes — which notification service?** |
| Disable SMS/Email 2FA in UI until wired | HIGH | None | Frontend 2FA method selector | Hide or grey out SMS/Email options | Easy | No — Claude can do |
| Set `REQUEST_TIMEOUT_SECONDS=60` in `.env.production.example` | MEDIUM | None | `.env.production.example` | Change default | Trivial | ✅ Yes |
| Restrict `allow_methods` in CORS to explicit list | MEDIUM | Low | `backend/app/main.py` | `allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` | Trivial | ✅ Yes |
| Evaluate `python-jose` → `PyJWT` migration | MEDIUM | Medium | `backend/app/core/security.py`, `requirements.txt` | Replace library | Medium | **Yes — test coverage needed** |
| Add scope filtering in CRUD queries | LOW | Medium | 35+ CRUD files | Add warehouse/company filter to queries | Hard | **Yes — data model decision** |

---

## Phase 4 — Performance

| Item | Priority | Risk | File(s) | Fix | Difficulty | Decision |
|------|---------|------|---------|-----|------------|----------|
| Paginate top 10 audit/esg/finance list queries | HIGH | Low | `crud/audit.py`, `crud/esg.py`, `crud/finance.py`, `crud/field_sales.py`, `crud/delivery.py` | Add limit/offset params | Easy | No |
| Paginate remaining 25+ CRUD list functions | HIGH | Low | 25+ CRUD files | Add limit/offset params | Medium | No |
| Add startup seeding optimization | MEDIUM | Low | `backend/app/db/seed.py` | Compare counts, skip if unchanged | Medium | No |
| Verify export streaming in finance/analytics | MEDIUM | Medium | `crud/finance.py`, `api/v1/endpoints/analytics.py` | Add StreamingResponse | Hard | No — audit first |
| Convert permission_codes to Set in AuthContext | MEDIUM | Low | `frontend/src/context/AuthContext.tsx` | `useMemo` + `Set<string>` | Easy | No |
| Increase prod backend memory limit to 2G | MEDIUM | None | `docker-compose.prod.yml` | Change memory limit | Trivial | ✅ Yes |

---

## Phase 5 — Testing

| Item | Priority | Risk | File(s) | Fix | Difficulty | Decision |
|------|---------|------|---------|-----|------------|----------|
| Add GitHub Actions CI workflow | HIGH | None | `.github/workflows/ci.yml` (new) | pytest + tsc + build | Medium | No |
| Add Playwright smoke tests | HIGH | None | `frontend/tests/e2e/` (new) | login, dashboard, logout | Medium | No |
| Add real-DB integration test fixture | HIGH | Medium | `backend/tests/conftest.py` | Docker-based test DB | Hard | No |
| Add migration chain test | HIGH | None | `backend/tests/test_migrations.py` | Fresh DB → alembic current | Medium | No |
| Add permission enforcement test | MEDIUM | None | `backend/tests/` | 403 on missing perm | Easy | No |

---

## Phase 6 — Production Readiness

| Item | Priority | Risk | File(s) | Fix | Difficulty | Decision |
|------|---------|------|---------|-----|------------|----------|
| Write complete production first-deploy runbook | CRITICAL | None | `docs/DEPLOYMENT.md` | Step-by-step guide | Easy | No |
| Add Next.js middleware for auth routing | MEDIUM | Low | `frontend/src/middleware.ts` (new) | Redirect /dashboard/* to /login if no cookie | Medium | No |
| Fix 401 hard redirect in API client | MEDIUM | Low | `frontend/src/lib/api.ts` | Use Next.js router | Easy | No |
| Add Redis AUTH password for production | LOW | Low | `docker-compose.prod.yml` | Add `--requirepass ${REDIS_PASSWORD}` | Easy | **Yes — password management decision** |
| Document multi-replica migration lock | HIGH | None | `docs/DEPLOYMENT.md` | Document Alembic advisory lock behavior | Easy | No |

---

## Estimated Implementation Timeline

| Phase | Scope | Estimated Time |
|-------|-------|---------------|
| Phase 0 | Tracking | 1 day |
| Phase 1 | Safe fixes | 1 day — Claude can apply |
| Phase 2 | DB/migrations | 3–5 days (decision required) |
| Phase 3 | Security | 3–5 days (2FA wiring hard) |
| Phase 4 | Performance | 3–4 days |
| Phase 5 | Testing | 5–7 days |
| Phase 6 | Prod readiness | 2–3 days |
| **Total** | | **2–3 weeks** |

---

## Items Claude Can Fix Without User Decision (Phase 1 + safe Phase 4/6)

Run after user confirms:
1. Fix `start-dev.bat` line 226 comment
2. Add rollback to `get_db`
3. Add `env_file` to prod compose db service
4. Remove dead `AUTO_CREATE_TABLES` block
5. Fix SAWarning overlaps on self-referential models
6. Set `REQUEST_TIMEOUT_SECONDS=60` in `.env.production.example`
7. Restrict CORS methods to explicit list
8. Convert `permission_codes` to Set in AuthContext
9. Paginate top 10 high-risk CRUD list functions
10. Fix 401 hard redirect in API client
11. Write `docs/DEPLOYMENT.md` production bootstrap section
12. Add GitHub Actions CI workflow skeleton
