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
| M20.S05.T003 | **Local PostgreSQL integration PASS with bounded scope.** The 2026-10-23 task-owned database run passed all 16 tests in `backend/tests/test_m20_v03_acceptance.py`, including the release rollback audit assertion, nested BOM material evaluation, demand-to-MPS creation, diagnostics, scenario replay, approval, production release, permission/scope denials and sequence concurrency. A separate PostgreSQL migration round-trip reached `20261022_0011`, downgraded to `20261021_0010` with all three MPS sequences absent, then upgraded and restored them. No factory master data was fabricated. Exact receipt: `evidence/v05/t003-local-20261023/CLOSEOUT.md`. |
| M20.S05.T004 | **Evidence index and risk disposition refreshed 2026-10-23.** The builder task record is complete only when its matrix and evidence index are current; M20 itself remains **OPEN / independent audit pending** because material gates below are unresolved. This report does not self-approve the milestone. |

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

## Strict Audit V05 remediation delta (2026-10-21)

This delta continues the same V01 master prompt from the V05 audit commit `11a17e711963257ed3c5a1ca3a7cc23d2a827e34`. It supersedes only the V05 findings and evidence below; the historical 20-task matrix and earlier receipts above remain context, not a new acceptance. Implementation commit: https://github.com/Sekiph82/fmcg-erp-system/commit/0b5033e28c12f7f2f202102496bb5c51d50723f4 . Earlier M20 implementation commit: https://github.com/Sekiph82/fmcg-erp-system/commit/402f699e1e2e4cd8e04a9106157f012a4f21780c .

### V05 finding status and bounded task matrix

| Gate / task | Current implementation and actual evidence | Builder disposition |
|---|---|---|
| V05-F14; M20.S04.T004 | Aggregate SHIFT_ADD is grouped by `(work_center_id, date)`, validated against an existing non-holiday/non-maintenance ResourceCalendar and configured, non-overlapping shift windows whose duration matches `available_hours`. Aggregate extra hours cannot exceed the remaining 24-hour day. Missing calendars/windows, malformed/mismatched or overlapping shifts are `PARTIAL_INPUTS`; those hours are not credited. Downtime is deducted before valid extra hours. PostgreSQL test exercises 8 configured hours (08:00–16:00), two additions totaling the remaining 16 hours, and rejection of 17 hours; helper cases cover missing calendar/windows and overlapping shifts. | **LOCAL IMPLEMENTATION + POSTGRESQL BOUNDARY PASS; independent audit pending.** |
| V05-F15; M20.S04.T004 | MERGE now requires matching product, source MRP result, campaign, batch size/count, period, scheduled dates, work center and feasibility, two positive finite quantities, and exact quantity conservation. Split remains an explicit two-part operation with positive values, max three decimals and exact sum; UI help states the same contract. Conflicting/chained structural edits and SHIFT_ADD against consumed lines reject. MPSLine has no line-level warehouse or recipe/BOM/version field; scope remains the parent plan's MRP warehouse/source. No absent attribute or factory policy was fabricated. PostgreSQL cases assert exact 100 kg conservation, reject feasibility mismatch and conflicting operations, and verify the live plan remains unchanged. | **BOUNDED LOCAL IMPLEMENTATION + POSTGRESQL PASS; cross-model data limits and independent audit pending.** |
| V05-F16; M20.S04.T004 / M20.S05.T002 | New Playwright test signs into the isolated backend, obtains a real finite plan/line from PostgreSQL, drives the scenario UI, POSTs an exact split to the real endpoint, reloads from the API and verifies persisted KPIs and scenario details. It asserts HTTP 201 and the actual request payload. | **REAL UI → API → POSTGRESQL ROUND-TRIP PASS; independent audit pending.** |
| M20.S01.T003, S04.T001–T002; strict P0 permission/scope/concurrency | Existing real-PostgreSQL route matrix covers permitted release, wrong target warehouse, wrong-company source plan, actor without release permission and transaction rollback after order flush. A new concurrent same-plan API case verifies two requests produce one release plus one idempotent retry, exactly two orders for two lines and one release audit row. This is bounded evidence, not every tenant permutation. | **BOUNDED POSTGRESQL PASS; broader tenant/company/warehouse combinations remain BLOCKED_EVIDENCE.** |
| M20.S05.T001–T004 | The targeted strict PostgreSQL suite is current and passing. Historical broader M20 suite/migration receipts remain in the earlier matrix. No migration was required for this delta. Cross-module full acceptance, migration proof at this exact V05 SHA, and the independent audit gate remain open. | **PARTIAL / AUDIT OPEN; no self-acceptance.** |

