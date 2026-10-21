# M20 Master Production Scheduling — Consolidated Strict Remediation Log

Date: 2026-10-21  
Repository: `Sekiph82/fmcg-erp-system`, `main`  
Master prompt: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CODEX_M20_STRICT_REMEDIATION_MASTER_PROMPT_V01.md  
Original scope: all five M20 sprints / 20 tasks. Owner-added acceptance gates: UI-01 and UI-02. S01.T001 and S01.T002 retain their prior scoped acceptance; they were not reimplemented.

## Published implementation commit

- Audit V04 MERGE, exact SPLIT, SHIFT_ADD, finite-capacity resimulation and browser evidence capture: https://github.com/Sekiph82/fmcg-erp-system/commit/402f699e1e2e4cd8e04a9106157f012a4f21780c
- Strict V02 remediation, release integrity, Developer Portal auth/client, dependency fixes and regression tests: https://github.com/Sekiph82/fmcg-erp-system/commit/4c1d5dd8578713e25166eb1e9e46c2ff3722e278
- Remediation implementation commit: https://github.com/Sekiph82/fmcg-erp-system/commit/cc8a1019092510248db374fd93a34966a1f614d6
- PostgreSQL route authorization/transaction, committed MRP→MPS scenario replay, and asyncpg test-lifespan remediation: https://github.com/Sekiph82/fmcg-erp-system/commit/3c5bc31e30131c9acf5de900155b0e68580a061c
- Historical regression fixture alignment and PostgreSQL release proof: https://github.com/Sekiph82/fmcg-erp-system/commit/bb09ccadd158a5693d78298ffd11dad3aa56eecf
- Nested BOM integration and enum normalization: https://github.com/Sekiph82/fmcg-erp-system/commit/9976b20975b26254f7a3811b5aa8ace147651f94
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
| M20.S01.T003 | **Implemented; PostgreSQL route matrix added.** Positive scoped release, denied target warehouse, denied other-company source plan, actor without permission, idempotent retry, audit provenance, and post-flush transaction rollback are exercised through the real FastAPI route against PostgreSQL. Other tenant permutations remain outside the seeded matrix. |
| M20.S01.T004 | **Implemented as synthetic fixtures only.** Acceptance and invariant JSON fixtures are linked below; they are not factory data or full integration acceptance. |
| M20.S02.T001 | **Implemented; local deterministic proof.** Date-safe daily/weekly/monthly buckets and conservation behavior are covered by `test_m20_remaining_engine.py`; integrated MRP→MPS DB path not fully proven. |
| M20.S02.T002 | **Implemented; partial proof.** Warehouse-scoped stock/reservation/dated-receipt/WIP/planned-supply netting is present. Historical test suite plus current focused tests do not establish all supply cases on PostgreSQL. |
| M20.S02.T003 | **Implemented; integrated PostgreSQL proof.** Nested approved BOM/subassembly recursion checks lifecycle, effective dates, UOM, cycle and depth limits. The PostgreSQL scenario test now evaluates a real root BOM → approved child BOM → material path and validates 2 KG baseline vs 20 KG candidate shortage with savepoint rollback. |
| M20.S02.T004 | **Implemented; partial proof.** Structured diagnostics persistence and constraints endpoint/UI exist. PostgreSQL migration is proven below; durable diagnostics/API transaction, duplicate replay, and rollback suite remains incomplete. |
| M20.S03.T001 | **Implemented; partial proof.** Finite capacity uses explicit rate UOM, calendars, holidays/maintenance and downtime; absent rates remain unknown and locked assignments are preserved. Focused local tests pass; not all real DB boundary cases are proven. |
| M20.S03.T002 | **Implemented with open master data.** Campaign sequencing and batch alignment diagnostics are present. Minimum-run policy is explicitly unknown because no authoritative configuration is present. |
| M20.S03.T003 | **Implemented with open master data.** Configured transition rows inform changeover calculations. Missing transitions and CIP durations stay unknown; no duration is fabricated. |
| M20.S03.T004 | **Implemented; partial proof.** Run IDs and affected line/work-center/slot diagnostics are produced. Complete committed DB persistence and cross-module scenarios remain unverified. |
| M20.S04.T001 | **Implemented; PostgreSQL release boundaries pass.** Company/source/target warehouse checks, all-or-none release, idempotent retry and audit creation pass positive and negative route tests, including rollback after order flush. Concurrent PO-number allocation also passes. |
| M20.S04.T002 | **Implemented; PostgreSQL authorization and audit pass.** The real route accepts the scoped actor, denies the actor without permission, enforces source and target warehouse scope, and writes one release audit event. No maker-checker policy is configured; segregation is not claimed. |
| M20.S04.T003 | **Implemented; committed PostgreSQL snapshot replay passes.** Seeded MRP→MPS scenarios persist versioned assumptions/results, replay the same comparison after commit, preserve the live plan, reject duplicate versions, and prove rollback of temporary scenario writes. |
| M20.S04.T004 | **Implemented for configured inputs; master-data limits remain.** MERGE combines only schedule-equivalent lines, exact SPLIT creates two quantity-conserving candidate lines, and SHIFT_ADD adds date/work-center finite-capacity hours. PostgreSQL tests verify merged quantity, exact split conservation, capacity overload reduction and unchanged live plan lines. Minimum-run policy, CIP duration and currency cost basis remain `OWNER_DATA_REQUIRED`; do not infer those outputs. |
| M20.S05.T001 | **Local regression PASS.** The final strict PostgreSQL/local suite has 77 passing tests, including seeded cross-module release, permission/scope negatives, audit provenance, snapshot replay and rollback. No asyncpg unraisable-coroutine warning remains after isolating the route-test lifespan. Existing SQLAlchemy/Pydantic/passlib deprecation warnings remain. |
| M20.S05.T002 | **Local frontend checks pass; independent audit remains pending.** Type-check and production build pass on Next.js 16.4.2; build generated 699/699 static pages. Lint exits 0 with 0 errors and 67 warnings. Final browser suite passes 12 tests, including five viewport widths, all nine integration tabs, API Keys/GraphQL, scenario JSON contracts and Developer Portal 401/404/403/500/invalid-JSON/timeout behavior. Seventeen masked screenshots and four sanitized Playwright traces are published under evidence/v04. Production dependency audit remains 0 vulnerabilities; full dev-tree audit still reports 9 advisories. |
| M20.S05.T003 | **Local PostgreSQL integration PASS with bounded scope.** Migration upgrade/downgrade, nested BOM material evaluation, demand-to-MPS creation, diagnostics, scenario rollback/replay, approval, production release, permission/scope denials and release rollback ran against PostgreSQL. No factory master data was fabricated. |
| M20.S05.T004 | **Evidence log published; audit pending.** No tracker or ChatGPT audit file was changed. This is not milestone acceptance. |

