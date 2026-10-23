# M02.S03.T003 — User-wide issued-session revocation

**Result:** Implementation and focused local verification complete. Production deployment and owner acceptance were not part of this task.

## Delivered

- Added a persisted per-user authentication-session version and included it in newly issued access tokens. Authentication rejects tokens whose version predates the user's current value, including legacy tokens without the claim after the version changes.
- Added authenticated `POST /api/v1/auth/logout-all`. It serializes against login and refresh, increments the user's session version, revokes all active refresh-token rows for that user, writes an audit event, commits, then clears both auth cookies.
- Added a security-page action with confirmation, loading and error states, and navigation to login after success. Updated help and administrator documentation.
- Added PostgreSQL-backed coverage for multiple sessions, legacy tokens, refresh-token rejection, audit/revocation state, re-login, and isolation of another user's sessions.

## Evidence

Integration tests used only the task-owned loopback PostgreSQL database `fmcg_m02_t003_7a1085e73ab24ed5af0af3238204f0b5` in container `fmcg-m02-s03-t003-7a1085e73ab24ed5af0af3238204f0b5`, labeled `codex.task=M02.S03.T003`. No production database, owner data, or GitHub Actions were used.

| Check | Result |
|---|---|
| Focused M02 refresh/session tests plus M20 auth transaction-boundary regression, with `M02_DISPOSABLE_TEST_DATABASE=1` and the exact disposable DB name | 14 passed; 2 upstream httpx deprecation warnings |
| Alembic downgrade to `20261023_0013`, then upgrade to head | Passed; final revision `20261023_0014` |
| Python compile check for changed authentication service, endpoint, model, dependency, and test modules | Passed |
| Frontend `npm run type-check` | Passed |
| `git diff --check` | Passed |

An independent read-only reviewer found no actionable correctness or security blocker in session version checks, user-before-family lock ordering, endpoint behavior, or cross-user isolation coverage. The reviewer did not independently execute tests.

## Acceptance references and limits

- Task authority: root `TASKS.md`, M02.S03.T003.
- No T003-specific acceptance document or newer M02 security audit was linked in `TASKS.md`. The available security references reviewed for the preceding M02 task are `docs/SECURITY_REVIEW.md` (2026-05-17) and `backend/tests/SECURITY_REPORT.md` (2026-05-02); both are historical and are not a fresh production security audit.
- No production runtime, deployment, owner-data, or production security acceptance is claimed.
