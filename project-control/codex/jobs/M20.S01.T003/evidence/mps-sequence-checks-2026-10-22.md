# M20.S01.T003 — MPS invariant checks

Date: 2026-10-22
Checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`

## Passing local checks

From `backend/`:

```text
venv\Scripts\python.exe -m py_compile app\services\mps_service.py app\services\mps_whatif_service.py app\services\mps_capacity_service.py app\services\mps_campaign_service.py app\api\v1\endpoints\mps.py alembic\versions\20261022_0011_mps_number_sequences.py tests\test_mps_sequences.py tests\test_m20_v03_acceptance.py tests\test_m20_s01_t001_v02_mps_remediation.py
```

Result: exit 0.

```text
venv\Scripts\python.exe -m pytest tests\test_mps_sequences.py tests\test_m20_remaining_engine.py -q
```

Result: **40 passed in 2.86s**.

```text
venv\Scripts\python.exe -m pytest tests\test_m20_s01_t001_v02_mps_remediation.py -k "generate_from_mrp" -q
```

Result: **2 passed, 14 deselected in 1.53s**.

```text
venv\Scripts\python.exe -m alembic heads
```

Result: single head `20261022_0011`.

## Implemented invariant corrections

- MPS plan and line numbers use PostgreSQL sequences instead of table counts, preserving their existing formats.
- What-if scenario numbers use a separate global PostgreSQL sequence instead of `COUNT(*) + 1`, preserving `WI-{six uppercase plan UUID hex}-{minimum four digit suffix}` formatting.
- Migration seeds all three sequences from existing canonical numbers and locks all three source tables while seeding. Deployment comments require old MPS and what-if writers quiesced until sequence-backed code is active.
- MRP-driven line regeneration row-locks the plan before status checks and line replacement. Empty-demand regeneration deletes only unlocked stale lines, preserves the MRP source link, and refreshes counters for retained locked rows.
- Manual line edits lock the plan first and scoped line second, and reject non-DRAFT plans. The endpoint maps this lifecycle rejection to HTTP 400.
- Scenario creation locks the plan before snapshotting lines. Capacity scheduling, material-feasibility evaluation, and campaign grouping lock the plan and reject non-DRAFT plans before reading/mutating lines, including legacy entry points. Independent review found no remaining inspected MPS writer bypasses the parent lock before snapshot/recalculation.
- Local unit coverage checks allocation names/formats/fallbacks, parent/line lock ordering, empty-demand regeneration semantics, and non-DRAFT guards for manual edits, capacity scheduling, material feasibility, and both campaign runners. PostgreSQL acceptance coverage checks concurrent allocation and is guarded to run only on PostgreSQL.

## Environment limits

- Docker-backed PostgreSQL integration could not run because the Docker Desktop Linux engine pipe is unavailable (`npipe:////./pipe/dockerDesktopLinuxEngine`). Migration seeding, upgrade behavior, and real concurrent database behavior still need PostgreSQL execution evidence.
- Full `pytest tests\\test_m20_s01_t001_v02_mps_remediation.py -q` produced **12 passed and 4 setup errors**; the 4 app-fixture cases cannot import `app.core.security` because the checkout's `backend/venv` lacks `jwt` (`ModuleNotFoundError: No module named 'jwt'`). The focused MRP lineage tests above passed. No package was installed and no environment policy was changed.

## V05 F14–F16 follow-up