## Strict findings F01–F10 closure

| Finding | Result |
|---|---|
| F01 PostgreSQL transaction/scope proof | **PASS FOR THE EXECUTED MATRIX; REMAINING TENANT PERMUTATIONS OPEN.** Real PostgreSQL route tests cover successful scoped release, wrong target warehouse, wrong-company source plan, missing release permission, repeat release, one audit event, and transaction rollback after order flush. The endpoint rechecks permission and plan/target warehouse scope before each release attempt. This does not claim every tenant configuration permutation. |
| F02 nested BOM/subassembly explosion | **PASS (LOCAL POSTGRESQL).** Recursive engine boundary/negative tests and root → approved child → material feasibility are exercised against PostgreSQL; baseline/candidate shortage quantities are verified and temporary writes roll back. |
| F03 scenario material/changeover/cost resimulation | **PARTIAL WITH OPERATIONS IMPLEMENTED.** PostgreSQL tests execute MERGE, exact two-part SPLIT and finite-capacity SHIFT_ADD resimulation, including exact 100 kg conservation, overload reduction from 2 to 0 hours after adding 2 shift hours, and no live-plan mutation. Existing MRP/BOM/material scenario proof remains. Minimum-run, CIP and currency inputs are `OWNER_DATA_REQUIRED`; full master-data-dependent scenario acceptance stays open. |
| F04 DB-backed service/API regressions | **PASS FOR THE EXECUTED LOCAL SUITE.** PostgreSQL diagnostics are committed across runs; immutable scenario snapshots replay identically after commit; duplicate versions fail; savepoint and release transaction rollback pass; route authorization and audit provenance pass. The asyncpg `Connection._cancel` warning was traced to production startup running in the route TestClient's private loop; route-level tests now use an isolated no-op lifespan. The final 77-test run emitted no unraisable warning. |
| F05 UI behavioral evidence | **BUILDER PASS / INDEPENDENT AUDIT PENDING.** Twelve local browser tests pass with full-width geometry, live backend route responses and safe error-state checks. Seventeen viewport/portal screenshots and four sanitized Playwright traces are published below. Independent visual audit is still required. |
| F06 migration proof | **PASS FOR MIGRATION CHAIN TESTED.** Fresh upgrade, downgrade/re-upgrade, and predecessor upgrade/downgrade ran against local PostgreSQL through revision `20261021_0010`. |
| F07 minimum-run/CIP/configuration | **OPEN MASTER DATA.** No authoritative minimum-run or CIP policy was present; unknown states are preserved. |
| F08 milestone closure | **OPEN.** This log is evidence only; strict blockers and independent audit remain. |
| F09 task traceability | **BUILDER EVIDENCE PUBLISHED; ACCEPTANCE PENDING.** The 20 task rows, F01-F13 mapping, full implementation commit URLs, source/test/schema links, exact commands/results, screenshots and traces are in this log. Rows do not imply independent task acceptance. |
| F10 historical MPS regressions on current source | **PASS (LOCAL REGRESSION).** Combined strict MPS + scenario suite: 77 passed with `-W always::pytest.PytestUnraisableExceptionWarning`; no assertion was weakened. This does not replace independent audit or all factory-data-dependent acceptance. |

