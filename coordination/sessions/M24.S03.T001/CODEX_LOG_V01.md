# M24.S03.T001 implementation log

**Status:** IMPLEMENTED; pending consolidated M24 acceptance in S04.T004.  
**Task authority:** root `TASKS.md`, exact task `M24.S03.T001 — WIP transfer/location model`.  
**Acceptance material:** `coordination/milestones/M24/EXECUTION_PLAN_V01.md`, S03 batch scope and T001 implementation assumptions.  
**Starting Git state:** `HEAD` and fetched `origin/main` both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`; divergence `0/0`. Existing local work was preserved. At task start there were 349 non-`.hiveai` status paths, including unrelated pre-existing changes; no reset, clean, stash, or broad staging was performed.

## Implementation

- Reused the existing posted `INTERMEDIATE_CREATE` and `STAGE_TRANSFER` material-flow records as the append-only WIP location ledger. Added typed WIP output, transfer, and balance contracts without introducing a duplicate inventory table or changing warehouse stock.
- Added authenticated WIP output and transfer routes scoped to the production order's source warehouse. Output is limited to the order product, order UOM, in-progress status, configured stage/location, and remaining planned quantity. Stage transfers retain exact output-line origin, batch, quality, and location lineage; partial transfers leave balances at both locations.
- Derived available WIP balances from posted output and transfer records. Production-order row locks serialize quantity checks; transaction-scoped advisory locks serialize globally unique idempotency keys. Identical retries return the original posting. Generic transaction, confirmation, transfer, and reversal paths cannot bypass the WIP posting/correction workflow.
- Replaced the WIP page's arbitrary generic transfer form with measured output, balance-by-location, and exact-origin transfer forms.
- Added guarded PostgreSQL acceptance cases for partial transfer balances, idempotency, overdraw, output over-plan, and stage/location mismatch. These tests were authored but not run; M24 plan defers the full database/API/frontend/E2E suite to S04.T004.
- Recorded the virtual WIP assumptions in `coordination/milestones/M24/EXECUTION_PLAN_V01.md`. The five generated `.next-m20-*` directories remain on disk and are now ignored by the targeted `.gitignore` pattern, reducing Git's active change set without deleting output.

## Changed files for this task

- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/app/schemas/material_flow.py`
- `backend/tests/test_m24_s03_t001_wip_location_db.py` (new)
- `frontend/src/app/dashboard/material-flow/wip-transfer/page.tsx`
- `frontend/src/lib/materialFlow.ts`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `.gitignore` (targeted generated-output ignore rule, also resolves the reported Git change-count warning)

## Checks and review

- `python -m py_compile app/api/v1/endpoints/material_flow.py app/services/material_flow_service.py app/schemas/material_flow.py tests/test_m24_s03_t001_wip_location_db.py` — passed.
- `ruff check app/api/v1/endpoints/material_flow.py app/services/material_flow_service.py app/schemas/material_flow.py tests/test_m24_s03_t001_wip_location_db.py` — passed.
- `npx eslint src/app/dashboard/material-flow/wip-transfer/page.tsx src/lib/materialFlow.ts` — passed.
- `python -c "from app.main import app; from app.db.base import Base; print('routes', len(app.routes), 'tables', len(Base.metadata.tables))"` — passed (`routes 10`, `tables 723`); emitted two existing FastAPI `regex` deprecation warnings from `allergen.py`.
- `alembic heads` — one head: `20261108_0017` (no new migration required because this task uses existing material-flow lineage columns).
- `git diff --check` for the changed files — passed; Git emitted the existing Windows LF-to-CRLF normalization notice for the new page.
- Independent read-only review found and the implementation corrected self-attributed approval, state-dependent retry behavior, same-order/cross-order idempotency races, and UOM normalization. Final review found no remaining critical issue. The reviewer did not run tests or edit files.
- No PostgreSQL, API, frontend build, or E2E tests were run. No approval, merge, commit, or push is claimed. The worktree still contains unrelated owner/project changes, so task implementation remains local pending consolidated milestone review.

## Queue state

`TASKS.md` was read and advanced through `scripts/codex/task-queue.mjs`: M24.S03.T001 is `[v]` IMPLEMENTED pending milestone verification, and M24.S03.T002 — Bulk/intermediate transfer is the exact selected successor. The current sprint header now reflects M24.S03. The tracker was revalidated after the transition. `origin/main` was fetched before implementation and remains unchanged; no push was made because the worktree contains hundreds of unrelated or earlier task changes.
