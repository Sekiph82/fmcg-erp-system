# M22.S02.T001 — Routing/work-center operation sequencing

Date: 2026-11-04
Actor: CODEX
State: Implementation and independent read-only review complete; milestone verification pending.

## Scope and acceptance material

- Canonical task: root `TASKS.md`, exact row `M22.S02.T001 — Routing/work-center operation sequencing`.
- Generated implementation handoff: `node scripts/codex/task-queue.mjs --spec`, status `SPEC_READY`, for this exact task.
- Domain acceptance: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`. A canonical `WorkOrder` is one operation under its `ProductionOrder`; it retains its routing step, sequence, work-center assignment and operation identity. The active `exec_*` model family remains separate. The document warns against inferring identity, cross-linking, deleting, merging, or silently relinking parallel records.
- Governance and latest applicable audit material: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, and `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`. V06 is an M20 verdict, not an M22 task audit. No M22.S02.T001-specific criteria or audit was present in the repository.
- Scope boundary: routing sequence display/generation is implemented for the canonical order family. Operation predecessor/start gates remain in the separately named M22.S03.T002 scope; no parallel-group semantics were inferred from the existing `is_parallel` flag.

## Synchronization and preserved work

- Starting `HEAD` and fetched `origin/main`: `cf05ac41e35bb91ff6c4ae4865b38f11eeae26d0`; divergence was 0 ahead / 0 behind.
- The unrelated tracked owner change in `frontend/next-env.d.ts` and other unrelated local/untracked artifacts were left unstaged and unchanged.
- The M22.S01.T004 commit was pushed and verified equal to `origin/main` before this task was claimed.
- FormuLab and other checkouts were not modified.

## Implementation

- Added an authenticated route-generation API for a planned, unapproved canonical production order. It validates that the selected active routing belongs to the order product, has steps, and uses active work centers; it creates one planned child `WorkOrder` per step in ascending step order with the routing's operation and work center, parent planned quantity and attributable creation history.
- Repeated generation returns the existing complete matching route set; partial/manual/mixed child sets fail without replacement. Route-bound manual creates must match the routing product, operation and work center, and a parent cannot mix routing versions or duplicate a step.
- Added a database uniqueness rule for one routing step per production order. The migration checks for legacy duplicates and route/product/operation/work-center mismatches, then fails with an explicit message rather than rewriting records. The routing-step FK changes from `SET NULL` to `RESTRICT`; ORM relationships and CRUD checks preserve sequence identity and prevent deletion of referenced steps/routings.
- Work-order listing now returns route-bound operations in parent/routing-step order, and the production-order detail UI can generate and display operations with step, operation, work center and quantities.
- Input validation rejects blank operation names, non-positive step numbers and negative standard/setup durations. CSV manual work-order import rejects inactive work centers and cannot mix manual rows into a routing-sequenced order.
- No `exec_*` records were changed or cross-walked; no existing records were backfilled or fabricated.

## Independent review

- Independent read-only review: `/root/m22_s02_t001_review`.
- Initial review found that ORM parent deletion could null a child's routing-step reference before PostgreSQL enforced `ON DELETE RESTRICT`. The relationship now uses `passive_deletes="all"`; a deferred PostgreSQL test asserts direct step and routing deletion fail while referenced.
- Follow-up review confirmed the FK guard remains authoritative and the import path preserves the routed/manual boundary. Final review also checked the migration's mismatch preflight and deferred DB assertions. No remaining blockers were reported. Reviewer did not edit files or run tests.

## Checks and limitations

- `git diff --check`: passed for the tracked implementation changes before final staging; final staged check and task-state validation are recorded at closure.
- A task-owned PostgreSQL integration test was added at `backend/tests/test_m22_s02_t001_routing_sequence_db.py`. Automated tests, type-check/build, migration execution, database upgrade/downgrade and runtime acceptance were intentionally deferred to the M22 milestone test batch under the owner's requested test cadence. No test or migration PASS is claimed.
- Migration upgrade includes a duplicate-link preflight. If an existing deployment has duplicate `(production_order_id, routing_step_id)` rows, the migration will stop and require explicit data resolution; it does not guess which record to preserve.
- No production-factory or live-employee behavior is claimed.

## Changed paths

- `backend/alembic/versions/20261104_0004_m22_routing_work_order_sequence.py`
- `backend/app/api/v1/endpoints/bulk_import.py`
- `backend/app/api/v1/endpoints/production_advanced.py`
- `backend/app/crud/production_advanced.py`
- `backend/app/models/production_advanced.py`
- `backend/app/schemas/production_advanced.py`
- `backend/tests/test_m22_s02_t001_routing_sequence_db.py`
- `frontend/src/app/dashboard/production/orders/[id]/page.tsx`
- `frontend/src/lib/productionAdvanced.ts`
- `coordination/sessions/M22.S02.T001/CLAUDE_LOG_V01.md`

`TASKS.md` is updated only through the canonical task-queue script.
