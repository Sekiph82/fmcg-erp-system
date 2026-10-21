# M20 Master Production Scheduling — Consolidated Strict Remediation Log

Date: 2026-10-21  
Repository: `Sekiph82/fmcg-erp-system`, `main`  
Master prompt: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CODEX_M20_STRICT_REMEDIATION_MASTER_PROMPT_V01.md  
Original scope: all five M20 sprints / 20 tasks. Owner-added acceptance gates: UI-01 and UI-02. S01.T001 and S01.T002 retain their prior scoped acceptance; they were not reimplemented.

## Published implementation commit

- Remediation implementation commit: https://github.com/Sekiph82/fmcg-erp-system/commit/cc8a1019092510248db374fd93a34966a1f614d6
- Earlier M20 implementation commits: https://github.com/Sekiph82/fmcg-erp-system/commit/0d706241ccd623fdbf7cea7f21feededc8ea3f83 and https://github.com/Sekiph82/fmcg-erp-system/commit/14a96ec1aca124ec65ff913c1cfe2cecb4eba771
- Previously accepted S01.T001 commits: https://github.com/Sekiph82/fmcg-erp-system/commit/04c359e00eb20187f7033d1aaefca8b446fedc51, https://github.com/Sekiph82/fmcg-erp-system/commit/ea3d82d0f0925713917b85ec82c1b91530bae4a8, https://github.com/Sekiph82/fmcg-erp-system/commit/826891b92e731c14b87c5e574831cd334aeea4e5, https://github.com/Sekiph82/fmcg-erp-system/commit/cd552bffe8056279da67c828566ea9ee2d3a2c65, https://github.com/Sekiph82/fmcg-erp-system/commit/158d2816c8ac65a452a1eb3135f9f34defd30c1b, https://github.com/Sekiph82/fmcg-erp-system/commit/16c4beac69abe1c3200fa925d10a76f1bd043298, https://github.com/Sekiph82/fmcg-erp-system/commit/431130deee504a4d08aa15b5a950a3d126ff0da4, https://github.com/Sekiph82/fmcg-erp-system/commit/5d8e9667e51363ef0816960f6145f3bbe7c2f045, https://github.com/Sekiph82/fmcg-erp-system/commit/fade01ef89ba4a792f2be6fa17f1ddbe3d2e6410, and https://github.com/Sekiph82/fmcg-erp-system/commit/21612da51a3a7169d5031069a03aeb30d32b94df.
- Previously accepted S01.T002 commit: https://github.com/Sekiph82/fmcg-erp-system/commit/95176af0c1583d275c9d73e0135d34cfa4895c8a.

The implementation commit is based on the then-current `origin/main`, contains only scoped product/test changes, and does not change `TASKS.md`, audit files, or workflow files. The sole `main` workflow was inspected; it responds to `push`/`pull_request`. The commit message includes `[skip ci]`, which suppresses those workflow runs. No Actions workflow, dispatch, rerun, or remote CI was triggered. Remote CI evidence is `DEFERRED_CI_QUOTA` through 2026-10-30 inclusive. Owner-local changes remain in the working checkout.

## Twenty-task implementation and evidence matrix

“Implemented” describes code; “proof” describes executed evidence. These are builder results, not independent acceptance. T001/T002 have only their prior bounded acceptance.