### Exact commands and results for this delta

- PostgreSQL integration suite, run inside task-owned container `m20-v05-backend` against the available PostgreSQL service (test source staged under `/tmp/m20-v05-20261021`): `docker exec -e PYTHONPATH=/tmp/m20-v05-20261021 -w /tmp/m20-v05-20261021 m20-v05-backend pytest -q tests/test_m20_v03_acceptance.py` → **4 passed, 69 warnings in 16.20s**. Warnings are existing SQLAlchemy `noload`, Pydantic v2, and passlib deprecations; no failed assertions. This is actual PostgreSQL evidence, not `BLOCKED_DB_PROOF`.
- Frontend types: `npx tsc --noEmit --incremental false --pretty false --project tsconfig.json` → **exit 0**.
- Changed-file lint: `npx eslint src/app/dashboard/mps/whatif/page.tsx src/lib/mps.ts e2e/m20-scenario-backend-roundtrip.spec.ts` → **exit 0, no diagnostics**.
- Next 16 route-wrapper lint: `$files = git diff-tree --no-commit-id --name-only -r HEAD | Where-Object { $_ -like 'frontend/src/app/*' } | ForEach-Object { $_.Substring('frontend/'.Length) }; npx eslint $files` → **exit 0, no diagnostics**.
- Production build: `$env:NODE_OPTIONS='--max-old-space-size=4096'; npm run build -- --webpack` → **exit 0; 699/699 static pages**. Warnings are listed above; the default Turbopack build did not succeed with the external dependency junction.
- Browser server: `NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev -- --webpack --hostname 0.0.0.0 --port 3001` (PowerShell env assignment used). Playwright command: `E2E_SKIP_WEBSERVER=1 E2E_BASE_URL=http://localhost:3001 M20_BACKEND_URL=http://localhost:8001 M20_EVIDENCE_DIR=../coordination/milestones/M20/evidence/v05 npx playwright test e2e/m20-scenario-backend-roundtrip.spec.ts --project=chromium --no-deps --retries=0 --workers=1 --trace on` → **1 passed in 18.2s**. Browser-observed statuses: plans 200, lines 200, scenario list 200, create 201, reload/list 200. The screenshot is captured after reload with the account email masked.
- Local production build: the default Turbopack build failed to resolve `next/package.json` because this clean clone's `frontend/node_modules` is a junction to the separate owner checkout. `npm run build -- --webpack` first exposed 21 dynamic route wrappers still using synchronous `params`. They were corrected for Next 16 Promise params in commit `2b55a7e2bcfc2f691991a11789a880b0324e3390`. After that fix, `npx tsc --noEmit --incremental false --pretty false --project tsconfig.json` passed and the Webpack production build exited 0, compiled successfully, and generated **699/699** static pages. Build warnings remain: a `process.cwd` Edge Runtime warning and 27 standalone-traced dependency files omitted because the linked `node_modules` target is outside `outputFileTracingRoot`. Thus compilation/prerender passes; a hermetic standalone artifact is not proven by this linked-dependency clone. No dependency installation was run against the junction.
- Remote GitHub Actions/CI: **not triggered; `DEFERRED_CI_QUOTA` remains through 2026-10-30.** The only tracked workflow is `.github/workflows/ci.yml`, with `push` and `pull_request` triggers only. The implementation commit carries `[skip ci]`; GitHub documents that skip marker for these events: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs . No `pull_request_target`, schedule, dispatch or other workflow exists in this checkout.

### Published UI and trace review

