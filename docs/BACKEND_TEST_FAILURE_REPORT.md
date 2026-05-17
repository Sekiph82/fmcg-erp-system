# Backend Test Failure Report

**FINAL STATUS: 462 passed, 0 failed — local Windows venv AND Docker/Linux (2026-05-17)**

Date: 2026-05-17  
Total passed (original): 407  
Total failed (original): 55  
Total passed (final): 462  
Total failed (final): 0  

---

## Summary by Root Cause

| # | Root Cause | Affected Tests | CI-Failing? | Auto-Fix Safe? |
|---|-----------|---------------|-------------|----------------|
| 1 | `is_locked` / `get_failure_count` only check in-memory, not Redis | 7 | YES | YES |
| 2 | Async `add`/`is_blocked` called without `await` in sync test methods | 4 | YES | YES |
| 3 | `sanitize_filename` ignores Windows backslash paths on Linux | 2 | YES | YES |
| 4 | Outdated Alembic head assertion (`20260515_0060` vs current `20260516_0060`) | 1 | YES | YES |
| 5 | Wrong relative path in file-existence check (runs from `backend/`, not repo root) | 1 | YES | YES |
| 6 | `email-validator` missing from `requirements.txt` | 1 | YES | YES |
| 7 | passlib 1.7.x + bcrypt 4.x incompatibility (72-byte wrap detection) | 1 | YES | YES |
| 8 | Docker volume: frontend/docs not mounted in backend container | 37 | NO (CI passes) | NO — Docker-only |
| 9 | `SEED_DEMO_DATA` env var leaked from `docker compose` env into pytest | 1 | NO (CI passes) | NO — Docker-only |
| 10 | Stale Redis login state between Docker test runs | 1 | NO (CI uses fresh Redis) | NO — Docker-only |

---

## Group 1 — Redis `is_locked` / `get_failure_count` Bug (7 tests, CI-FAILING)

**Root cause:** `login_limiter.py::is_locked(identifier)` only checks the in-memory `_lockouts` dict.  
`record_login_failure` writes the lock to Redis (`r.setex(f"ll:lock:{identifier}", ...)`) but never updates `_lockouts`.  
Result: `is_locked` always returns `False` when Redis is available. `get_failure_count` has the same split.

**Affected tests:**

