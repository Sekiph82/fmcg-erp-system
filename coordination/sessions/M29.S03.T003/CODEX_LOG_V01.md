# M29.S03.T003 — Predictive risk→maintenance action loop

## Implementation status

Implemented; pending consolidated M29.S04 acceptance. A reviewed prediction can now create a real PM work order through the existing spare-part reservation path. Prediction generation itself remains advisory and does not schedule work automatically.

## Changes

- Added an idempotent, row-locked conversion from `REVIEWED` prediction to linked PM work order. It requires an active plan for the same asset, an explicit scheduled date, and both `maintenance.review_prediction` and `maintenance.create` permissions.
- Reused the existing work-order creation path, including its spare-part availability checks and reservations. Inactive/mismatched plans and unavailable parts do not create an order.
- Added a nullable work-order link and action actor/timestamp fields to predictions, with an idempotent Alembic migration. No legacy prediction or work-order rows were backfilled or fabricated.
- Replaced the UI status-only “Work Order Planned” action with an explicit plan/date form. After review, the UI shows the reviewed predictions eligible for planning. The authenticated user ID is recorded; the client cannot choose the reviewer identity.
- Prevented review-only updates from setting `WORK_ORDER_CREATED`. Existing legacy rows marked with that status but missing a link are surfaced for reconciliation and cannot silently create a duplicate.

## Lightweight and focused evidence

- Focused `pytest` for `test_m29_s03_t003_prediction_action_loop.py`: 4 passed.
- `python -m py_compile` for modified backend model, service, API, schema, migration, and focused test: PASS.
- SQLAlchemy model import, mapper configuration, and maintenance endpoint import: PASS.
- `python -m alembic heads`: one head, `20261108_0026`.
- Scoped ESLint for predictive maintenance page/client: PASS.
- Scoped tracked `git diff --check`: PASS.
- Database migration execution, full backend/frontend suites, typecheck/build, and consolidated M29 code/security review remain pending M29.S04.

## Inputs reviewed

- `TASKS.md` M29.S03.T003 row.
- `coordination/milestones/M29/EXECUTION_PLAN_V01.md`.
- The applicable GAP-023 predictive-maintenance audit and its documented prediction/review lifecycle and permission context.