- The 17 V04 screenshots plus the new V05 screenshot (18 total) were checked for file integrity/dimensions and visually reviewed. The set covers dashboard/integrations at 1366×768, 1536×960, 1920×1080, 768×1024 and 390×844, Developer Portal desktop/phone/error states, and the new scenario round trip. Representative full-resolution review found the main work area using the available width beside the persistent sidebar and no obvious clipping/overlap in the captured views. This is builder review only; independent visual acceptance remains pending.
- All four V04 Playwright trace ZIPs passed `ZipFile.testzip()` with no corrupt members (92, 130, 952 and 139 entries). Structured trace/network records point to the expected local app/API hosts `localhost:3000` and `localhost:8000`; scanned records contained no email, cookie, authorization-token, refresh-token or API-key fields/values. Existing V04 trace URLs remain listed above. A V05 trace was not added because the real round-trip trace contains an authenticated session; its redacted screenshot and exact test result are published instead.
- New source/test/evidence links pinned to implementation SHA `0b5033e28c12f7f2f202102496bb5c51d50723f4`:
  - Scenario capacity/calendar/merge/split service: https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/backend/app/services/mps_whatif_service.py
  - PostgreSQL scope, calendar, operation, permission, rollback and concurrency tests: https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/backend/tests/test_m20_v03_acceptance.py
  - Real MPS route ORM eager loading and auth transaction fix: https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/backend/app/services/mps_service.py and https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/backend/app/core/deps.py
  - Scenario UI and API response typing: https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/frontend/src/app/dashboard/mps/whatif/page.tsx and https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/frontend/src/lib/mps.ts
  - Actual backend browser integration: https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/frontend/e2e/m20-scenario-backend-roundtrip.spec.ts
  - Redacted screenshot after real save/reload: https://github.com/Sekiph82/fmcg-erp-system/blob/0b5033e28c12f7f2f202102496bb5c51d50723f4/coordination/milestones/M20/evidence/v05/m20-scenario-backend-roundtrip.png
- Next.js 16 Promise-params fix commit: https://github.com/Sekiph82/fmcg-erp-system/commit/2b55a7e2bcfc2f691991a11789a880b0324e3390 . All 21 changed route wrappers (async `redirect()` wrappers except the client payroll route, which unwraps `params` with React `use`) are linked at this exact SHA:
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/expenses/claims/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/fixed-assets/assets/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/fixed-assets/assets/%5Bid%5D/add-component/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/marketing/crm/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/marketing/ecommerce/performance/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/marketing/ecommerce/products/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/marketing/ecommerce/stores/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/marketing/surveys/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/payroll/runs/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/portal/accounts/%5Bid%5D/view/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/procurement/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/production-execution/%5Bid%5D/genealogy/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/production/plans/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/promotions/schemes/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/putaway/execute/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/recruitment/candidates/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/recruitment/requisitions/%5Bid%5D/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/supplier-portal/accounts/%5Bid%5D/purchase-orders/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/surveys/%5Bid%5D/respond/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/surveys/%5Bid%5D/results/page.tsx
  - https://github.com/Sekiph82/fmcg-erp-system/blob/2b55a7e2bcfc2f691991a11789a880b0324e3390/frontend/src/app/dashboard/wms/counts/%5Bid%5D/page.tsx

### Remaining blockers and disposition

1. Minimum-run quantity, CIP durations and approved currency/cost basis are unavailable in authoritative factory master data. They remain **OWNER_DATA_REQUIRED**; related outputs remain unknown/`PARTIAL_INPUTS` and no values were invented.
2. The PostgreSQL tenant/warehouse/permission/concurrency cases above are bounded; every tenant/company/warehouse permutation and all possible race schedules are not proven. Cross-module and full migration upgrade/downgrade acceptance at this exact V05 implementation SHA remain open strict-audit evidence gates.
3. Next 16 source type-check and Webpack build pass after fixing 21 dynamic-route Promise-params errors; standalone tracing still omits 27 files outside the checkout root because this clone uses an external dependency junction. The default Turbopack attempt still cannot resolve `next/package.json` through that junction. Nine development-tree dependency advisories remain as reported in the prior audit; no forced major dependency migration was made.
4. Remote CI remains **DEFERRED_CI_QUOTA** through 2026-10-30. No PostgreSQL availability blocker applies to the executed tests. No workflow was dispatched.
5. UI screenshot/trace review is builder evidence only. V05-F14/F15/F16 are not independent acceptance, and `M20.S05.T004` remains **OPEN** pending ChatGPT audit. `TASKS.md`, `TASKS_HISTORY.md`, and all ChatGPT audit files remain untouched.

Milestone handoff remains **AWAITING_CHATGPT_MILESTONE_AUDIT**. This log does not self-approve M20 or change prior task acceptance.

## Final continuation — auth transaction boundary and verification (2026-10-21)

