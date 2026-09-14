# M20-S01-T001 V03 — Strict Audit Criteria

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Task: `M20.S01.T001`
Revision purpose: close frozen V02 findings `F-V02-001` through `F-V02-004`.

These criteria are for ChatGPT's independent audit after Claude implementation. Claude does not audit itself.

## A. Governance

- **M20S01-V03-001** Work only on `Sekiph82/fmcg-erp-system` `main`.
- **M20S01-V03-002** Safely sync with `origin/main`; preserve owner work; no force push/destructive reset/clean.
- **M20S01-V03-003** `TASKS.md` and `TASKS_HISTORY.md` remain unmodified by Claude.
- **M20S01-V03-004** Changes are limited to F-V02-001..004 and directly necessary tests/evidence.

## B. Whole-plan release truth

- **M20S01-V03-010** `RELEASED` is not derived merely from `created > 0`.
- **M20S01-V03-011** If any FEASIBLE/release-required line fails PO creation, the plan remains fail-closed and is not marked fully RELEASED.
- **M20S01-V03-012** The code explicitly defines whether non-FEASIBLE unresolved lines block whole-plan RELEASED or are outside the release set; behavior and return payload must agree.
- **M20S01-V03-013** Mixed partial release is behaviorally tested: at least one PO created + at least one release-required line skipped/fails => plan not RELEASED.
- **M20S01-V03-014** Return payload truthfully reports created/skipped/unresolved counts and completion state.

## C. UOM/master-data integrity

- **M20S01-V03-020** No local hard-coded `KG` fallback is used when Product or authoritative UOM cannot be resolved.
- **M20S01-V03-021** Missing Product fails closed before PO creation for that line/release transaction.
- **M20S01-V03-022** Missing/invalid UOM follows existing authoritative repository semantics; no new duplicate default/conversion rule is invented.
- **M20S01-V03-023** Behavioral tests cover missing Product and missing/invalid UOM.

## D. Transactional partial-failure integrity

- **M20S01-V03-030** A release attempt that succeeds on an early line and fails on a later line cannot persist a partial ProductionOrder set if the service contract is all-or-fail.
- **M20S01-V03-031** Transaction rollback is proven behaviorally at endpoint/transaction level, not by source string inspection only.
- **M20S01-V03-032** After rollback, plan status, MPS line PO linkage and persisted ProductionOrders remain consistent with pre-call state.
- **M20S01-V03-033** Service does not introduce internal commits that defeat the outer transaction.

## E. Regression evidence

- **M20S01-V03-040** Focused V01/V02/V03 MPS tests pass.
- **M20S01-V03-041** Relevant MRP/production/auth/module-registry/recipe/warehouse tests pass except only demonstrably pre-existing unrelated failures.
- **M20S01-V03-042** If the same three module-registry failures remain, exact before/after or base-commit evidence proves all three existed before the V03 implementation diff.
- **M20S01-V03-043** Backend compile/import checks pass.
- **M20S01-V03-044** `git diff --check` passes.
- **M20S01-V03-045** No test is deleted/disabled/weakened merely to obtain green.

## F. Evidence log

- **M20S01-V03-050** Claude creates exactly `coordination/sessions/M20-S01-T001/CLAUDE_LOG_V03.md`.
- **M20S01-V03-051** Log records starting GitHub SHA, implementation SHA(s), exact changed files, commands/results, failures/fixes, blockers and remaining risks.
- **M20S01-V03-052** Log contains factual evidence only and no audit PASS/FAIL verdict.
- **M20S01-V03-053** All authorized changes and log are pushed safely to `main`.

## G. Closure law

- **M20S01-V03-060** ChatGPT independently audits actual source/diff/tests/log after V03.
- **M20S01-V03-061** Claude does not modify tracker state.
- **M20S01-V03-062** M20.S01.T001 closes only if the frozen P1 findings are resolved and transactional proof is sufficient.
