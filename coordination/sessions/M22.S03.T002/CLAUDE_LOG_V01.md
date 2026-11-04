# M22.S03.T002 — Dependency/predecessor enforcement

Date: 2026-11-04
Actor: CODEX
State: IMPLEMENTED; acceptance and M22 milestone verification pending.

## Scope and acceptance material

- Canonical task: root `TASKS.md`, exact row `M22.S03.T002 — Dependency/predecessor enforcement`.
- Generated implementation handoff: `node scripts/codex/task-queue.mjs --spec`, status `SPEC_READY`, for this exact task.
- Domain acceptance: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`. A canonical `WorkOrder` is a routed operation under its `ProductionOrder`; the separate `exec_*` family remains independent and must not be cross-linked or modified here.
- Governance/latest audit material: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md`, and `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`. V06 is an M20 verdict, not an M22 task-specific audit. No M22.S03.T002-specific criteria or audit was present.
- The preceding routing task log explicitly left operation start gates to this task and did not infer parallel-group semantics from `RoutingStep.is_parallel`.

## Implementation

- Canonical routed WorkOrders now require every lower-numbered step in the same routing and production order to have at least one active WorkOrder, and every such active row must be `COMPLETED`, before start. Missing or cancelled-only predecessors fail closed.
- Cancelled split/merge source rows do not themselves block a route when active replacement rows exist for that step; all active replacements must complete. The existing parent-first lock acquired by lifecycle transitions serializes predecessor checks with canonical WorkOrder state changes on that production order.
- Unrouted/manual WorkOrders retain the existing start path. The separate `exec_*` predecessor implementation was not modified. No migration or owner-data change was needed.
- `RoutingStep.is_parallel` has no group identity or dependency representation. Until the model can express parallel groups, routed steps are conservatively sequenced by `step_number`; the implementation does not enable concurrent parallel execution.
- Added guarded disposable-PostgreSQL regression cases for the exact loopback, passwordless M22.S03.T002 database; they cover all-earlier-step gating, missing/cancelled predecessors, completed replacement rows, and the manual-operation boundary.

## Preliminary review and verification limits

- Focused read-only implementation reviewer: `/root/m22_s03_t002_review`; consolidated independent review remains pending at M22 acceptance.
- The reviewer identified two test error-message expectation mismatches after the cancelled-source handling changed. Both expectations were corrected and the reviewer confirmed that correction with no remaining findings. The reviewer did not edit files or run tests.
- Automated tests were intentionally deferred to the requested M22 milestone-batched verification. No test PASS is claimed.
- `git diff --check` passed (exit code 0). No migration was added.

## Synchronization and preserved work

- Before the task claim, fetched `origin/main`; `HEAD` and `origin/main` were both `1749fbd428aefdff8dd2bc3276445dd8c9e3b5c8` with 0/0 divergence.
- The unrelated tracked owner edit in `frontend/next-env.d.ts` and all unrelated untracked files were left unstaged and unchanged.
- The task-queue script, not this log, owns the exact task-state transition in root `TASKS.md`.
- FormuLab and other checkouts were not modified.