This continuation starts from published `main` SHA `84de146217309f76090ab6f3fc6351b383f50cdc`, matching `origin/main`. The dirty sibling owner checkout was left untouched. Implementation commit: https://github.com/Sekiph82/fmcg-erp-system/commit/5cfe87a82cc1078d54e52bb4d5af6fb9c0a3de94 .

### Authentication transaction finding and correction

`get_current_user()` previously committed the shared `get_db()` session after loading the authenticated user and eager permission/scope relationships. This could commit pending writes made by an earlier dependency, and it hid SQLAlchemy autobegin state so MPS handlers could enter `db.begin()` only because auth had committed the request session. The behavior was global and could change transaction semantics in unrelated APIs.

The fix removes that commit and gives authentication its own `get_auth_db()` session. The business endpoint retains the request's original `get_db()` session and owns its commit/rollback boundary. The existing `get_db` import through `app.core.deps` remains available to current routers. Authentication token validation, active-user checks, eager role/permission/scope loading and permission enforcement are unchanged.

New PostgreSQL test: https://github.com/Sekiph82/fmcg-erp-system/blob/5cfe87a82cc1078d54e52bb4d5af6fb9c0a3de94/backend/tests/test_m20_auth_transaction_boundary.py . It proves an explicit transaction can run in the actual MPS plans handler; an unrelated warehouses read remains usable; a user without MPS permission receives 403; an invalid token receives 401; and a write staged by an earlier dependency is not committed by authentication when the endpoint fails. Both test users are deleted on the successful test path.

Exact local PostgreSQL commands (current clean source staged in task-owned `/tmp/m20-auth-boundary-84de146` inside the existing backend test container):

```text
docker exec -e PYTHONPATH=/tmp/m20-auth-boundary-84de146 -w /tmp/m20-auth-boundary-84de146 fmcg-erp-system-backend-1 python -m py_compile app/core/deps.py app/db/session.py tests/test_m20_auth_transaction_boundary.py
docker exec -e PYTHONPATH=/tmp/m20-auth-boundary-84de146 -w /tmp/m20-auth-boundary-84de146 fmcg-erp-system-backend-1 pytest -q -W always::pytest.PytestUnraisableExceptionWarning tests/test_m20_strict_findings.py tests/test_m20_remaining_engine.py tests/test_m20_postgres_scenario_savepoint.py tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_s01_t002_mps_preservation.py tests/test_m20_v03_acceptance.py tests/test_m20_auth_transaction_boundary.py --tb=short
```

Results: py_compile **exit 0**; complete current M20 regression set **79 passed, 71 warnings in 22.11s**. Warnings are existing SQLAlchemy/Pydantic/passlib/httpx deprecations; no `PytestUnraisableExceptionWarning` or failed assertion occurred. This 79-test result supersedes the earlier 77-test count and includes the newly added auth-boundary regression. An initial incomplete staging run reported 22 setup failures because the temporary runner lacked `pytest.ini`, fixture JSON and the frontend MPS source referenced by historical tests; after copying those tracked inputs, the complete rerun passed. This does not expand the seeded tenant/company/warehouse matrix beyond the cases described in the earlier evidence.

### Next.js 16 standalone package and dynamic-route verification

To avoid the owner-linked dependency junction, frontend source was archived from this clean checkout into a unique `%TEMP%` directory and dependencies were installed there with `npm ci --no-audit --no-fund`. The linked `frontend/node_modules` was not modified. npm reported its existing install-script approval gate for `unrs-resolver`; no script approval policy was widened. `npm run build` in the isolated frontend succeeded on Next.js 16.4.2: compile and TypeScript passed and static generation completed **699/699** pages. Turbopack logged a temporary-parent lockfile discovery warning; it did not fail the build.

The standalone package was completed by copying the build's `.next/static/` and `public/` assets into `.next/standalone/`, as required by Next.js standalone deployment. Verification found `server.js`, the packaged Next runtime, package metadata and build manifests. A local trace audit read **764** `.nft.json` manifests and **115,428** traced file entries: **0 missing files, 0 paths outside the isolated project root**. The packaged `node server.js` process started on `127.0.0.1:3187`. A browser smoke pass exercised the 21 updated dynamic routes: all returned HTTP 200 without browser `pageerror`; intended legacy route wrappers redirected to their workspace routes, and the procurement detail remained on its parameterized route. A separate no-cookie pass sent all 21 routes to `/login`. In the rendered-route pass, authentication was a controlled synthetic browser fixture and non-auth API calls were stubbed to HTTP 503; this verifies route wrapper/runtime behavior, not production authorization or backend data.

