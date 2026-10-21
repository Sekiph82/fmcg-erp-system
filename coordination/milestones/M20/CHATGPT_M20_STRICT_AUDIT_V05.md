# M20 STRICT AUDIT V05 — 2026-10-21

**VERDICT: PARTIAL / CHANGES_REQUIRED. M20 NOT CLOSED.**

Evidence reviewed: current https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CODEX_M20_FINAL_EXECUTION_LOG_V03.md ; implementation https://github.com/Sekiph82/fmcg-erp-system/commit/402f699e1e2e4cd8e04a9106157f012a4f21780c ; criteria https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md .

**Method and limits:** Independently fetched the builder log, the implementation commit diff, the current scenario service and frontend Playwright scenario test source. **Did not independently run PostgreSQL, pytest, Playwright, npm build or open the 17 screenshots / four traces.** Their existence is supported by explicit repository paths in the report, but their visual content is not independently accepted. Builder reports 77 backend and 12 browser passes, typecheck/build 699/699, lint 0 errors/67 warnings, 69 deprecations, production audit 0 and full development audit 9. These are builder-reported executions, not independent reruns.

## Improvements
- S04.T004 now has MERGE for schedule-equivalent lines, exact two-part SPLIT and SHIFT_ADD scenario capacity resimulation. The diff includes validation, persisted assumptions and candidate-only expansion. Builder reports PostgreSQL regression for quantity conservation, overload reduction and live-plan isolation. This is material progress from V04.
- Published evidence directory lists 17 responsive/Developer Portal PNG screenshots and four sanitized traces. UI-01/UI-02 are **BUILDER_PASS / INDEPENDENT_VISUAL_PENDING**, no longer evidence-absent.
- Previous seeded cross-module PostgreSQL, permission/release and immutable snapshot tests remain in source. No unraisable asyncpg warning is reported in the latest 77-test run.

## New targeted code-review findings requiring reproduction
**V05-F14 P1: Aggregate SHIFT_ADD daily-hour bound is not enforced.** backend/app/services/mps_whatif_service.py validates each SHIFT_ADD hours >0 and <=24 at lines ~508–527, then sums multiple additions by (work_center_id, date) without checking aggregate available hours, overlapping shifts, calendar, labor policy, or downtime. _scenario_capacity_loads at ~115–123 simply adds the sum to daily calendar availability, potentially crediting physically impossible hours. Reproduce two additions to same WC/day and calendar already at 24h; reject invalid totals or use configured actual shift/calendar constraints. Preserve UNKNOWN if no policy data.

**V05-F15 P1: MERGE/SPLIT scope and conservation edge cases.** MERGE matching checks product, period, schedule dates and WC but not explicitly warehouse, source allocation, recipe/BOM/version, capacity eligibility or line constraints. Verify model scope and whether these attributes exist; test cross-warehouse or incompatible recipe if representable, chained operations, same line multiple changes, lock handling, precision and source-line exclusion. SPLIT enforces exactly two parts, not arbitrary N; ensure UI and documented contract agree. Do not assert an exploit without a real reproduction.

**V05-F16 P1: Scenario UI E2E is mocked for the MPS API.** frontend/e2e/m20-scenario-operations.spec.ts intercepts **/api/v1/mps/** and responds with synthetic plans/lines/scenario JSON, asserting serialized POST payloads. This is a valid frontend contract test, but **not real backend round-trip evidence**. Pair it with an actual PostgreSQL-backed browser/API integration scenario and validate rendered KPI values after reload.

## Open acceptance gates
- Missing authoritative minimum-run, CIP durations and approved-currency cost policy: **OWNER_DATA_REQUIRED**. Never fabricate data; clearly document exact fields and fallback semantics.
- Full tenant/company/warehouse permission and concurrency permutations: partially covered; bounded acceptance only.
- UI-01/UI-02 actual screenshot visual quality and sanitized trace review pending; do not infer PASS solely from a screenshot path.
- Development dependency advisories: nine reported; triage and document impact, avoid forced major upgrade without compatibility tests.
- Remote CI: **DEFERRED_CI_QUOTA** through 2026-10-30; no Actions without owner approval.
- Historical T001/T002 bounded PASS retained. M20.S05.T004 remains OPEN.

## Next continuous execution
Remediate and test V05-F14–F16 and remaining feasible boundary/visual evidence. Publish actual artifact content in accessible format and comprehensive redacted exact-SHA receipts; no per-task stopping, no TASKS.md/ChatGPT audit changes by Codex, no CI. Do not repeatedly rerun accepted tasks without regression reason. Report final AWAITING_CHATGPT_MILESTONE_AUDIT.

**M20 remains OPEN / CHANGES_REQUIRED.**