## Strict findings F11–F13 closure

| Finding | Result |
|---|---|
| F11 released-plan idempotency integrity | **SOURCE FIX + LOCAL POSTGRESQL NEGATIVE PASS; SCOPE MATRIX OPEN.** A retry now checks every positive-quantity MPS line has a surviving production order and rejects deleted/missing links instead of returning partial success. A real PostgreSQL test deletes the linked order (the FK nulls the line link) and confirms retry fails closed. The release route executes the normal release permission, source-plan warehouse and target warehouse scope guards before both first release and retry. Full wrong-actor/tenant/company/warehouse route matrix remains open. |
| F12 material calculation status semantics | **LOCAL POSTGRESQL PASS.** A calculated material shortage remains `COMPLETE` with a shortage quantity/count delta; absent approved BOM/recipe input returns `PARTIAL_INPUTS`, unknown reasons and a null delta. Both cases are covered by PostgreSQL scenario tests. |
| F13 Developer Portal response/auth contract | **IMPLEMENTED; LOCAL BROWSER PASS; INDEPENDENT EVIDENCE PENDING.** Requests now go through the configured Axios client, including its credential and response-interceptor behavior. The browser verifies 401 sign-in redirect, real dashboard/resources/API key/GraphQL backend routes, and safe 404/403/500/invalid-JSON/timeout responses. Production dependency audit is clean; 9 dev-tree advisories remain because npm's compatible fix requires a Tailwind 4 / lint-tooling major migration. |

## UI-01 — responsive full available content area