| Task | Implementation, actual evidence, and remaining defect/proof limit |
|---|---|
| M20.S01.T001 | **Previously accepted, not repeated.** Historical bounded source/tests and commits above. |
| M20.S01.T002 | **Previously accepted, not repeated.** Historical preservation evidence and commit above. |
| M20.S01.T003 | **Implemented; partial proof.** Scope/eligibility invariants, explicit unknown inputs, and scenario validation are exercised by focused tests. Full tenant/warehouse/release transaction matrix remains incomplete. |
| M20.S01.T004 | **Implemented as synthetic fixtures only.** Acceptance and invariant JSON fixtures are linked below; they are not factory data or full integration acceptance. |
| M20.S02.T001 | **Implemented; local deterministic proof.** Date-safe daily/weekly/monthly buckets and conservation behavior are covered by `test_m20_remaining_engine.py`; integrated MRP→MPS DB path not fully proven. |
| M20.S02.T002 | **Implemented; partial proof.** Warehouse-scoped stock/reservation/dated-receipt/WIP/planned-supply netting is present. Historical test suite plus current focused tests do not establish all supply cases on PostgreSQL. |
| M20.S02.T003 | **Implemented; partial proof.** Nested approved BOM/subassembly recursion now checks lifecycle, effective dates, UOM, cycle and depth limits. Engine boundary/negative tests pass. Actual nested-BOM database material-feasibility path remains unverified. |
| M20.S02.T004 | **Implemented; partial proof.** Structured diagnostics persistence and constraints endpoint/UI exist. PostgreSQL migration is proven below; durable diagnostics/API transaction, duplicate replay, and rollback suite remains incomplete. |
| M20.S03.T001 | **Implemented; partial proof.** Finite capacity uses explicit rate UOM, calendars, holidays/maintenance and downtime; absent rates remain unknown and locked assignments are preserved. Focused local tests pass; not all real DB boundary cases are proven. |
| M20.S03.T002 | **Implemented with open master data.** Campaign sequencing and batch alignment diagnostics are present. Minimum-run policy is explicitly unknown because no authoritative configuration is present. |
| M20.S03.T003 | **Implemented with open master data.** Configured transition rows inform changeover calculations. Missing transitions and CIP durations stay unknown; no duration is fabricated. |
| M20.S03.T004 | **Implemented; partial proof.** Run IDs and affected line/work-center/slot diagnostics are produced. Complete committed DB persistence and cross-module scenarios remain unverified. |
| M20.S04.T001 | **Implemented; proof incomplete.** Approval/release guards, company/warehouse checks, all-or-none release behavior and retry guards exist. Historical release tests expose 15 stale fixture failures; no new successful full PostgreSQL rollback/concurrency release matrix is claimed. |
| M20.S04.T002 | **Implemented; proof incomplete.** Authenticated actor and warehouse scope checks are present. Maker-checker policy is not configured, so segregation is not claimed; full PostgreSQL permission/audit proof remains open. |
| M20.S04.T003 | **Implemented; partial proof.** Scenario inputs are isolated in savepoints for material evaluation; snapshots are versioned. Material rollback has a passing PostgreSQL test. Committed snapshot/replay/comparison transaction coverage is incomplete. |
| M20.S04.T004 | **Partial implementation.** Material resimulation reuses production feasibility logic and is covered by a passing PostgreSQL savepoint test. Capacity and configured changeover metrics are evaluated with explicit partial-input states. CIP duration and currency-backed cost deltas remain unknown; MERGE/SHIFT_ADD are rejected and SPLIT remains approximate. |
| M20.S05.T001 | **Partial verification.** Current focused engine + PostgreSQL scenario tests: 28 passed. Historical MPS regression suite on this checkout: 57 passed, 15 failed; all 15 are older release mock/PG fixtures that lack the newly required completed warehouse-scoped MRP run or current `_select_release_recipe` date argument. Failures are not called passes and remain to be reconciled. |
| M20.S05.T002 | **Frontend checks pass; strict UI gates tested.** Type-check/build pass; lint has zero errors and 67 warnings. Developer Portal E2E: 6 passed. Responsive full-width Playwright: 1 test passed across five viewport sizes and dashboard/integration tabs. React 18 deprecation and Browserslist/middleware warnings remain. |
| M20.S05.T003 | **Implemented; partial integration proof.** Migration upgrade/downgrade and real PostgreSQL scenario rollback have been run. Full release rollback/concurrency, permission/tenant, MRP→inventory/BOM→production order acceptance suite remains incomplete. |
| M20.S05.T004 | **Evidence log published; audit pending.** No tracker or ChatGPT audit file was changed. This is not milestone acceptance. |

## Strict findings F01–F10 closure

