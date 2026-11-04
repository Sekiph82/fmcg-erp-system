# M22.S03.T004 — Scheduling linkage to MPS

Date: 2026-11-04
Actor: CODEX
State: IMPLEMENTED; acceptance and M22 milestone verification pending.

## Scope and acceptance material

- Canonical scope: root `TASKS.md`, exact row `M22.S03.T004 — Scheduling linkage to MPS`.
- Domain boundary: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` identifies `ProductionOrder` as the canonical order with schedule/source/target warehouses and planning links; MPS remains a planning proposal that creates parent orders only through explicit release.
- Latest applicable planning audit: `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V06.md` and `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`. These are historical MPS audits, not an M22 task verdict. No M22.S03.T004-specific prompt, acceptance matrix, or audit artifact was present.
- The existing MPS contract stores the released order ID on its `MPSLine`, and maps planned line dates (or plan-range fallback) to canonical `ProductionOrder.scheduled_start` / `scheduled_end`. The MRP run owns the source warehouse; the release code previously failed to copy it to the production order.

## Implementation

- MPS release now assigns the source warehouse from its completed source MRP run to the created canonical `ProductionOrder`. It fails closed if that source warehouse is inactive, matching the downstream production-release readiness requirement and the existing active-target guard.
- Existing `MPSLine.production_order_id` remains the single association; no redundant MPS foreign key or schema migration was introduced. Existing planned-line dates continue to map to order schedule datetimes, with MPS plan dates as the established fallback.
- Added exact-loopback, passwordless, task-named disposable-PostgreSQL integration cases for MPS-line/order association, planned schedule propagation, source/target warehouse linkage, and inactive-source rejection without partial release state.
- Updated `TASKS.md` current sprint to M22.S03 to match the current task.

## Validation and review status

- `python -m py_compile backend/app/services/mps_service.py backend/tests/test_m22_s03_t004_mps_schedule_linkage_db.py` passed.
- A focused import check for `release_mps_plan` passed.
- `git diff --check`, `node scripts/codex/validate-task-state.mjs`, and `node scripts/codex/task-queue.mjs --check` passed while T004 was current.
- PostgreSQL integration tests, comprehensive M22 tests, and consolidated independent code/security review remain pending at M22 milestone acceptance. No runtime/database or audit PASS is claimed.

## Synchronization and preserved work

- Fetched `origin/main` before T004 claim; local `HEAD` and `origin/main` both resolved to `cc6610ea123e1d7285f0e7d4f5678925e1f70ef5` (0/0 divergence).
- The unrelated tracked owner edit `frontend/next-env.d.ts` and unrelated untracked files were not modified or staged.
- FormuLab and other checkouts were not modified.
