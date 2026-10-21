# M20 STRICT INDEPENDENT RE-AUDIT V04 — 2026-10-21

**Verdict: PARTIAL_ACCEPTANCE / CHANGES_REQUIRED. M20 remains OPEN.**

Reviewed the current published consolidated execution report at https://github.com/Sekiph82/fmcg-erp-system/blob/4b5d4b3d3864ac7172eb8b3fc15a9b826d762a7a/coordination/milestones/M20/CODEX_M20_FINAL_EXECUTION_LOG_V03.md and implementation diff https://github.com/Sekiph82/fmcg-erp-system/commit/3c5bc31e30131c9acf5de900155b0e68580a061c. Compared against prior https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V03.md.

## Independently inspected
- New 518-line PostgreSQL test file backend/tests/test_m20_v03_acceptance.py contains a seeded, committed MRP→MPS→approved BOM/material stock→durable diagnostics→what-if snapshot/comparison→approve/release production-order→cross-session replay sequence, with rollback and duplicate snapshot constraint assertions.
- A separate test exercises real FastAPI release route with PostgreSQL company/warehouse/permission scope and atomic rollback; this is stronger evidence than previous mocked scope tests.
- The route test fixture now replaces production lifespan with a bounded test lifespan and restores the original in finally, addressing cross-event-loop startup seeding. This is a plausible targeted fix for the asyncpg cancellation warning, but is not independent reproduction.
- Builder reports 77 PostgreSQL/local M20 tests passed in 28.97 s, 11 browser tests passed, frontend typecheck/build passed, lint 0 errors/67 warnings, 69 deprecations, and no remaining asyncpg teardown warning. These results were NOT independently executed by ChatGPT. Remote CI DEFERRED_CI_QUOTA through October 30, 2026.

## Findings
- F01 / F04 / F06: **IMPROVED / BOUNDED BUILDER EVIDENCE**. A meaningful positive and negative PostgreSQL scope/release matrix and committed diagnostics/snapshot replay are now covered. Not every tenant/warehouse/permission permutation or concurrency boundary is tested.
- F02 / F12: **IMPROVED / BOUNDED BUILDER EVIDENCE**. Nested BOM and shortage-vs-unknown semantics are supported by PostgreSQL test source; full factory master-data acceptance not claimed.
- F03 / F07: **OPEN FUNCTIONAL/CONFIGURATION GATE**. Scenario MERGE and SHIFT_ADD are unsupported, SPLIT is approximate. Minimum-run, CIP duration and approved-currency cost policy have no authoritative master data. Unknown results are appropriate, but required scenario behavior remains incomplete.
- F05 / UI-01 / UI-02 / F13: **BUILDER PASS, INDEPENDENT VISUAL EVIDENCE PENDING**. 11 Playwright tests are reported, but screenshots/traces are not published for independent review. Next 16 cross-app regressions beyond reported suite remain unverified.
- F10 / teardown: **IMPROVED**. 77 tests reportedly pass without asyncpg cancellation warning after test-lifespan isolation; remaining 69 deprecation warnings and 9 development dependency findings are tracked.
- F08: **NOT CLOSED**. M20.S04.T004 and M20.S05.T004 cannot be marked done. No factory data may be fabricated, and no unsupported scenario operation may be called PASS.

## Task status
Historical bounded acceptance: S01.T001 and S01.T002 retained.
Implementation and builder-backed test evidence substantially improved for S01.T003, S02.T001–T004, S03.T001–T004, S04.T001–T003, S05.T001–T003; do not conflate implementation with full milestone acceptance.
S01.T004 synthetic acceptance fixtures are not authoritative factory data.
S04.T004 PARTIAL; S05.T002 independently unverified visual output; S05.T004 OPEN.
Other remaining supply/tenant permutations and authoritative minimum-run/CIP/currency data are explicit acceptance limitations.

## Next actions
1. Continue a single bounded M20 remediation effort for feasible code gaps, especially scenario operations MERGE/SHIFT_ADD/exact SPLIT, and add positive/negative tests or explicit supported-operation contracts; never fabricate policy data.
2. Publish sanitized Playwright screenshots and traces, exact-SHA backend and migration receipts, and comprehensive cross-module/tenant/warehouse matrix.
3. Keep unavailable factory policies in an explicit OWNER_DATA_REQUIRED gate rather than forcing fake values. Identify exact required configuration fields.
4. Maintain no GitHub Actions/remote CI through 2026-10-30 and beyond absent authorization. Codex must not change TASKS.md or ChatGPT audit files.
5. Request another independent ChatGPT audit only when new evidence or implementation addresses remaining acceptance gates.

**M20 NOT CLOSED.**
