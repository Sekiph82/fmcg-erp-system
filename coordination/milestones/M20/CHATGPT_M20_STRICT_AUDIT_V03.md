# M20 INDEPENDENT STRICT RE-AUDIT V03 — 2026-10-21

**Verdict: FAIL / CHANGES_REQUIRED. M20 is NOT accepted.**
Baseline criteria: coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md.
Builder evidence: coordination/milestones/M20/CODEX_M20_FINAL_EXECUTION_LOG_V03.md at report commit fd288fe39dd71e36cba8ccf254aae576e4dac2ec.
Implementation: https://github.com/Sekiph82/fmcg-erp-system/commit/4c1d5dd8578713e25166eb1e9e46c2ff3722e278
Previous independent audit: coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V02.md.

## Independent inspection vs builder execution
Independently fetched current report, TASKS.md and 4c1d5dd source diff. No ChatGPT-run PostgreSQL, pytest, Playwright, build or dependency audit. Builder reports 75 backend tests, 11 browser tests, frontend typecheck/build, 699/699 static pages, production npm audit zero findings, nine dev-tree findings, 67 lint warnings. **These are builder-reported results, not independently reproduced test executions.** An unawaited asyncpg Connection._cancel teardown warning persists; -W error::RuntimeWarning did not make the run warning-free.

## V02 findings reevaluated
- **F11 IMPROVED / PARTIAL**: release_mps_plan() RELEASED retry now selects all positive-quantity lines, rejects missing links and missing orders, and checks target warehouse. New PostgreSQL test test_m20_strict_findings.py covers deleted order / nulled link. The source-level partial-release concern is mitigated, but full tenant/actor/warehouse/idempotent replay and audit-provenance negative matrix remains absent. Endpoint permission guard is builder-reported, not end-to-end independently proven.
- **F12 IMPROVED / PARTIAL**: PostgreSQL test asserts missing BOM produces PARTIAL_INPUTS, while nested BOM scenario test asserts calculated shortage with COMPLETE status and 2 KG vs 20 KG. This addresses the main semantic concern at builder-evidence level. More cases for mixed unknowns/shortages and rollback are needed.
- **F13 IMPROVED / PARTIAL**: Developer Portal client/auth tests now cover shared 401 redirect, actual configured backend origin, API keys/GraphQL routes, invalid JSON and timeout. Eleven browser cases are builder-reported. This does not establish production cookie/CSRF/CORS, all RBAC permutations or full Next 16 cross-application compatibility.
- **F01 P0 BLOCKED_EVIDENCE**: tenant/company/warehouse/permission positive and negative PostgreSQL matrix and durable audit trails still incomplete.
- **F02 P1 BUILDER_PROVEN_PARTIAL**: nested approved root→child→material DB scenario exists and builder reports pass; exhaustive effective date, UOM and negative DB cases still needed for full acceptance.
- **F03 P1 FAIL**: scenario material/capacity/changeover/currency cost not fully modeled; MERGE and SHIFT_ADD unsupported, SPLIT approximate. Missing authoritative CIP/minimum-run/currency policy cannot be invented, but missing-data contract should be independently tested.
- **F04 P1 BLOCKED_EVIDENCE**: durable diagnostic commit/replay, immutable snapshot round-trip, rollback/duplicate replay and API authorization still incomplete; teardown warning unresolved.
- **F05 / UI-01 / UI-02 P1 BUILDER_PASS / INDEPENDENT_BLOCKED_EVIDENCE**: responsive and Developer Portal E2E source and builder results improved. Local screenshots/traces not available for independent visual/traffic inspection. Cross-application Next 16 regression and permission/error paths remain.
- **F06 P1 BUILDER_PASS / INDEPENDENT_BLOCKED_EVIDENCE**: builder reports PostgreSQL migration upgrade/downgrade; receipts and DB integrity assertions insufficient for strict gate.
- **F07 P1 OPEN MASTER DATA**: minimum-run, CIP duration, approved currency cost source absent; preserve explicit UNKNOWN, do not fabricate.
- **F08 P0 FAIL**: M20 closure prohibited while critical blockers remain.
- **F09 P1 PARTIAL**: 20 task rows and commit URLs present, but partial evidence does not equal accepted tasks.
- **F10 P1 BUILDER_PASS / INDEPENDENT_BLOCKED_EVIDENCE**: 75 regression tests reported; previous test changes and asyncpg warning require targeted quality review.

## Twenty-task verdicts
S01.T001 PASS historical bounded; S01.T002 PASS historical bounded.
S01.T003 BLOCKED_EVIDENCE; S01.T004 BLOCKED_EVIDENCE (synthetic fixtures only).
S02.T001 BLOCKED_EVIDENCE; S02.T002 BLOCKED_EVIDENCE; S02.T003 BLOCKED_EVIDENCE (strong PostgreSQL test source); S02.T004 BLOCKED_EVIDENCE.
S03.T001 BLOCKED_EVIDENCE; S03.T002 BLOCKED_EVIDENCE (master data); S03.T003 BLOCKED_EVIDENCE (master data); S03.T004 BLOCKED_EVIDENCE.
S04.T001 BLOCKED_EVIDENCE; S04.T002 BLOCKED_EVIDENCE; S04.T003 BLOCKED_EVIDENCE; S04.T004 FAIL (incomplete).
S05.T001 BLOCKED_EVIDENCE (teardown warning and incomplete regression); S05.T002 BLOCKED_EVIDENCE (builder browser pass); S05.T003 BLOCKED_EVIDENCE (cross-module matrix incomplete); S05.T004 FAIL (milestone not accepted).

## Mandatory next actions
1. In **one continuous milestone remediation run**, complete tenant/company/warehouse/permission + release transaction positive/negative PostgreSQL matrix, committed diagnostics/snapshot replay, seeded MRP→MPS→BOM/inventory→production release, scenario negative and rollback paths.
2. Distinguish absent authoritative factory master data from incomplete software behavior; implement safe configurable behavior with explicit unknown status and targeted tests. Do not invent production policies.
3. Diagnose and eliminate asyncpg teardown unraisable warning at root cause. Preserve regression strength.
4. Provide exact-SHA commands/output, PostgreSQL migration and transaction receipts, API/authorization traces, Playwright screenshots/trace, Next 16 cross-app and dependency evidence, redacted of secrets. Do not claim independent PASS from builder reports.
5. Keep remote CI DEFERRED_CI_QUOTA through 2026-10-30; no remote CI without owner authorization. Codex must not edit TASKS.md or ChatGPT audits. ChatGPT alone updates canonical tracker.

**Disposition: M20 REMEDIATION IN PROGRESS. Do not close milestone.**
