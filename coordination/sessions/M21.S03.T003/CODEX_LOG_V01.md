# M21.S03.T003 — Alternate/substitute component governance

## Decision and policy behavior

The owner directed that planner/quality approval use a real recorded workflow and that `EMERGENCY_ONLY` receive a defined rule. Requests now persist their BOM, directly owned BOM line, substitute, target quantity, derived substitute quantity, production/order trace reference, reason, shortage-evidence reference, requester identity, status, and per-role approval decisions.

- `NO_SUB` rejects substitution requests.
- `PLANNER_APPROVAL` requires a user with `bom.approve`.
- `QA_APPROVAL` requires a user with `quality.approve`.
- `BOTH_REQUIRED` requires both permissions, exercised by different users.
- `SHORTAGE_ONLY` requires a shortage-evidence reference and planner approval.
- `EMERGENCY_ONLY` requires a written reason, shortage-evidence reference, and separate planner and quality approvals. Reviewers must confirm the primary material cannot satisfy the scheduled quantity/date and routine procurement cannot meet the schedule.

Every approval is recorded with role, actor, decision, reason, and audit event. The requester cannot approve their own request. Approval is rejected if the BOM line/group policy or the calculated quantity basis changed. Explosion checks the required approval records and distinct approvers again, binds the request to the BOM that directly owns the line, and derives the substitute quantity again from current line basis, BOM quantity, loss factors, and substitute ratio. Requests cannot be applied to a different target quantity or production/order trace reference, and active master identity, item type, and exact UOM are rechecked. Implicit UOM conversion is not allowed.

## Verification

- `python -m py_compile` passed for the changed service, API, model, schema, and test modules.
- `python -m pytest -q backend/tests/test_m21_s03_t003_substitution_rbac.py backend/tests/test_bom_explosion_nested.py` — 13 passed.
- Frontend `npm.cmd run type-check` — passed.
- The task-owned disposable PostgreSQL runner migrated a fresh synthetic database to Alembic head and passed the integration test, including the approval lifecycle, server-derived quantity, stale-policy and stale-quantity rejection, malformed nested-line binding, and audit persistence.
- `git diff --check` passed for the task-owned changes.
- Independent read-only review found and prompted fixes for recursive direct-BOM ownership, approval-time/explosion-time quantity freshness, and decision-time policy freshness. The final targeted re-review confirmed the policy-freshness fix; the updated database regression passed.
- The PostgreSQL container was bound to loopback, had no volume mounts, used synthetic data only, and was removed after the run. A follow-up label query confirmed no `codex.task=M21.S03.T003` container remains.

## Limits

Shortage and production/order values are trace references supplied by users, not foreign keys to verified inventory or released orders. The ERP does not independently establish the shortage or schedule facts; planner and quality reviewers must verify the supporting records. No production data, external database, or GitHub Actions run was used.
