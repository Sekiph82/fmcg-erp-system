# M02.S03.T002 — Inactivity/session-expiry policy

**Result:** Implementation and focused local verification complete. Production deployment and owner acceptance were not part of this task.

## Delivered

- Recorded session activity for session-bound authenticated requests and refresh-token rotation, while preserving the session's original absolute expiry.
- Revoked idle session families after the configured inactivity period and recorded `AUTH_SESSION_EXPIRED` audit events.
- Added a migration that backfills existing token families from their latest token creation time before requiring activity timestamps.
- Serialized activity, rotation/replay, and logout mutations on a family-level PostgreSQL advisory lock. Activity timestamps use database time and monotonic updates to prevent delayed requests from moving activity backward.
- Kept authentication activity commits on the separate auth database session so they do not commit staged endpoint business writes.
- Documented and exposed the existing eight-hour default in the environment examples; configuration rejects values below one minute.

## Evidence

The integration tests used only the task-owned loopback PostgreSQL database `fmcg_m02_t002_45f120a19df14748b66d9040333e77e8` in container `fmcg-m02-s03-t002-45f120a19df14748b66d9040333e77e8`, labeled `codex.task=M02.S03.T002`. No production database, owner data, or GitHub Actions were used.

| Check | Result |
|---|---|
| `backend` focused M02 refresh/session tests plus M20 auth transaction-boundary regression, with `M02_DISPOSABLE_TEST_DATABASE=1` and the exact disposable DB name | 13 passed; 2 upstream httpx deprecation warnings |
| Regression for a delayed activity update waiting behind a newer committed timestamp | Passed as part of the 13-test run |
| Regression for predecessor replay concurrent with successor rotation; family revoked and replay audit retained | Passed as part of the 13-test run |
| Python compile check for changed auth service and integration tests | Passed |
| Alembic downgrade to `20261023_0012`, then upgrade to head | Passed; final revision `20261023_0013` |
| `git diff --check` | Passed |

An independent read-only reviewer found no remaining concurrency or transaction blocker in the reviewed T002 paths. The reviewer did not independently execute tests.

## Acceptance references and limits

- Task authority: root `TASKS.md`, M02.S03.T002.
- Existing security material reviewed: `docs/SECURITY_REVIEW.md` (2026-05-17) and `backend/tests/SECURITY_REPORT.md` (2026-05-02). These historical reports are not a fresh production security audit.
- No production runtime, live database, owner-data, deployment, M20 acceptance, or publication gate is claimed as accepted here.