### Playwright suite status

`npx playwright test --list` in the isolated frontend discovered **596 tests across 27 files**. The first 12-test M20 invocation used `--no-deps` and stopped before test bodies because the required storage-state file had not been created. The corrected invocation enabled the configured auth setup; it attempted 13 tests (setup plus 12 M20 tests), but setup was blocked because the local backend rejected the suite's documented default `admin` / `Admin1234!` credential as invalid. The 12 dependent browser tests did not run in this continuation. No owner credential was changed or read. Earlier successful M20 browser receipts remain recorded above, including the 12-test pass and real scenario UI-to-PostgreSQL round trip; this continuation does not claim a fresh full Playwright pass. The 596-test suite remains **BLOCKED_EVIDENCE: valid local E2E account is unavailable**.

### Current dependency advisory review

Fresh isolated `npm audit --json` reports **9 development-tree affected packages: 7 high and 2 moderate**; `npm audit --omit=dev --audit-level=moderate` reports **0 production vulnerabilities**. Affected development packages are `@next/eslint-plugin-next`, `braces`, `chokidar`, `eslint-config-next`, `fast-glob`, `micromatch`, `postcss-nested`, `postcss-selector-parser`, and `tailwindcss`. npm's suggested `tailwindcss@4.3.3` is a major migration; it requires reviewing Tailwind config, PostCSS integration, plugins and visual/browser coverage before adoption. npm's suggested `eslint-config-next@14.2.35` would downgrade the lint config across the app's Next 16 major and is not a safe automatic fix. Safe options are to wait for a Next-16-compatible patched lint-config chain or update compatible transitive package ranges in a lockfile-only change after `npm explain`/audit verification; treat the independent moderate `postcss-nested` fix as a separately reviewed lockfile update. No forced or major dependency migration was applied.

### Final gates and disposition

- V05-F14/F15/F16 implementation and evidence remain as recorded in the V05 delta; this continuation did not alter scenario calculations or claim a new UI-to-PostgreSQL scenario run.
- `OWNER_DATA_REQUIRED` remains for minimum-run quantities, CIP durations and approved currency/cost basis. No factory configuration was fabricated.
- Remote CI remains **DEFERRED_CI_QUOTA** through 2026-10-30 inclusive. The sole workflow is push/pull_request only; the implementation commit includes `[skip ci]`. No workflow was dispatched or rerun.
- Independent ChatGPT acceptance remains pending. Expanded tenant permutations, the 596-test Playwright run, development-only advisories and owner-provided data remain open. `TASKS.md`, `TASKS_HISTORY.md` and ChatGPT audit files were not modified.

Final handoff: **AWAITING_CHATGPT_MILESTONE_AUDIT**. This evidence report does not self-approve M20.

## M20.S05.T004 evidence refresh (2026-10-23)

This update is scoped to the evidence-index and closeout preparation required by M20.S05.T004. It incorporates the task-owned T003 PostgreSQL receipt at `evidence/v05/t003-local-20261023/CLOSEOUT.md` and the T002 frontend and real scenario round-trip receipt at `evidence/v05/t002-local-20261023/CLOSEOUT.md`. The full 20-row implementation/evidence matrix above remains the coverage matrix; T003 and T004 rows have been refreshed to the current local execution record. No historical acceptance is extended by this update.

### V05 finding reconciliation

- **F14 — aggregate SHIFT_ADD bound:** implementation and boundary evidence are in commit `0b5033e28c12f7f2f202102496bb5c51d50723f4`, after the 2026-10-21 16:37 +03:00 V05 audit. The validator aggregates by work center/date, requires a consistent calendar with non-overlapping configured windows, refuses additions beyond the remaining 24-hour day, and leaves unconfigured or downtime-ambiguous capacity uncredited. The PostgreSQL suite covers additions totaling the 16-hour remainder of an 8-hour calendar and rejects 17 hours. The T004 rerun adds the audit's specific two-addition/full-day case.
- **F15 — MERGE/SPLIT boundaries:** commit `0b5033e28c12f7f2f202102496bb5c51d50723f4` requires matching MRP source, product, campaign, batch, priority, feasibility, period, schedule and work center for merges; split quantities remain two positive finite values with at most three decimals and exact sum conservation. The T004 PostgreSQL rerun adds explicit source-MRP mismatch, chained-merge and locked-source rejection. `MPSLine` contains no line-level warehouse or recipe/BOM-version field; lines are plan-scoped and the parent plan is linked to one MRP run/warehouse. Those absent fields are recorded as model limits, not fabricated safeguards.
- **F16 — real browser persistence:** T002's local receipt records a real browser login, split POST, reload and persisted KPI/detail checks. The runner must start the API with the exact disposable `DATABASE_URL`; the browser test itself can verify loopback URL and the matching database-name opt-in, but cannot introspect an already-running backend's connection. This remains runner-side evidence for independent confirmation, not an auditor PASS.