Dashboard, integration overview/tabs and Developer Portal screens retain the full main content width beside the sidebar. Playwright measured horizontal overflow and main/content geometry at 1536x960, 1920x1080, 1366x768, 768x1024 and 390x844. It visits Dashboard and all nine integration views. API Keys and GraphQL are also measured at desktop and phone widths. Seventeen screenshots are published in the evidence directory; screenshot capture masks the seeded account email. Four traces were sanitized for credentials, authorization/cookie values and email addresses. These builder artifacts support independent review but do not constitute audit acceptance.

Final actual command (PowerShell, from `frontend/`): `$env:E2E_SKIP_WEBSERVER='1'; $env:E2E_BASE_URL='http://localhost:3000'; npx playwright test e2e/m20-scenario-operations.spec.ts e2e/m20-responsive-dashboard.spec.ts e2e/developer-portal-errors.spec.ts e2e/m20-developer-portal-auth.spec.ts --project=chromium --no-deps --retries=0 --workers=1 --trace on` — **12 passed (1.7m)**.

## UI-02 — Developer Portal errors and Next.js outdated popup

The root cause and fix are documented above: Developer Portal requests now use the configured Axios API client, non-JSON and non-2xx replies are handled safely, requests time out, and unsafe response bodies are not rendered. A 401 follows the session redirect to `/login`. The app is on Next.js **16.4.2** rather than the reported outdated 14.2.35. The final 12-test suite covers live dashboard/resources/API-key/GraphQL responses, 401 recovery, HTML 404/403/500, malformed JSON and timeouts. Published UI-02 screenshots cover Developer Portal overview, API Keys/GraphQL at desktop and phone, safe 404 state and 401 recovery. Independent visual review is pending.

## PostgreSQL and local verification

- `docker exec fmcg-erp-system-backend-1 pytest -q tests/test_m20_postgres_scenario_savepoint.py tests/test_m20_remaining_engine.py --tb=short` — **28 passed, 1 deprecation warning**. PostgreSQL scenario uses a root BOM → approved child BOM → material path, compares baseline 2 KG vs candidate 20 KG shortage, and confirms temporary line edits and diagnostic rows are rolled back.
- `docker exec fmcg-erp-system-backend-1 pytest -q -W always::pytest.PytestUnraisableExceptionWarning tests/test_m20_strict_findings.py tests/test_m20_remaining_engine.py tests/test_m20_postgres_scenario_savepoint.py tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_s01_t002_mps_preservation.py tests/test_m20_v03_acceptance.py --tb=short` — **77 passed, 69 warnings in 30.64s**. PostgreSQL-backed coverage includes nested BOM material feasibility, diagnostic history, persisted snapshot replay and duplicate-version rejection, scenario/savepoint rollback, company/warehouse/permission route denials, successful and repeated release, audit provenance, post-flush release rollback, deleted-order retry fail-closed, and concurrent PO sequence allocation. No unraisable asyncpg warning occurred; 69 existing deprecation warnings remain.
- Frontend: `$env:NODE_OPTIONS='--max-old-space-size=4096'; npm run type-check` — passed. Exact-checkout E2E lint: `npx eslint e2e/m20-scenario-operations.spec.ts e2e/m20-responsive-dashboard.spec.ts e2e/developer-portal-errors.spec.ts e2e/m20-developer-portal-auth.spec.ts` — passed. Product lint: `npm run lint -- --ignore-pattern 'playwright-report/**' --ignore-pattern 'test-results/**'` — exit 0, **0 errors, 67 warnings**. `npm run build` on Next.js 16.4.2 — passed; TypeScript and static generation **699/699** succeeded. Warnings include React 18 support deprecation, legacy middleware convention, Browserslist data and parent lockfile notice.
- `npm audit --omit=dev --audit-level=moderate` — **0 vulnerabilities** after compatible dependency manifest and lockfile updates (including axios 1.16.1→1.20.0 and Next.js 14.2.35→16.4.2). Full `npm audit` still reports **9 dev-tree findings (7 high, 2 moderate)** in Tailwind 3 / ESLint transitive dependencies. npm's proposed clean fix requires Tailwind 4 and lint-tooling major changes; no `--force` upgrade was applied. npm also warned that the `unrs-resolver` install script is not approved under the current allow-scripts policy; no install-script permission was broadened.
- Migration DBs: `fmcg_erp_m20_acceptance` upgraded predecessor `20261020_0010` to `20261021_0010`, verified both MPS diagnostics/snapshot and Developer Portal tables, downgraded to `20261020_0010` (removing the two new developer-key tables), then re-upgraded. `fmcg_erp_m20_full_migrations` upgraded from empty to `20261021_0010` (657 public tables), downgraded to `20261019_0010` and re-upgraded. These were local PostgreSQL runs; they are not remote CI evidence.
- `python -m alembic heads` — one head `20261021_0010`.
- Historical migration wrapper also showed the existing offline `--sql` path stops in `20260516_0060_performance_indexes.py` when its catalog query returns no row; online PostgreSQL migration tests above are the migration evidence.
- GitHub Actions / remote CI: **not run; `DEFERRED_CI_QUOTA` through 2026-10-30**.

