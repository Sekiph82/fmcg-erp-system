# M20.S04.T002 Closeout

Task: **Enforce permissions/audit trail on approval/release**

## Changes and evidence

- Approval and release routes require their MPS module permissions and the authenticated principal. They enforce the source MRP warehouse scope; release also enforces the target warehouse scope and same-company constraint.
- Approval persists the principal as `approved_by_id` and writes an audit event with actor identity, before/after status, and approval time. Release writes the matching actor, before/after status, release time, production-order IDs, and target warehouse.
- The approval route refreshes the persisted plan before response serialization so server-managed timestamps are available after the transaction.
- PostgreSQL acceptance coverage exercises denied approval for a principal without permission, denied approval outside the warehouse scope, successful approval, actor attribution, audit timestamp and before/after values, and release audit contents. Existing release cases also cover wrong company/warehouse scope, missing permission, idempotency, and transaction rollback.
- Independent read-only review found no remaining concrete issue in the task-scoped diff.

## Verification

- Disposable PostgreSQL 16 database, loopback-only, isolated for this task. Alembic `upgrade head` succeeded; the container was stopped and removed after the run. The generated database password was not recorded.
- With `M20_DISPOSABLE_TEST_DATABASE=1` and the exact generated database name, ran:
  `python -m pytest -q tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_v03_acceptance.py`
- Result: **53 passed, 69 warnings** in 26.32 seconds. Warnings were existing Pydantic/deprecation warnings.
- Remote CI/GitHub Actions were not run under the M20 quota restriction through 2026-10-30.

## Policy limit

The invariant matrix records that an MPS maker-checker/segregation policy is not configured. No self-approval restriction was invented. If the business requires approver/releaser separation, that policy needs an explicit owner decision and configuration before production use.
