# M29.S01.T004 — Spare-parts availability prerequisite

## Outcome

Implemented explicit spare-part requirements on preventive-maintenance plans and transactional availability checks when scheduling PM work orders. Only quantities configured by the user are treated as requirements; no spare-part demand or stock is fabricated.

## Changes

- Added plan requirement and work-order reservation models, constraints, indexes, and migration `20261108_0020`.
- Added read/update API for plan requirements with current stock, active reservations, and available quantity.
- PM work-order creation locks the plan and required spare-part rows, rejects inactive/short stock with HTTP 409, and creates reservations in the same transaction.
- Spare-part usage now rejects quantities beyond free stock plus that work order's own remaining reservation. It reduces on-hand stock and the matching reservation together; other work orders' reserved stock remains protected.
- Manual stock reductions below active reservations and deactivation of parts still referenced by a plan/reservation are rejected.
- Added a plan requirements editor and availability preview. Scheduling is disabled while the live check is loading or refreshing, and unavailable required parts are shown. The editor button is shown only to `maintenance.edit` users.

## Validation evidence

- Python `py_compile` passed for the changed maintenance model, CRUD, schema, endpoint, model export, and migration modules.
- Imports of the new models, request schema, and maintenance router passed.
- Alembic reports `20261108_0020` as the current migration head; the migration was not applied to a database.
- Focused ESLint passed for `frontend/src/lib/maintenance.ts` and `frontend/src/app/dashboard/maintenance/plans/page.tsx`.
- Scoped `git diff --check` passed.
- Independent read-only review found no blocker and confirmed the stock/reservation accounting, migration/model alignment, and UI permission/fetch guards. No tests were run.

## Deferred verification

Per the M29 milestone test batching decision, database-backed migration and maintenance tests remain for M29.S04. No application database was modified by this task.