## Failed verification attempts and resolutions

- An early `npm run type-check` exposed a nullable abort-signal mismatch and an Axios response-type mismatch in the Developer Portal client. Both were corrected; the final type-check completed with exit code 0.
- Early test-authoring runs of `test_m20_v03_acceptance.py` exposed invalid ORM constructor/relationship use, incorrect fixture-period and diagnostic-history expectations, and detached lazy permission collections. These were corrected without changing product assertions; the focused PostgreSQL file finished **2 passed** and is included in the final 77-test run.
- The full suite initially emitted an unawaited asyncpg cancellation coroutine during teardown. Shallow allocation tracing pointed to asyncpg's cancellation task; the route-level TestClient fixture was then isolated from production lifespan seeding on its private loop. The final suite passed without that warning. A deeper `PYTHONTRACEMALLOC=10` diagnostic was stopped after the backend container reached its 1 GiB memory limit; no test result was claimed from that interrupted run.
- The first Developer Portal browser assertion expected an inline 401 alert. The shared Axios interceptor instead redirects expired sessions to `/login`; the regression now asserts that behavior. The Logs heading accessible-name assertion was also corrected by hiding its decorative icon. The final combined browser run passed 11 tests.
- The first production dependency audit reported five production vulnerabilities. Compatible manifest/lockfile updates removed the production findings; the full audit still reports the nine development-tree findings listed above.
- The final backend command had no failed assertions. The first Docker-hosted frontend type-check attempt exited on Node heap exhaustion; the host retry with `NODE_OPTIONS=--max-old-space-size=4096` passed. An unfiltered lint run failed on generated Playwright trace JavaScript; rerunning while excluding only generated `playwright-report/**` and `test-results/**` passed with zero errors and 67 existing warnings. Early Playwright attempts exposed unavailable container Chromium and a disabled MERGE stage button; the host browser run and type-specific validation fixed these, and the final suite passed. Remaining technical gaps are minimum-run/CIP/currency configuration, additional tenant/company/warehouse permission permutations, nine development-tree dependency findings, `DEFERRED_CI_QUOTA`, and independent audit. Local PostgreSQL was available; no database-unavailability blocker is claimed.

## Source, test, migration, and fixture links