### Current evidence index

- `evidence/v05/t002-local-20261023/CLOSEOUT.md` and its redacted screenshot: T002 type-check, build, 12 view tests and one real scenario browser/API round trip.
- `evidence/v05/t003-local-20261023/CLOSEOUT.md`: T003 PostgreSQL test and migration-round-trip results.
- `backend/tests/test_m20_v03_acceptance.py`: current disposable-PostgreSQL integration suite and targeted boundary assertions.
- `frontend/e2e/m20-scenario-backend-roundtrip.spec.ts`: real browser-to-API scenario persistence test.
- `evidence/v04/`: 17 responsive/Developer Portal screenshots and four sanitized traces listed in the earlier matrix. Their visual and trace acceptance remains independent-auditor work.
- `CHATGPT_M20_STRICT_AUDIT_V05.md` and `CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md`: current independent verdict and mandatory acceptance rules.
- Implementation pins: historical V03 work `402f699e1e2e4cd8e04a9106157f012a4f21780c`; V05 remediation `0b5033e28c12f7f2f202102496bb5c51d50723f4`; T002 `f9db28333d97b954ea171993aa7a8777047cd110`; T003 `c4ec24ba24396acfe3fb1a2ff8bc2b303f7a9b96`; T004 evidence/test/tracker closeout `763cf2935868852d1725d8c51051ee1a734a47a3`.

### Open risks and objective exit criteria

M20 remains **OPEN / PARTIAL**. The V05 independent verdict is `PARTIAL / CHANGES_REQUIRED`; this builder update does not supersede it. Open gates are: synthetic minimum-run, CIP, and currency assumptions are now owner-authorized and represented in the virtual acceptance fixture; broader tenant/company/warehouse and concurrency permutations; independent review of UI-01/UI-02 screenshots and sanitized traces; independent recheck of F14–F16 at the current evidence pins; nine development-tree dependency advisories; and remote CI deferred through 2026-10-30. The broader 596-test Playwright suite also remains blocked by the unavailable valid local E2E account as recorded in the preceding continuation. Synthetic values and accounts are test-only and are not live factory data; no audit approval was invented, and no GitHub Actions were run.

M20 can be marked accepted only after the independent auditor assigns PASS to every mandatory gate in `CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md`, confirms exact-SHA behavioral evidence for the integrated paths, and finds no blocking P0/P1 issue. Remote CI deferral is separate from local PostgreSQL proof and does not by itself substitute for any local gate. The owner authorized Codex to update task status; tracker completion of T004 evidence preparation is not M20 milestone acceptance.

## Virtual-factory assumptions and PostgreSQL recheck (2026-10-28)

The owner answered `Q-M21-S05-T004-M20-DATA`: because no physical factory or employees exist, Codex is authorized to create realistic, explicitly synthetic virtual-factory assumptions for M20 demo and integration acceptance. The former `OWNER_DATA_REQUIRED` gate for minimum runs, CIP, cost currency and test users is superseded for this bounded virtual acceptance; it is not a claim about live operations. The committed-code candidate in this checkout now includes a clearly labeled test-only Nairobi FMCG fixture (KES base currency, product minimum runs and standard-cost currencies, FILL-01 shift and changeover/CIP inputs, and demo planner/quality/admin users). Runtime behavior consumes configured minimum run quantities, configured transition CIP capacity, and only comparable configured standard costs; missing, invalid, mixed-currency, or ambiguous assumptions remain unknown instead of being guessed.

The migration `20261028_0023` passed fresh disposable PostgreSQL upgrade, downgrade to `20261028_0022`, re-upgrade to head, and `alembic current` at `20261028_0023`. The task-owned disposable PostgreSQL regression run passed **100 tests** across the M20 strict findings, MPS engine, migration/savepoint, release, acceptance and auth transaction-boundary suites. Its task-labeled disposable container was removed after the run. Frontend `npm run type-check` passed in the same work session; `git diff --check` and final queue-state validation are still to be recorded after this log update.