| Finding | Result |
|---|---|
| F01 PostgreSQL transaction/scope proof | **PARTIAL / BLOCKED_EVIDENCE.** Migration and scenario savepoint are proven; full release atomicity, rollback, concurrency, idempotency, permissions, tenant and warehouse matrix is not. |
| F02 nested BOM/subassembly explosion | **IMPLEMENTED; PARTIAL_EVIDENCE.** Recursive engine and negative tests pass; nested material feasibility through PostgreSQL is not yet proven. |
| F03 scenario material/changeover/cost resimulation | **PARTIAL.** Material baseline/candidate is database-tested; capacity/configured transition logic is present; CIP and approved-currency cost basis are absent and remain unknown. |
| F04 DB-backed service/API regressions | **PARTIAL.** A real PostgreSQL scenario no-mutation test passes. Release transaction and diagnostics persistence suite remains incomplete. |
| F05 UI behavioral evidence | **PASS FOR UI-01/UI-02 TEST GATES.** Browser E2E and viewport geometry tests pass; cross-system frontend tests beyond the listed routes remain incomplete. |
| F06 migration proof | **PASS FOR MIGRATION CHAIN TESTED.** Fresh upgrade, downgrade/re-upgrade, and predecessor upgrade/downgrade ran against local PostgreSQL through revision `20261021_0010`. |
| F07 minimum-run/CIP/configuration | **OPEN MASTER DATA.** No authoritative minimum-run or CIP policy was present; unknown states are preserved. |
| F08 milestone closure | **OPEN.** This log is evidence only; strict blockers and independent audit remain. |
| F09 task traceability | **PARTIAL.** Twenty task rows, F01–F10 mapping, full commit links, source/test/schema URLs and commands are included. Rows do not imply independent task acceptance. |
| F10 historical MPS regressions on current source | **FAIL / OPEN.** Re-run result is 57 passed, 15 failed; failures listed above are stale release fixtures/expectations and remain unresolved. |

## UI-01 — responsive full available content area

Removed narrow centered wrappers from the dashboard, integration overview/tabs, Webhooks and Developer views while preserving the sidebar and page padding. The browser test checks actual content/main-region geometry, horizontal overflow, headings and usability at 1536×960, 1920×1080, 1366×768, 768×1024 and 390×844. It visits Dashboard and the integration views (Overview, M-Pesa, Sync, Barcode, Logs, Webhooks, Developer) and saves screenshot artifacts under ignored local Playwright output.

Actual command, run against the live local app: `E2E_SKIP_WEBSERVER=1 npx playwright test e2e/m20-responsive-dashboard.spec.ts --project=chromium --no-deps --retries=0` — **1 passed (1.6m)**. The test iterates the viewport/tab combinations inside one Playwright test; no GitHub-hosted screenshots are claimed.

## UI-02 — Developer Portal errors and Next.js outdated popup

Root cause: Developer Portal requests used a separate relative-URL API wrapper that could hit the Next.js origin; error responses, including Next 404 HTML, were parsed as JSON and surfaced as uncaught runtime errors. Requests now use the configured backend API base and credentials, check HTTP status/content type before parsing, apply a bounded timeout, and return concise sanitized errors with retryable UI state. Backend Developer Portal routes and API key schema/migration are registered. Frontend Next.js was upgraded from **14.2.35** to **16.4.2**, removing the reported outdated-version popup in the running local app.

Actual E2E command: `E2E_SKIP_WEBSERVER=1 npx playwright test e2e/developer-portal-errors.spec.ts --project=chromium --no-deps --retries=0` — **6 passed (19.6s)**. Coverage: successful configured backend response, HTML 404, 401, 403, HTML 200/invalid JSON, 500 and retry/recovery states. Local smoke confirmed backend Developer route responses `200, 200`; the browser E2E ran with live frontend/backend. No credentials or raw HTML are exposed in the error state.

## PostgreSQL and local verification

- `docker exec fmcg-erp-system-backend-1 pytest -q tests/test_m20_postgres_scenario_savepoint.py tests/test_m20_remaining_engine.py --tb=short` — **28 passed, 1 deprecation warning**. PostgreSQL scenario uses an approved recipe, compares baseline 2 KG vs candidate 20 KG shortage, and confirms temporary line edits and diagnostic rows are rolled back.
- `docker exec fmcg-erp-system-backend-1 pytest -q tests/test_m20_remaining_engine.py tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_s01_t002_mps_preservation.py --tb=no` — **57 passed, 15 failed**. Failures: `test_release_blocks_all_orders_when_ineligible_lines_exist`; `test_release_rejects_nonexistent_warehouse`; `test_release_rejects_inactive_warehouse`; `test_select_release_recipe_returns_the_queried_recipe`; `test_release_skips_line_when_no_approved_effective_recipe_exists`; `test_release_sets_production_order_uom_from_product`; `test_release_stays_approved_when_every_feasible_line_is_skipped`; `test_release_becomes_released_when_at_least_one_order_is_created`; `test_repeated_release_call_is_rejected_and_creates_no_second_order`; `test_mixed_partial_release_remains_approved_and_reports_unresolved_lines`; three `test_release_fails_closed_for_missing_or_invalid_authoritative_product_uom` cases; `test_release_endpoint_rolls_back_persisted_state_on_late_flush_failure`; and `test_concurrent_postgres_mps_releases_allocate_distinct_order_numbers`. Do not interpret these as acceptance evidence.
- Frontend: `npm run type-check` — passed. `npm run lint` — passed with **0 errors, 67 warnings**. `npm run build` — passed, static generation **699/699**; warnings include React 18 support deprecation under Next 16, legacy middleware convention, stale Browserslist data and parent lockfile notice.
- Migration DBs: `fmcg_erp_m20_acceptance` upgraded predecessor `20261020_0010` to `20261021_0010`, verified both MPS diagnostics/snapshot and Developer Portal tables, downgraded to `20261020_0010` (removing the two new developer-key tables), then re-upgraded. `fmcg_erp_m20_full_migrations` upgraded from empty to `20261021_0010` (657 public tables), downgraded to `20261019_0010` and re-upgraded. These were local PostgreSQL runs; they are not remote CI evidence.
- `python -m alembic heads` — one head `20261021_0010`.
- Historical migration wrapper also showed the existing offline `--sql` path stops in `20260516_0060_performance_indexes.py` when its catalog query returns no row; online PostgreSQL migration tests above are the migration evidence.
- GitHub Actions / remote CI: **not run; `DEFERRED_CI_QUOTA` through 2026-10-30**.

