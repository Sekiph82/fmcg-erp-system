# Auto-Fix Continuation Guide

Date: 2026-05-17 (Round 3)
Purpose: Let the next Claude session continue without asking the user anything.

---

## What Was Done This Run (Round 3)

### Backend tests — DONE
- `backend/tests/test_permissions.py` (NEW): 12 tests — `has_permission`, `has_any_permission`, `forbidden_detail`, `require_permission`. All pass without DB.
- `backend/tests/test_migrations.py` (NEW): 4 tests — single head, all have downgrade, no duplicate IDs, all importable. All pass without DB.
- `backend/requirements.txt`: Added `pytest>=8.0.0` and `pytest-asyncio>=0.23.0` so CI can run tests.

### DEPLOYMENT.md — DONE
- Replaced broken first-deploy step (`alembic upgrade head` on fresh DB) with correct `prod_bootstrap.py` workflow.
- Added note to Migration Procedure section clarifying `prod_bootstrap.py` exception.

---

## Verification
```bash
docker compose --env-file .env.development exec backend \
  python -m pytest tests/test_permissions.py tests/test_migrations.py -v
# 16 passed
```

---

## What To Do Next (in order, no decisions needed)

### 1. Run the full existing test suite and fix any failures

```bash
docker compose --env-file .env.development exec backend \
  python -m pytest tests/ -v --tb=short -x 2>&1 | head -120
```

Many existing tests in `tests/` use `pip install` inline or have import issues. 
Check which ones fail and fix import paths or missing deps, but DO NOT delete tests.

### 2. Add `pytest-asyncio` config to `pyproject.toml` or `pytest.ini`

The tests use `asyncio.run()` rather than `@pytest.mark.asyncio`, so no asyncio mode config is needed. But check:
```bash
# inside container
python -m pytest tests/ --collect-only 2>&1 | grep "ERROR"
```
Fix any collection errors.

### 3. Add `workflow-controls.spec.ts` E2E test coverage for the new auth guard

The middleware now redirects `/dashboard/*` to `/login?next=<path>` when no cookie.  
Check `frontend/e2e/auth-public.spec.ts` — it already has a test for this.  
If the test is failing due to the `?next=` query param change, update the assertion:
```typescript
await expect(page).toHaveURL(/\/login/);  // already matches with ?next= param
```

### 4. Decisions needed (do NOT apply without user input)

| Item | Decision needed |
|------|----------------|
| Wire 2FA OTP (SMS/Email) | Which notification service? SMTP? Twilio? |
| python-jose → PyJWT | Needs test coverage before migration |
| Redis AUTH password | Password management strategy |
| Multi-replica migration | Architecture decision for init container |

---

## Files Changed This Run

| File | Change |
|------|--------|
| `backend/tests/test_permissions.py` | NEW — 12 permission unit tests |
| `backend/tests/test_migrations.py` | NEW — 4 migration integrity tests |
| `backend/requirements.txt` | Added pytest, pytest-asyncio |
| `docs/DEPLOYMENT.md` | Fixed first-deploy section (prod_bootstrap.py) |
| `docs/AUTO_FIX_CONTINUATION.md` | Updated for round 4 |

---

## Project State Summary

| Area | Status |
|------|--------|
| Dev startup | Working |
| Login / auth/me | Working |
| CORS security | Fixed |
| Auth redirect (401) | Fixed (Next.js router) |
| Dashboard auth guard | Fixed (middleware cookie check) |
| CRUD pagination | Complete |
| CI/CD | Working (compile + migrate + test + type-check + build) |
| Production bootstrap | Ready (`scripts/prod_bootstrap.py`) |
| Production runbook | Updated in `docs/DEPLOYMENT.md` |
| Permission tests | 12 passing |
| Migration tests | 4 passing |
| 2FA — TOTP | Working |
| 2FA — SMS/Email | Disabled in UI (OTP not dispatched — TODO) |
| SAWarnings | Fixed |
| Playwright e2e | Comprehensive (auth-public, authenticated-shell, critical-workflows) |
| Production deploy | NOT YET (needs 2FA OTP decision + ops runthrough) |

---

## How to Resume

Say: **"Next"** — Claude will read this file and continue from item 1.