| Test | File | Error |
|------|------|-------|
| `test_brute_force_triggers_lockout` | `test_attack_simulation.py` | `assert is_locked("attacker_brute")` → False |
| `test_concurrent_different_users_isolated` | `test_attack_simulation.py` | `get_failure_count("user_A")` returns 0, expected 1 |
| `test_lockout_after_max_attempts` | `test_security.py` | `assert is_locked("baduser")` → False |
| `test_failure_count_increments` | `test_security.py` | count returns 0, expected 1 (Redis has count, in-memory doesn't) |
| `test_reset_clears_failures` | `test_security.py` | `get_failure_count` returns 0 before reset |
| `test_lockout_releases_after_window` | `test_security.py` | `is_locked` returns False throughout |
| `test_limit_enforcement_stops_at_threshold` | `test_load_simulation.py` | `is_locked` returns False after 5+ failures |

**Fix:** Make `record_login_failure` dual-write: set `_lockouts[identifier]` when Redis lock is set.  
Also make `get_failure_count` read Redis when `_failures[identifier]` is absent.  
Tests also need `setup_method` to clear Redis keys for test identifiers (not just in-memory dicts).

---

## Group 2 — Async Methods Called Without `await` (4 tests, CI-FAILING)

**Root cause:** `token_blocklist.add()` and `token_blocklist.is_blocked()` are `async def`.  
Calling without `await` returns a coroutine object (always truthy). `assert not coroutine` → AssertionError.  
`asyncio_mode = auto` handles `async def test_*` but not sync tests that call async functions.

**Affected tests:**

| Test | File | Error |
|------|------|-------|
| `test_different_token_not_blocked` | `test_attack_simulation.py` | `assert not is_blocked(other_token)` — coroutine is truthy |
| `test_expired_revoked_token_auto_released` | `test_attack_simulation.py` | same — `assert not is_blocked(expired)` |
| `test_10000_token_adds_complete` | `test_load_simulation.py` | `add(token, expiry)` returns coroutine, never adds |
| `test_expired_tokens_cleaned_up` | `test_load_simulation.py` | same |

**Fix:** Convert these test methods to `async def` and add `await`.

---

## Group 3 — Windows Backslash Path Traversal Not Sanitized (2 tests, CI-FAILING)

**Root cause:** `file_validator.py::sanitize_filename` calls `os.path.basename(filename)`.  
On Linux, `os.path.basename("..\\..\\windows\\etc")` returns the full string unchanged (Linux uses `/` only).  
The regex `_UNSAFE_FILENAME_RE.sub("_", ...)` replaces `\\` with `_` but leaves `..` intact in the result.  
`filename.lstrip(".")` removes leading dots from the final basename-like fragment but the traversal path remains.

**Affected tests:**

| Test | File | Probe | Expected | Got |
|------|------|-------|----------|-----|
| `test_path_traversal_sanitization` (Windows probe) | `test_attack_simulation.py` | `"..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"` | no `..` in result | `..` survives |
| `test_path_traversal_sanitization` (null byte probe) | `test_attack_simulation.py` | `"file\x00name.txt"` | no null byte | null byte survives (secondary) |

**Fix:** Normalize `\\` → `/` before `os.path.basename`. Also strip null bytes.

---

## Group 4 — Outdated Alembic Head Assertion (1 test, CI-FAILING)

**Root cause:** Test asserts `'20260515_0060' in result.stdout` but Alembic head was updated to `20260516_0060` in Round 4.

**Affected test:**

| Test | File | Expected | Actual |
|------|------|----------|--------|
| `test_alembic_head_matches_expected` | `test_gap018_gs1_label_printing.py` | `20260515_0060` | `20260516_0060` |

**Fix:** Update expected string to `20260516_0060`.

---

## Group 5 — Wrong Relative Path (1 test, CI-FAILING)

**Root cause:** Test builds `Path("backend/alembic/versions/20260511_0020_...")`.  
pytest runs from `backend/` directory → path resolves to `backend/backend/alembic/...` → FileNotFoundError.

**Affected test:**

| Test | File | Bad path |
|------|------|----------|
| `test_posting_migration_file_exists` | `test_gap002_posting_integration.py` | `"backend/alembic/versions/..."` |

**Fix:** Change to `"alembic/versions/..."` (relative to `backend/`) or use `Path(__file__).parents[...] / "alembic/versions/..."`.

---

## Group 6 — Missing `email-validator` Package (1 test, CI-FAILING)

**Root cause:** Pydantic `EmailStr` requires `email-validator` package. Not in `requirements.txt`.  
`fastapi` was added without `[all]` extras. Test `test_multi_company_tenant_isolation` imports a schema with `EmailStr` field → `ImportError`.

**Affected test:**

| Test | File | Error |
|------|------|-------|
| `test_multi_company_tenant_isolation` | `test_gap025_multi_company.py` | `ImportError: email-validator is not installed` |

**Fix:** Add `email-validator>=2.0.0` to `requirements.txt`.

---

## Group 7 — passlib + bcrypt 4.x Incompatibility (1 test, CI-FAILING)

**Root cause:** passlib 1.7.x runs a wrap-bug detection using a 72+ byte string during `CryptContext` initialization or first use.  
bcrypt 4.x enforces the 72-byte limit strictly and raises `ValueError: password cannot be longer than 72 bytes`.  
passlib 1.7.x does not handle this exception → crash in `hash_password("TestPassword1")`.

**Affected test:**

| Test | File | Error |
|------|------|-------|
| `test_password_hashing_reasonable_time` | `test_load_simulation.py` | `ValueError: password cannot be longer than 72 bytes` |

**Fix:** Pin `bcrypt<4.0.0` in `requirements.txt` OR upgrade to `passlib[bcrypt]>=1.7.4` with `bcrypt>=4.0.1` which ships a compatibility shim, OR switch to `bcrypt` directly. Safest: pin `bcrypt>=4.0.0,<5.0` and add `passlib>=1.7.4` — passlib 1.7.4 added the shim. **Actual fix: `bcrypt>=4.0.1` is fine; passlib 1.7.4 fixes the detection.** Current `requirements.txt` likely has `passlib==1.7.4` already — check; if bcrypt is unpinned and resolves to 4.x, add `passlib[bcrypt]>=1.7.4`.

---

## Group 8 — Docker Volume Mount: Frontend/Docs Not Available (37 tests, CI-PASSES)

**Root cause:** Backend Docker container does not mount `frontend/` or `docs/` directories.  
Tests that check frontend TypeScript files, documentation files, or screenshot paths use  
`Path(__file__).resolve().parents[2]` to reach repo root, then access `frontend/src/...` or `docs/...`.  
In Docker: test file is at `/app/tests/test_xxx.py`, so `parents[2]` = `/`; paths like `/frontend/src/lib/wms.ts` don't exist.  
These tests PASS in CI because CI checks out the full repo and runs pytest from the repo root.

**Affected tests (37):**

- `test_gap008_wms_service.py` — `frontend/src/lib/wms.ts`
- `test_gap009_production_dashboard.py` — `frontend/src/app/production/...`
- `test_gap010_inventory_management.py` — `frontend/src/app/inventory/...`
- `test_gap011_procurement_service.py` — `frontend/src/app/procurement/...`
- `test_gap020_maintenance_module.py` — `frontend/src/app/maintenance/...`
- `test_gap021_sustainability.py` — `frontend/src/app/sustainability/...`
- `test_gap022_financial_reporting.py` — `frontend/src/app/financial/...`
- `test_gap023_maintenance_page_guard.py` — maintenance page guard TypeScript checks
- `test_gap024_ai_pages.py` — `frontend/src/app/ai/...`
- `test_gap025_multi_company.py` (partial) — docs file existence
- `test_manual_audit_docs.py` — `docs/MANUAL_AUDIT_*.md`
- `test_screenshot_automation_docs.py` — screenshot doc files
- `test_full_manual_generation_readiness.py` — doc + frontend file checks

**Action:** These are environment-specific failures. No code fix needed — tests are correct.  
Consider: add a `pytest.mark.requires_repo_root` marker and skip when running inside Docker.  
For now: document as known Docker-only failures. CI status unaffected.

---

## Group 9 — `SEED_DEMO_DATA` Env Var Leaked from Docker Compose (1 test, CI-PASSES)

**Root cause:** `docker compose up` with `.env.development` sets `SEED_DEMO_DATA=true`.  
This env var leaks into pytest subprocess. `test_hardening.py` asserts `SEED_DEMO_DATA` is not `"true"` in a test context.  
In CI: `SEED_DEMO_DATA: "false"` is set in `ci.yml` workflow. Passes.

**Affected test:**

| Test | File |
|------|------|
| `test_seed_demo_data_disabled_in_prod_config` | `test_hardening.py` |

**Action:** Docker-only. No code change needed. Use `pytest -p no:env` or set `SEED_DEMO_DATA=false` in local test invocation.

---

## Group 10 — Stale Redis Login State Between Docker Test Runs (1 test, CI-PASSES)

**Root cause:** `test_failure_count_increments` expects count=1 after 1 failure, but Redis still has count from a previous test run.  
CI always starts a fresh Redis container. Docker dev reuses the same Redis instance across runs.

**Action:** Docker-only. No code change needed for CI. Fix is in Group 1 (proper test cleanup).

---

## Fix Plan (CI-Failing Only)

| # | File | Change |
|---|------|--------|
| 1 | `backend/app/core/login_limiter.py` | Dual-write `_lockouts` when Redis lock set; read Redis in `get_failure_count` |
| 1 | `backend/tests/test_attack_simulation.py` | `setup_method` flush Redis keys for test identifiers |
| 1 | `backend/tests/test_security.py` | `setup_method` flush Redis keys |
| 2 | `backend/tests/test_attack_simulation.py` | Make 2 sync test methods `async def`, add `await` |
| 2 | `backend/tests/test_load_simulation.py` | Make 2 sync token test methods `async def`, add `await` |
| 3 | `backend/app/core/file_validator.py` | Normalize `\\` → `/` before `os.path.basename`; strip null bytes |
| 4 | `backend/tests/test_gap018_gs1_label_printing.py` | `20260515_0060` → `20260516_0060` |
| 5 | `backend/tests/test_gap002_posting_integration.py` | `"backend/alembic/versions/..."` → `"alembic/versions/..."` |
| 6 | `backend/requirements.txt` | Add `email-validator>=2.0.0` |
| 7 | `backend/requirements.txt` | Verify passlib/bcrypt versions; add `bcrypt>=4.0.1` if missing |
