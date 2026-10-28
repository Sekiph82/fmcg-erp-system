# M03.S02.T004 — Implementation Log V01

## Scope

The canonical `TASKS.md` row was the only task-specific acceptance material; it had no linked T004 prompt or criteria file, and no T004 session existed before this implementation. The owner's decision was applied to the exact question/task match: a user with the appropriate permission can directly change master data, every change must be audited, and a separate approver is not required. No additional business approval policy was invented.

The scope covers direct create/update paths for products, materials, suppliers, warehouses, companies and branches, plus the existing bulk import paths for products, materials, suppliers and warehouses. Existing governed deactivate/merge paths remain with the M03.S02.T002 lifecycle service and its actor-attributed lifecycle records. `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, and the preceding M03 implementation log `coordination/sessions/M03.S02.T003/CODEX_LOG_V01.md` were reviewed for relevant authorization, audit, and transaction requirements.

## Changes

- Added exact create/edit permissions to the core master write endpoints and aligned the supplier list/detail routes with `suppliers.view`. Supplier view is granted to the existing broad procurement-visibility roles; scoped-only procurement roles are not granted global supplier access. The duplicate warehouse create/edit seed entries were removed.
- Added shared before/after master-data audit events, recording the authenticated actor, entity, action, and required permission in the same database transaction as each write. No-op updates do not emit false change events. Sensitive supplier contact/compliance and company tax/registration values are redacted.
- Applied the same audit path to company and branch writes. Branch edits also verify access to the owning company before mutation.
- Added per-record audit to all four existing bulk-import adapters. Import writes require the authenticated actor; imported suppliers marked `APPROVED` receive the actual steward's approval ID and timestamp before the audit snapshot.
- Removed client control of `SupplierUpdate.approved_by_id` and `approved_at`. Direct supplier qualification transitions and approved supplier imports use the same authenticated-actor lineage rule.
- Aligned master create/edit/deactivate controls in the affected pages with their permission codes, including supplier view access.
- No database migration was needed: the existing `audit_logs` schema already has actor, module, target, and before/after JSON fields.

## Starting State and Ownership

- Starting `HEAD` and fetched `origin/main`: `c843cba chore(m03): record stewardship decision gate [skip ci]` (no divergence).
- Existing owner edit `frontend/next-env.d.ts` and unrelated untracked project-control/dashboard files were left untouched and unstaged. No private task state or owner answer inbox was inspected.
- Implementation commit: `c317a03bd1f3fd933f0eb3a4e34952f71d0620f3` (`feat(m03): audit authorized master stewardship [skip ci]`).

## Verification

- `python -m pytest -q -rs tests/test_m03_master_stewardship.py tests/test_permissions.py tests/test_m03_master_duplicate_detection.py tests/test_m03_master_lifecycle.py` — **38 passed, 4 skipped, 1 deprecation warning**. The database-gated cases are intentionally tied to separately named M03 task databases; T004's database test was run separately below.
- Fresh task-owned loopback PostgreSQL 18.6 database `fmcg_m03_t004_b3a6aee37cce4f729ed08a48`: `python -m alembic upgrade head` — passed through revision `20261028_0016`.
- With `M03_DISPOSABLE_TEST_DATABASE=1` and the exact T004 database name set, `python -m pytest -q tests/test_m03_master_stewardship.py::test_postgresql_master_update_audit_persists_and_rolls_back_atomically` — **1 passed**. It observed the persisted authenticated-actor before/after audit row and verified that an injected audit-storage failure rolls back the master write.
- `npm run type-check` — passed.
- `npx eslint src/app/dashboard/products/page.tsx src/app/dashboard/materials/page.tsx src/app/dashboard/suppliers/page.tsx src/app/dashboard/warehouses/page.tsx` — passed.
- `git diff --check` and staged diff check — passed. Task-state and queue validation passed before task closure.
- The loopback test database, PostgreSQL process, and temporary server files were removed after verification. No password was used or shared.
- Independent read-only review found bypasses in company/branch writes and master imports, an unredacted supplier field, supplier approval-lineage inconsistency, and missing supplier-view role grants. These were corrected; the final review reported no remaining blocker. The reviewer made no edits and ran no tests.

## Limits

No production/owner database or owner data was accessed. No GitHub Actions, external audit verdict, deployment, or production-readiness claim was made. All commits use `[skip ci]`.
