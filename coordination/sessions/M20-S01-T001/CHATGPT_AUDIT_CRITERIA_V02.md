# M20-S01-T001 V02 — Strict Audit Criteria

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Task: `M20.S01.T001`
Revision purpose: close the complete frozen V01 finding set F-V01-001 through F-V01-009.

These criteria are for ChatGPT's independent audit after Claude implementation. Claude does not perform the audit and does not assign PASS/FAIL.

## A. Governance

- **M20S01-V02-001** Work only in `Sekiph82/fmcg-erp-system` on `main`.
- **M20S01-V02-002** Safely sync local workspace with `origin/main`; preserve all owner work; no force push/destructive reset/clean.
- **M20S01-V02-003** `TASKS.md` and `TASKS_HISTORY.md` remain unmodified by Claude.
- **M20S01-V02-004** No competing `.hiveai` tracker is recreated.
- **M20S01-V02-005** Changes remain limited to the frozen V01 findings and directly necessary regression tests/docs.

## B. Authorization proof

- **M20S01-V02-010** MPS routes continue to use authenticated current-user/RBAC dependencies.
- **M20S01-V02-011** Real negative request/dependency tests prove unauthenticated access fails.
- **M20S01-V02-012** Real negative tests prove authenticated-but-unauthorized critical mutation fails with the expected authorization behavior.
- **M20S01-V02-013** Tests do not rely only on `inspect.getsource()` or string counting for auth proof.

## C. MRP lineage

- **M20S01-V02-020** MRP run existence and COMPLETED-state checks remain enforced.
- **M20S01-V02-021** Every deterministic current-schema context invariant between MPS plan and MRP run is enforced.
- **M20S01-V02-022** An unrelated completed MRP run is rejected when the current schema provides enough information to determine mismatch.
- **M20S01-V02-023** Any schema limitation preventing stronger lineage validation is documented precisely, without inventing new broad schema in this task.

## D. Release target and recipe integrity

- **M20S01-V02-030** Target warehouse is validated before any ProductionOrder is created.
- **M20S01-V02-031** Existing active/status/plant constraints on Warehouse are honored if present in the current model.
- **M20S01-V02-032** Recipe selection follows the strongest existing lifecycle truth: approval/status/effective/current/version semantics where available.
- **M20S01-V02-033** Recipe selection is deterministic when multiple candidates exist.
- **M20S01-V02-034** Tests prove invalid warehouse and invalid/ambiguous recipe conditions fail safely.

## E. ProductionOrder semantics

- **M20S01-V02-040** ProductionOrder UOM is derived from authoritative existing product/recipe/master data, not hard-coded `KG`.
- **M20S01-V02-041** No new duplicate UOM conversion rule is introduced.
- **M20S01-V02-042** MPS line to ProductionOrder linkage remains exactly-once.

## F. Truthful release state

- **M20S01-V02-050** A plan cannot become fully RELEASED when required eligible lines fail creation or required unresolved lines remain, unless an explicit existing partial-release state contract supports it.
- **M20S01-V02-051** Zero-order release cannot falsely produce successful RELEASED state.
- **M20S01-V02-052** Skipped-no-recipe and ineligible conditions are surfaced truthfully and state remains fail-closed/actionable.
- **M20S01-V02-053** Partial failure inside order creation cannot leave a misleading lifecycle state.

## G. Behavioral idempotency

- **M20S01-V02-060** Repeated release is tested behaviorally, not by source string count.
- **M20S01-V02-061** Second release cannot create additional ProductionOrders.
- **M20S01-V02-062** Already RELEASED/CLOSED state is rejected or otherwise fail-closed by the real service contract.

## H. Migration ownership proof

- **M20S01-V02-070** Exact revision/file responsible for fresh-database MPS table creation is identified.
- **M20S01-V02-071** If metadata-driven baseline creation is used, the audit trail proves MPS model tables are loaded into metadata at migration execution time.
- **M20S01-V02-072** No duplicate migration is added unless fresh-DB evidence proves one is required.
- **M20S01-V02-073** Alembic remains single-head.

## I. Regression evidence

- **M20S01-V02-080** Focused M20 tests pass.
- **M20S01-V02-081** Relevant MRP tests pass.
- **M20S01-V02-082** Relevant production-order/production tests pass.
- **M20S01-V02-083** Relevant module-registry/auth tests pass.
- **M20S01-V02-084** If unrelated failures remain, before/after or isolated-main evidence proves they are not introduced by V02.
- **M20S01-V02-085** Backend compile/import checks pass.
- **M20S01-V02-086** Frontend type-check/build passes if frontend is changed.
- **M20S01-V02-087** `git diff --check` is clean.
- **M20S01-V02-088** No strict test is deleted/disabled/weakened to obtain green.

## J. Evidence log

- **M20S01-V02-090** Claude writes exactly `coordination/sessions/M20-S01-T001/CLAUDE_LOG_V02.md`.
- **M20S01-V02-091** Log records start SHA, implementation SHA(s), exact changed files, exact commands/results, failures/fixes, blockers, migration evidence and remaining risks.
- **M20S01-V02-092** Log contains factual evidence only; no self-audit PASS/FAIL verdict.
- **M20S01-V02-093** All implementation/log changes are pushed to `main` safely.

## K. Closure law

- **M20S01-V02-100** ChatGPT independently audits V02 source/diff/tests/log against these criteria.
- **M20S01-V02-101** Claude does not close the task or update tracker state.
- **M20S01-V02-102** M20.S01.T001 closes only after all P1 findings are resolved and remaining P2 proof gaps are either resolved or explicitly accepted by ChatGPT with sufficient independent evidence.