- MPS engine: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/services/mps_engine.py
- MPS demand/material diagnostics: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/services/mps_advanced_service.py
- MPS capacity: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/services/mps_capacity_service.py
- MPS campaigns: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/services/mps_campaign_service.py
- MPS plan/release: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/services/mps_service.py
- MPS scenario engine: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/services/mps_whatif_service.py
- MPS API: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/api/v1/endpoints/mps.py
- MPS/diagnostic/snapshot models: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/models/mps.py
- Diagnostics and immutable scenario migration: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/alembic/versions/20261020_0010_mps_diagnostics_and_scenario_snapshots.py
- Developer Portal API/models: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/api/v1/endpoints/api_portal.py and https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/app/models/api_portal.py
- Developer Portal API-key migration: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/alembic/versions/20261021_0010_developer_portal_api_keys.py
- Recursive engine + boundary regressions: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/tests/test_m20_remaining_engine.py
- PostgreSQL savepoint proof: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/tests/test_m20_postgres_scenario_savepoint.py
- PostgreSQL authorization, transaction, diagnostics, snapshot replay and production release acceptance tests: https://github.com/Sekiph82/fmcg-erp-system/blob/3c5bc31e30131c9acf5de900155b0e68580a061c/backend/tests/test_m20_v03_acceptance.py
- Isolated FastAPI route-test lifespan (prevents cross-loop database seeding/cancellation leakage): https://github.com/Sekiph82/fmcg-erp-system/blob/3c5bc31e30131c9acf5de900155b0e68580a061c/backend/tests/test_m20_s01_t001_v02_mps_remediation.py
- Synthetic acceptance fixture: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/tests/fixtures/m20_acceptance_dataset.json
- Invariant matrix: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/tests/fixtures/m20_invariant_matrix.json
- MPS frontend types/API: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/lib/mps.ts
- MPS dashboard: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/mps/page.tsx
- MPS what-if comparison: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/mps/whatif/page.tsx
- MPS constraints screen: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/mps/constraints/page.tsx
- Responsive dashboard E2E: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/e2e/m20-responsive-dashboard.spec.ts
- Developer Portal error/retry E2E: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/e2e/developer-portal-errors.spec.ts
- Strict M20 PostgreSQL finding regressions: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/tests/test_m20_strict_findings.py
- Concurrent MPS release sequence teardown regression: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/backend/tests/test_m20_s01_t001_v03_mps_remediation.py
- Developer Portal auth/routes/responsive/error E2E: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/e2e/m20-developer-portal-auth.spec.ts
- Developer Portal error/retry E2E (401 now follows shared sign-in redirect): https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/e2e/developer-portal-errors.spec.ts
- Developer Portal API client: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/lib/api_portal_api.ts
- Developer Portal dashboard, API-key and GraphQL pages: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/developer/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/developer/keys/page.tsx, and https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/developer/graphql/page.tsx
- Dashboard shell: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/components/DashboardShell.tsx
- Integration overview and tabs: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/integrations/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/integrations/mpesa/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/integrations/sync/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/integrations/barcode/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/integrations/logs/page.tsx, https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/webhooks/page.tsx, and https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/src/app/dashboard/developer/page.tsx
- Frontend dependency versions: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/package.json
- Frontend compatible dependency and security lockfile updates: https://github.com/Sekiph82/fmcg-erp-system/blob/4c1d5dd8578713e25166eb1e9e46c2ff3722e278/frontend/package-lock.json



## Audit V04 remediation delta and final evidence (2026-10-21)

The V04 code commit is based on exact `origin/main` SHA `961a3dded321ea60a64941b99ab2b366c6e271e3`. It changes MPS what-if behavior, associated regression tests and browser evidence capture. The canonical tracker, task history, independent audit/criteria files and workflow files remain unchanged.

**Scenario behavior implemented for configured inputs:** MERGE requires two distinct unlocked lines in the same plan with matching product, period, schedule dates and work center; it sums planned/demand quantities and removes the consumed line from candidate capacity/changeover. SPLIT requires exactly two positive finite quantities at no more than three decimal places and exact sum equality; candidate capacity/changeover sees two parts. SHIFT_ADD requires finite-capacity mode, a scheduled unlocked target line with a work center, an in-range ISO date and 0 < hours <= 24; it adds capacity to that work center/date. The assumptions and candidate results persist in the immutable scenario snapshot; the live plan is unchanged.