These values and accounts are test fixtures, not actual employees, site configuration, approved business policy or live cost master data. This execution does not change the independent M20 strict-audit verdict or close M20/M21. Remaining audit-only gates must be assessed against the updated implementation and evidence; no ChatGPT audit was edited and no GitHub Actions were run.

### Final verification recorded (2026-10-28)

The checks mentioned as pending in the preceding subsection have now completed: `git diff --check` passed (Git emitted only line-ending normalization warnings); `py_compile` passed for the changed backend modules/tests; frontend `npm run type-check` passed; `node scripts/codex/validate-task-state.mjs` passed; and `node scripts/codex/task-queue.mjs --check` confirmed the exact current task remains `M21.S05.T004` / `BLOCKED` with no explicit successor. `task-queue.mjs --apply-answers` reported no additional unanswered exact matches. No task status was promoted, no successor was guessed, and no remote Actions were run.

### Superseding verification after read-only review (2026-10-28)

A fresh read-only reviewer found that scenario summaries were still labelled `KES` regardless of company base currency. This was corrected by persisting nullable `impact_cost_currency` on each scenario, exposing it through `MPSWhatIfOut`, and rendering the stored currency in list/detail UI only when a valid cost basis exists. Migration `20261028_0024` passed upgrade → downgrade to `20261028_0023` → re-upgrade on fresh task-owned PostgreSQL. The HTTP integration test now asserts KES on create/list/detail and compares a 12.5 KES scenario delta; no-currency cases remain null/unknown.

The authorized virtual-factory acceptance case now also seeds two synthetic HR employees, operator profiles, FILL-01 shift assignments, and a synthetic filling-machine record whose standard labor requirement is two operators. Cleanup is included and exercised in the PostgreSQL test. This is not real employee data. **MPS capacity still allocates work-center hours and does not constrain individual attendance or qualifications**; the configured line throughput assumes the two-person crew, so the existing M32 labor/qualification constraint is not claimed as implemented.

After these corrections, the same bounded M20 regression suite again passed **100 tests** on disposable PostgreSQL, with 70 existing deprecation warnings. Migration upgrade/downgrade/re-upgrade completed at `20261028_0024`; task-labeled container cleanup succeeded. `npm run type-check`, backend `py_compile`, and `git diff --check` passed. The earlier 97-pass/3-failure run was an intermediate test-fixture cleanup mistake, corrected before this successful rerun. Independent M20 strict acceptance and visual/trace audit are still required; this report does not change V05 or close M20.

### Superseding F14 remediation receipt (2026-10-29)

The V05-F14 review correctly noted that date-plus-hours alone did not prove an added shift existed. `SHIFT_ADD` now requires an explicit start/end interval whose duration matches the submitted hours, rejects overlap with configured calendar windows or other added intervals, enforces the aggregate daily-hour limit, and leaves additions uncredited when the calendar is missing/inconsistent or downtime overlap cannot be resolved without a work-center timezone. The frontend collects and displays the interval duration. Unit and PostgreSQL acceptance tests exercise valid intervals, aggregate overflow, overlap boundaries, full-day calendars, and unresolved downtime.

Fresh isolated PostgreSQL receipt: `evidence/v06/t004-20261029-f14/CLOSEOUT.md`. A follow-up found and fixed adjacent-UTC-day downtime uncertainty; the currency database constraints now require three uppercase ASCII letters via migration `20261029_0025`. On a new task-labeled container/database, the full bounded M20 suite passed **100 tests, 73 warnings** in 50.39 seconds. Alembic upgraded to head, downgraded to `20261028_0024`, upgraded again, and reported `20261029_0025 (head)`. The exact disposable container/database identifiers and cleanup confirmation are in the receipt; no password was used or recorded. Frontend `npm run type-check` and production build passed; the focused mocked scenario UI suite passed 3/3; backend `py_compile` and `git diff --check` passed. The UI tests cover request serialization only, not the real API/database browser round trip. This does not establish M20 acceptance or independent visual/trace approval. The M20 V05 audit remains `OPEN / CHANGES_REQUIRED` pending a fresh independent review of the current implementation and the other listed acceptance gates. No GitHub Actions were run.