- SHIFT_ADD capacity is now left uncredited with `SHIFT_ADD_DOWNTIME_OVERLAP_UNRESOLVED` whenever same-work-center downtime overlaps the proposed date. The request has no added-shift time window, so overlap cannot be ruled out. Added hours remain recorded as uncredited assumptions. Existing daily 24-hour and configured shift-window checks remain in force.
- MERGE now validates both source quantities against configured batch size/count, permits different valid batch counts, and sums the derived count. SPLIT requires batch-aligned quantities and derives each part's count. Candidate `required_hours` is cleared for structural changes because the scenario capacity calculation derives hours from candidate quantity/rate; stale source hours are not copied into persisted candidate lines. Independent read-only review found no remaining concrete F14/F15 defect in the inspected scope.
- Focused verification: `pytest tests\\test_m20_v03_acceptance.py -k "shift_add or structural_scenarios" -q` — **2 passed, 4 deselected**; `pytest tests\\test_mps_sequences.py tests\\test_m20_remaining_engine.py -q` — **40 passed**; `python -m py_compile app\\services\\mps_whatif_service.py tests\\test_m20_v03_acceptance.py` — exit 0.
- PostgreSQL execution of the scenario acceptance test remains unavailable: `pytest tests\\test_m20_v03_acceptance.py -k test_postgres_whatif_merge_exact_split_and_added_shift_resimulate_without_live_mutation -q -x --tb=short` failed before scenario assertions with `ConnectionRefusedError: [WinError 1225]`. Running the complete V03 acceptance file yielded 2 unit passes and 4 PostgreSQL test failures at connection setup. No database evidence is claimed.
- V05-F16 is not limited to the mocked `frontend/e2e/m20-scenario-operations.spec.ts`: a separate real browser/API/PostgreSQL test, `frontend/e2e/m20-scenario-backend-roundtrip.spec.ts`, exists. The V03 execution log pins that source to commit `0b5033e28c12f7f2f202102496bb5c51d50723f4` and reports **1 passed in 18.2s**, HTTP 200 for plans/lines/list/reload and HTTP 201 for create, with a post-reload screenshot. The pinned commit is an ancestor of current HEAD and its test source matched the historical file exactly before the safety edit. The screenshot exists (384,003 bytes) and visually shows the scenario list and 100.0% / 0-delay KPIs after reload. This is builder-reported execution evidence, not a fresh independent rerun.
- For owner-data safety, the current browser test now selects only a finite plan whose number starts with the hardcoded disposable prefix `M20-OPS-PLAN-`; it will not choose arbitrary owner plans. The modified spec passes the local ESLint executable with no diagnostics. This small filter change has not been rerun against PostgreSQL because the local database endpoint is unavailable. The mocked E2E remains a frontend serialization contract test, while the separate roundtrip test supplies the actual browser/API/database path in the V03 evidence.
- The roundtrip test now skips before login or API access unless `M20_DISPOSABLE_TEST_DATABASE=1` is explicitly set. It persists scenario history without cleanup, so that opt-in is only for a task-owned disposable database. This guard prevents accidental default execution but does not prove the configured backend is disposable; a caller could still set the flag against shared data. The reviewer confirmed the guard’s placement and limitation. Focused ESLint after the guard exited 0; no browser test was run.
- Fresh isolated PostgreSQL browser/API rerun on 2026-10-22: created task-owned PostgreSQL 16 container `fmcg-m20-e2e-7e5883126fab` with loopback-only port `127.0.0.1:55432`, no mounted volume, freshly migrated through Alembic head `20261022_0011`, and synthetic plan `M20-OPS-PLAN-a20c852629` with an unlocked positive line. No shared or owner database was used. Ran with `M20_DISPOSABLE_TEST_DATABASE=1` and backend/frontend isolated on loopback ports 18001/13000: `playwright test e2e/m20-scenario-backend-roundtrip.spec.ts --project=chromium --no-deps --retries=0` — **1 passed in 10.0s**. Browser/API receipts: plans 200, plan lines 200, what-if list 200, scenario create 201, reload plans/list/lines 200. The saved SPLIT roundtrip rendered after reload with SL 100.0% and 0 delays. Post-reload visual evidence: `m20-scenario-backend-roundtrip-2026-10-22.png`.
- The first fresh rerun exposed a real middleware issue: `InputSanitizerMiddleware` replaced `_receive` after `request.body()` had populated Starlette's cached `_body`; nested `BaseHTTPMiddleware` replayed that cached body and later received an unexpected `http.request` instead of waiting for disconnect, ending the response with `No response returned`. The middleware now replaces the cached sanitized `_body`, preserving Starlette's receive/disconnect channel. Independent read-only review confirmed this is correct for the repository's installed Starlette implementation. The successful PostgreSQL-backed E2E above was run after this fix.
- Explicit owner-data gates recorded for future configuration; no values were fabricated: (1) minimum production run quantity with product or work-center scope, matching UOM, and effective period; (2) CIP duration with applicable work-center/transition or family scope, unit, effective period, and authoritative source; (3) changeover family mapping (or confirmation that `Product.category` is authoritative), work center/from-family/to-family, duration minutes, effectivity, and approved source; (4) approved scenario cost basis (hourly or unit/recipe basis), amount/rate, ISO currency, effective period, source, and FX conversion policy if currencies differ. Current diagnostics continue to report missing CIP/minimum-run and cost as unknown. The no-effective-Recipe release condition remains separate from BOM feasibility and must not be bypassed with synthetic recipe data.
- Updated the source-linked `MPSWhatIfScenario` invariant row in `backend/tests/fixtures/m20_invariant_matrix.json` to include the builder-reported real roundtrip evidence and distinguish it from current local independent verification. Independent read-only review confirmed the scenario invariants and clarified that added shift time has no inferred interval.
- Refreshed the matrix's approval/release, demand/supply, BOM/Recipe, work-center, capacity-diagnostic and campaign rows to distinguish validated API paths from legacy direct-service behavior. The review confirmed the documented BOM-feasibility versus Recipe-backed release distinction. A stale SalesOrder warehouse/UOM counterexample was qualified to legacy/direct calls; the active advanced projector uses exact source-warehouse scope and rejects order/product UOM mismatch.

## Completion and evidence chronology clarification — 2026-10-23

- The 2026-10-21 V05 audit correctly reports that it did not independently execute the browser/database test and that the then-reviewed frontend test was mocked. A separate task-owned PostgreSQL browser/API rerun was performed locally on 2026-10-22 and is recorded above; it passed 1/1 and persisted/reloaded the scenario. The review note saying no E2E was performed refers to the earlier safety-only review before that rerun; the later middleware follow-up records the successful execution and independent code review. These records describe different review times/scopes, not conflicting outcomes.
- The task queue previously had no valid state for a completed current task while waiting for an explicitly selected successor. Added `Current Task Status: COMPLETE` for a canonical `[x]` current row; the queue now reports successor selection as required when `Next Task/Action` does not name a different canonical task. Regression coverage also rejects empty task ledgers and orphan `[~]` rows. `node --test scripts/codex/task-queue.test.mjs` passed 15/15. An independent read-only reviewer confirmed the completion/handoff state and found no remaining transition defect.
- T003 is complete locally. No successor task was inferred, no owner data was fabricated, and no code was published or merged.
