# M23.S02.T003 — Material consumption confirmation

**Implementation state:** IMPLEMENTED; pending consolidated M23.S04 validation and acceptance.

## Scope and starting state

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Starting `HEAD` and fetched `origin/main`: `0db8dc68c971661dbda55f6992f3b4e70e4da84d` (divergence `0 0`).
- Root `TASKS.md` row and `coordination/milestones/M23/EXECUTION_PLAN_V01.md` were read. No T003-specific prompt, acceptance matrix, or M23 audit verdict exists in the repository. Applied `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md` (ERP-AL-003, 008, 010, 011, 012, 013), and `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` as applicable architecture/security guidance.
- The local tree already contained unrelated owner and prior-task changes. They were preserved; no reset, clean, restore, staging, commit, or push was performed.

## Implementation

- Added operation-scoped material listing and consumption to the authenticated Shop Floor API. Both require an active ERP-authenticated operator session bound to the exact started work order and its line scope.
- Consumption locks the parent execution order, work order, and material row; rejects inactive execution, foreign order/operation material, non-finite/non-positive quantities, inconsistent totals, non-issued material, quantities above issued-minus-consumed-minus-returned, and unrecorded/ambiguous lot selection.
- Writes the separate `exec_*` material consumed total and an attributable `MATERIAL_CONSUMPTION` activity record. No stock movement, standard production-model crosswalk, per-lot quantity allocation, or dual-write was invented. The UI labels lot references as trace-only because the current model has no issued quantity by lot.
- Added work-order parent validation when assigning an operation material. Issue and return amounts now reject non-finite values; a fully settled mixed consumed/returned line keeps the `CONSUMED` status when any quantity was consumed.
- Added an operator-terminal Materials panel, operation-only response/type, usage-manual guidance, and focused deferred tests.
- Independent read-only review found that the initially reused production-material response could expose `unit_cost` and `extended_cost` to scoped line operators. Replaced it with `SFOperationMaterialOut`, which omits costing fields, and received a clean read-only re-review. This log does not claim a separate ChatGPT audit verdict.

## Changed files for this task

- `backend/app/api/v1/endpoints/shop_floor.py`
- `backend/app/schemas/shop_floor.py`
- `backend/app/services/shop_floor_service.py`
- `backend/app/services/production_execution_service.py`
- `backend/tests/test_m23_s02_t003_material_consumption.py` (authored; not executed)
- `frontend/src/app/dashboard/shop-floor/terminal/page.tsx`
- `frontend/src/lib/shopFloor.ts`
- `docs/user-manual/module-manuals/manufacturing/08-shop-floor.md`

These source files also contain pre-existing M23/local edits; this list does not attribute their full accumulated diffs to T003.

## Checks and evidence

Passed:

- `python -m py_compile backend/app/services/production_execution_service.py backend/app/services/shop_floor_service.py backend/app/api/v1/endpoints/shop_floor.py backend/app/schemas/shop_floor.py backend/tests/test_m23_s02_t003_material_consumption.py`
- `cd frontend && npx eslint src/app/dashboard/shop-floor/terminal/page.tsx src/lib/shopFloor.ts`
- `cd frontend && npx tsc --noEmit --pretty false`
- `git diff --check` (passed; Git emitted existing LF-to-CRLF working-copy warnings).

The new T003 pytest cases were not run. Per the M23 execution plan, comprehensive API/database/UI/integration and security tests plus consolidated independent review are deferred to M23.S04; no test PASS, milestone acceptance, or merge is claimed here. No migration was required because the existing execution material and activity models already contain the operation link, quantity fields, lot references, and actor-attributed activity storage.

## Remaining boundaries

- Inventory balance posting and standard `ProductionOrder` / `WorkOrder` crosswalk remain out of scope and unverified.
- Per-lot quantity depletion is not representable by the current schema; selected lots are trace references only.
- Retry/idempotency protection for execution actions remains a later M23.S03 task.
- `TASKS.md` was read; task lifecycle transition is delegated to the authorized `scripts/codex/task-queue.mjs` command. No direct manual tracker edit was made for this log.