## Source, test, migration, and fixture links

- MPS engine: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/services/mps_engine.py
- MPS demand/material diagnostics: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/services/mps_advanced_service.py
- MPS capacity: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/services/mps_capacity_service.py
- MPS campaigns: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/services/mps_campaign_service.py
- MPS plan/release: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/services/mps_service.py
- MPS scenario engine: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/services/mps_whatif_service.py
- MPS API: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/api/v1/endpoints/mps.py
- MPS/diagnostic/snapshot models: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/models/mps.py
- Diagnostics and immutable scenario migration: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/alembic/versions/20261020_0010_mps_diagnostics_and_scenario_snapshots.py
- Developer Portal API/models: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/api/v1/endpoints/api_portal.py and https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/app/models/api_portal.py
- Developer Portal API-key migration: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/alembic/versions/20261021_0010_developer_portal_api_keys.py
- Recursive engine + boundary regressions: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/tests/test_m20_remaining_engine.py
- PostgreSQL savepoint proof: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/tests/test_m20_postgres_scenario_savepoint.py
- Synthetic acceptance fixture: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/tests/fixtures/m20_acceptance_dataset.json
- Invariant matrix: https://github.com/Sekiph82/fmcg-erp-system/blob/main/backend/tests/fixtures/m20_invariant_matrix.json
- MPS frontend types/API: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/lib/mps.ts
- MPS dashboard: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/mps/page.tsx
- MPS what-if comparison: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/mps/whatif/page.tsx
- MPS constraints screen: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/mps/constraints/page.tsx
- Responsive dashboard E2E: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/e2e/m20-responsive-dashboard.spec.ts
- Developer Portal error/retry E2E: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/e2e/developer-portal-errors.spec.ts
- Developer Portal API client: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/lib/api_portal_api.ts
- Dashboard shell: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/components/DashboardShell.tsx
- Integration overview and tabs: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/integrations/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/integrations/mpesa/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/integrations/sync/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/integrations/barcode/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/integrations/logs/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/webhooks/page.tsx, and https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/src/app/dashboard/developer/page.tsx
- Frontend dependency versions: https://github.com/Sekiph82/fmcg-erp-system/blob/main/frontend/package.json

## Remaining blockers

1. The historical MPS test suite remains red at 57 passed / 15 failed, chiefly because mock/PG release fixtures do not supply the required completed, warehouse-scoped MRP run and one recipe helper does not supply `as_of`. This must be reconciled without weakening scope/release checks.
2. Full PostgreSQL release atomicity/late rollback/concurrency/idempotency and tenant/permission boundary matrix has not passed; scenario savepoint and migration proof do not replace it.
3. Nested BOM material feasibility has unit boundary coverage but lacks a real PostgreSQL nested-BOM service test.
4. Minimum-run/CIP duration and approved-currency cost basis are not configured; related scenario outputs remain explicitly unknown. MERGE/SHIFT_ADD are unsupported and SPLIT remains an approximation.
5. Remote CI remains deferred through 2026-10-30. No Actions run was started.
6. Independent ChatGPT audit and any canonical tracker update remain pending. `TASKS.md`, `TASKS_HISTORY.md` and ChatGPT audit files were not modified.

Milestone disposition: **AWAITING_CHATGPT_MILESTONE_AUDIT**. This report does not self-accept M20 or mark any task newly accepted.
