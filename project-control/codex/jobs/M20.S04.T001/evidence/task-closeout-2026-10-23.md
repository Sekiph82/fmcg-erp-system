# M20.S04.T001 Closeout

Task: **Harden draft→approve→release semantics**

## Changes

- Post-approval edits reopen an unreleased MPS plan as DRAFT, clear approval attribution, and record the authenticated editor. Released plans and plans with production-order links remain immutable.
- An ON_HOLD line now requires an explicit authenticated `clear_hold` action. Clearing resets feasibility to PENDING, unlocks the line for scheduling, and records before/after values and actor in the audit log.
- Release rejects positive-quantity prelinked orders before creating any orders, fails closed when any positive line is blocked or lacks an effective approved recipe, and validates complete, unique, existing order links on retry.
- Successful release responses include the persisted production-order IDs; repeated missing-recipe remarks are avoided.
- Added PostgreSQL acceptance coverage for approval prerequisites, post-approval feasibility drift, repair/reapproval, explicit hold clearing, prelinked-order rejection, idempotent retry, release immutability, and cleanup of synthetic audit data.

## Verification

- Disposable PostgreSQL 16 database created for this task on a loopback-only port; Alembic `upgrade head` succeeded. The database was stopped and removed after the run; its password was ephemeral and not recorded.
- Ran with `M20_DISPOSABLE_TEST_DATABASE=1` and the exact generated database name:
  `python -m pytest -q tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_v03_acceptance.py`
- Result: **53 passed, 69 warnings** in 27.25 seconds. Warnings are existing Pydantic/deprecation warnings; no test failed or skipped.
- `git diff --check` passed.
- Independent read-only review found no remaining concrete issue in the task-scoped implementation and test diff.
- GitHub Actions and remote CI were not run under the M20 CI quota restriction through 2026-10-30.

## Remaining limits

- This closeout records local implementation and test evidence only. It does not claim ChatGPT audit acceptance or milestone completion.
