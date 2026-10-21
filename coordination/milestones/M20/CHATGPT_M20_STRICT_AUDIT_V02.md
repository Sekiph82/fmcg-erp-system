# M20 INDEPENDENT STRICT RE-AUDIT V02 — 2026-10-21
**Overall verdict: FAIL / CHANGES_REQUIRED. Do not close M20.**
Criteria (unchanged): https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md
Builder submission: https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/milestones/M20/CODEX_M20_FINAL_EXECUTION_LOG_V03.md
Reviewed implementation commits:
https://github.com/Sekiph82/fmcg-erp-system/commit/cc8a1019092510248db374fd93a34966a1f614d6
https://github.com/Sekiph82/fmcg-erp-system/commit/bb09ccadd158a5693d78298ffd11dad3aa56eecf
https://github.com/Sekiph82/fmcg-erp-system/commit/9976b20975b26254f7a3811b5aa8ace147651f94
Independent source inspection was performed against GitHub main. **No local PostgreSQL, pytest, browser, or frontend build was independently executed by ChatGPT.** All reported 73 pytest passes, browser E2E passes, migration passes and build results are builder claims, not independently reproduced PASS. The supplied test source and actual code paths were inspected.

## Strict findings and dispositions
- **F01 P0 BLOCKED_EVIDENCE**: PostgreSQL late-flush rollback, concurrent PO numbering and nested BOM savepoint test source exists; builder reports execution. Required full company/tenant/warehouse/permission positive+negative transaction matrix, idempotent release replay, and audit provenance remain incomplete. This is a critical gate.
- **F02 P1 IMPROVED / BLOCKED_EVIDENCE**: Nested BOM recursion and a real DB integration test source exist, with root→child→material and 2 KG vs 20 KG assertion. Builder reports test PASS. This is meaningful new evidence, but no independent rerun and no exhaustive effective-date/UOM/substitution/negative integrated matrix; do not call full M20 acceptance.
- **F03 P1 FAIL**: Scenario implementation and builder log explicitly leave approved-currency cost, CIP duration, MERGE/SHIFT_ADD and exact SPLIT unresolved. Current code explicitly rejects MERGE/SHIFT_ADD and approximates SPLIT. Mandatory scenario comparison incomplete.
- **F04 P1 BLOCKED_EVIDENCE**: 73 builder-reported tests now include PostgreSQL source-backed tests; improved from earlier 18. Durable diagnostics/snapshot replay and full API/tenant/permission regressions remain absent. Pytest unraisable Connection._cancel warning requires isolation/cleanup diagnosis; no silent suppression.
- **F05 P1 PARTIAL / BLOCKED_EVIDENCE**: Browser E2E source exists and builder reports 6 Developer tests and one viewport loop across 5 sizes/9 tabs. This supports UI-01/UI-02 at builder level. Browser screenshot artifacts are local only, not accessible for independent visual verification. Developer tests mock failure responses; success test observes 200s, not a complete real-backend contract and auth matrix.
- **F06 P1 IMPROVED / BLOCKED_EVIDENCE**: Builder claims local PostgreSQL migration fresh upgrade/downgrade/re-upgrade to 20261021_0010. Migration source exists; exact SQL outputs/DB constraints/FK/JSONB/duplicate replay proof and independent rerun not available. Structural Alembic head alone is insufficient.
- **F07 P1 OPEN**: Authoritative minimum-run, CIP and approved currency/cost master data unavailable; unknowns must remain explicit. Do not fabricate factory data.
- **F08 P0 FAIL**: M20 cannot close with F01/F03/F04/F07 and cross-module acceptance open.
- **F09 P1 PARTIAL**: Twenty task rows and full commit URLs exist; many rows explicitly say partial proof. Traceability alone not behavioral acceptance.
- **F10 P1 IMPROVED / BLOCKED_EVIDENCE**: Historical regression tests were modified in bb09cc... to accommodate new behavior; builder reports 73 passing on current source. Verify tests have not weakened prior assertions and reproduce exact SHA; no independent run.
- **UI-01 P1 BUILDER_PASS / INDEPENDENT_BLOCKED_EVIDENCE**: responsive geometry assertions inspect main content at 1536,1920,1366,768,390 and nine integration tabs; builder claims run passed. Screenshots remain ignored local artifacts; no independent visual review of after-state.
- **UI-02 P1 BUILDER_PASS / INDEPENDENT_BLOCKED_EVIDENCE**: request helper now uses configured apiClient.getUri and checks response.ok/content-type; E2E covers HTML 404, 401,403, HTML 200,500 and retry claims. Source file developer-portal-errors.spec.ts has six test() blocks. Need actual network trace, backend auth/route behavior, timeout and invalid JSON recovery evidence. Next.js major upgrade 14→16 also requires dependency/security and cross-app regression, not just build.
- **NEW F11 P0 — Potential release idempotency correctness gap (source-level)**: in backend/app/services/mps_service.py, release_mps_plan() returns idempotent success for RELEASED status after reading non-null production_order_id rows; it does not visibly check that all required lines still have surviving orders, nor re-validate requester authorization in that early-return branch. Add real PostgreSQL negative tests for missing/deleted order, wrong warehouse, wrong actor/tenant, partial releases and concurrency; fix if confirmed. Do not infer exploitable security vulnerability without proving route guards.
- **NEW F12 P1 — Simulation status semantics**: _simulate_scenario_materials() sets status COMPLETE only if both baseline/candidate infeasible_lines == 0, even when shortage quantities are computed; verify distinction between complete calculation with shortage and missing/unknown input, and test shortage_count_delta behavior. Ensure true material shortage is not silently labeled missing data.
- **NEW F13 P1 — Client response/authorization contracts**: frontend/src/lib/api_portal_api.ts uses fetch(apiClient.getUri(...)) instead of axios; therefore axios response interceptors are bypassed. Check login/session-expiry behavior and whether authorization is cookie-only as intended. Confirm API key/GraphQL routes, CORS and production base URL. Test 401 recovery and secure contract validation, not merely text messages.