**PostgreSQL operation result:** seeded 40 kg and 60 kg same-product lines with 8 available hours and 10 kg/hour. MERGE snapshot = 100 kg; SPLIT = 15.125 + 24.875 kg plus untouched 60 kg (100 kg total); merge/split candidate overload = 2 hours; SHIFT_ADD of 2 hours reduced overload to 0; snapshot records the added date/work center/hours; live MPS lines still total 100 kg. This is implementation proof with synthetic inputs, not factory master-data acceptance.

**Actions gate:** `.github/workflows/ci.yml` is the only workflow and declares only `push` and `pull_request`; there are no `pull_request_target`, `workflow_dispatch`, schedule or other workflow triggers. Both commits contain `[skip ci]`. GitHub documents those markers as suppressing `push`/`pull_request` runs: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs. No remote CI was dispatched; `DEFERRED_CI_QUOTA` applies through 2026-10-30.

### New source and test URLs

- Scenario service: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/backend/app/services/mps_whatif_service.py
- PostgreSQL merge/split/shift and snapshot test: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/backend/tests/test_m20_v03_acceptance.py
- Unit-level exact split and capacity arithmetic: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/backend/tests/test_m20_remaining_engine.py
- Scenario UI controls: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/frontend/src/app/dashboard/mps/whatif/page.tsx
- Scenario browser contract: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/frontend/e2e/m20-scenario-operations.spec.ts
- Responsive dashboard/integrations browser evidence: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/frontend/e2e/m20-responsive-dashboard.spec.ts
- Developer Portal safe error regressions: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/frontend/e2e/developer-portal-errors.spec.ts
- Developer Portal 401, API Keys/GraphQL and screenshots: https://github.com/Sekiph82/fmcg-erp-system/blob/402f699e1e2e4cd8e04a9106157f012a4f21780c/frontend/e2e/m20-developer-portal-auth.spec.ts

### Screenshot and trace files

All evidence is under `coordination/milestones/M20/evidence/v04/`. Screenshot pairs cover dashboard and integrations at 1536x960, 1920x1080, 1366x768, 768x1024 and 390x844. Additional images cover Developer Portal overview, API Keys and GraphQL at desktop/phone sizes, safe 404 and 401 recovery. Four traces cover responsive UI, scenario operations, Developer Portal 404 and 401. Text traces were scrubbed for credentials, authorization/cookie fields and emails and passed the recorded scans before publication.

- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-dashboard-1536x960.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-dashboard-1920x1080.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-dashboard-1366x768.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-dashboard-768x1024.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-dashboard-390x844.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-integrations-1536x960.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-integrations-1920x1080.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-integrations-1366x768.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-integrations-768x1024.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-integrations-390x844.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-overview.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-api-keys-1536x960.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-api-keys-390x844.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-graphql-1536x960.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-graphql-390x844.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-safe-error-404.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-401-recovery.png
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-responsive-dashboard-trace.zip
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-scenario-operations-trace.zip
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-404-trace.zip
- https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/evidence/v04/m20-developer-portal-401-trace.zip

## Remaining blockers

1. Independent visual review remains pending. Browser screenshots and sanitized Playwright traces are published for independent inspection; independent visual audit acceptance is still pending.
2. No authoritative minimum-run, CIP-duration or approved-currency basis was present. Those outputs stay unknown and are `OWNER_DATA_REQUIRED`. MERGE, exact SPLIT and SHIFT_ADD are implemented and tested for configured cases; broader master-data and tenant permutations remain open.
3. Full tenant permutations beyond the executed two-company/warehouse/actor route matrix remain unverified. The PostgreSQL matrix actually run is linked above.
4. Remote CI remains `DEFERRED_CI_QUOTA` through 2026-10-30; no Actions run was started. Full npm audit still has 9 development-tree findings (7 high, 2 moderate).
5. Independent ChatGPT milestone audit remains pending. No local PostgreSQL availability blocker remains for the executed cases. `TASKS.md`, `TASKS_HISTORY.md` and ChatGPT audit files were not modified.

Milestone disposition: **AWAITING_CHATGPT_MILESTONE_AUDIT**. This report does not self-accept M20 or mark any task newly accepted.
