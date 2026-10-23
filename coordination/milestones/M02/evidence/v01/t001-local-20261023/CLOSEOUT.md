# M02.S03.T001 — Refresh-token rotation lifecycle

**Result:** Implementation and focused local verification complete. Production deployment and owner acceptance were not part of this task.

## Delivered

- Issued opaque refresh credentials in HttpOnly cookies after password login and successful 2FA verification.
- Stored only SHA-256 digests; rotated each credential once under a row lock and linked each consumed token to its successor.
- Revoked a session family on refresh-token reuse, logout, and inactive-user refresh. Session-bound access JWTs are rejected after family revocation.
- Kept the original seven-day session expiry through rotation so regular refreshes cannot extend a session indefinitely.
- Added a frontend refresh-and-retry path for authenticated API calls, including authenticated 2FA settings. Pre-auth login and 2FA challenge failures do not trigger refresh attempts.
- Added audit events without recording raw refresh credentials.

## Evidence

The integration tests used only the task-owned loopback PostgreSQL database `fmcg_m02_t001_844183eafad347e488aa46db` in container `fmcg-m02-s03-t001-844183eafad347e488aa46db` (label `codex.task=M02.S03.T001`). No production database, owner data, or GitHub Actions were used.

| Check | Result |
|---|---|
| `backend/venv/Scripts/python.exe -m pytest -q tests/test_m02_refresh_token_rotation.py` with `M02_DISPOSABLE_TEST_DATABASE=1` and the exact disposable database name | 6 passed |
| `backend/venv/Scripts/python.exe -m pytest -q tests/test_m20_auth_transaction_boundary.py` against the same isolated database | 1 passed, 2 upstream httpx deprecation warnings |
| `backend/venv/Scripts/python.exe -m py_compile` for changed backend modules and the M02 test | Passed |
| Alembic downgrade to `20261022_0011`, schema check, then upgrade to head and schema check | Passed; table absent after downgrade and restored after upgrade |
| `npm run type-check` in `frontend` | Passed |
| `npm run test:auth-refresh` in `frontend` | 2 passed; Node emitted a non-failing module-type performance warning |
| `git diff --check` | Passed |

An independent read-only reviewer checked the implementation and focused frontend regression test. The reviewer reported no remaining blocker and did not independently execute tests.

## Acceptance references and limits

- Task authority: root `TASKS.md`, M02.S03.T001.
- Existing security material reviewed: `docs/SECURITY_REVIEW.md` (2026-05-17) and `backend/tests/SECURITY_REPORT.md` (2026-05-02). These are historical reports; neither is a fresh production security audit.
- The next sprint task, M02.S03.T002, owns inactivity/session-expiry policy. This task enforces the current fixed absolute refresh-session lifetime.
- No production runtime, browser, owner-data, security audit, deployment, or publication gate is claimed as accepted here.