## Task-by-task strict status
S01.T001 PASS (previous bounded); S01.T002 PASS (previous bounded).
S01.T003 BLOCKED_EVIDENCE; S01.T004 FAIL (synthetic-only).
S02.T001 BLOCKED_EVIDENCE; S02.T002 BLOCKED_EVIDENCE; S02.T003 BLOCKED_EVIDENCE (strong new DB test source); S02.T004 BLOCKED_EVIDENCE.
S03.T001 BLOCKED_EVIDENCE; S03.T002 BLOCKED_EVIDENCE; S03.T003 BLOCKED_EVIDENCE; S03.T004 BLOCKED_EVIDENCE.
S04.T001 BLOCKED_EVIDENCE; S04.T002 BLOCKED_EVIDENCE; S04.T003 BLOCKED_EVIDENCE; S04.T004 FAIL.
S05.T001 BLOCKED_EVIDENCE; S05.T002 BLOCKED_EVIDENCE; S05.T003 BLOCKED_EVIDENCE; S05.T004 FAIL.
UI-01 BLOCKED_EVIDENCE (builder PASS); UI-02 BLOCKED_EVIDENCE (builder PASS).

## Required remediation and final audit evidence
1. Implement missing mandatory functionality and transaction/permission/scope integration cases; no fabricated policy data.
2. Publish complete deterministic test output (commands, SHA, failures, skips), DB migration receipts, test fixture isolation and after-state, API request/response evidence, browser screenshots/trace, and regression after Next 16 migration. Redact secrets.
3. Fix F11–F13 if reproduced; add negative regression tests. Separate blocked factory configuration from incomplete implementation.
4. Diagnose unraisable coroutine warning, avoid silent test suite false-positive.
5. Maintain CI quota restriction through 2026-10-30 and beyond without owner authorization; do not touch TASKS.md or ChatGPT audit files from Codex.
6. ChatGPT will independently inspect code and evidence and update canonical tracker only on acceptance. Remote CI deferral is not a substitute for local functional evidence.
