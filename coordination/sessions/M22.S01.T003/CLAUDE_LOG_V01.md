# M22.S01.T003 — Approval/release/cancel/close semantics

**State:** Implementation and independent source review complete; runtime and database acceptance not run.

## Scope and acceptance material

- Current task: \`TASKS.md\` row \`M22.S01.T003\`, the sole task authority.
- Domain acceptance: \`coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md\`. It assigns approval/release authority to the parent and says operation completion is not parent approval.
- Applicable governance: \`coordination/AUDIT_POLICY.md\` and \`coordination/AUDIT_INDEX.md\`; relevant findings include exact state guards, authenticated scoped actions, migration evidence, and adversarial review of critical production flows.
- Latest general strict audit considered: \`coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md\`. It is an M20 audit, not an M22 task verdict. No M22.S01.T003-specific audit was present.

## Synchronization and preserved work

- Starting \`HEAD\`: \`920dd205725c628fd449448c596843bdc9c77b5b\`.
- Fetched \`origin/main\` at task start: same SHA; committed divergence was 0 ahead / 0 behind.
- The pre-existing tracker claim for this task was maintained through the task queue. The unrelated tracked owner edit in \`frontend/next-env.d.ts\` and unrelated local/untracked owner files were left unchanged and unstaged.
- FormuLab and other checkouts were not modified.

## Implementation

- Added separate parent-order approval actions and actor/timestamp fields for both \`ProductionOrder\` and the active \`ProdExecOrder\` compatibility surface. Added migration \`20261104_0002\` after \`20261104_0001\`; canonical approver deletion is restricted to retain its approval reference.
- Approval is permitted only for PLANNED parent orders, records the authenticated approver and time, rejects repeated approval, rejects self-approval, and fails closed when creator attribution is missing. Release requires this approval. Canonical recipe approval and QMS release gates remain in place.
- Approved planning is frozen across parent edits, canonical and execution work-order create/edit/delete, execution material planning, and canonical work-order import. The import rechecks the locked parent before insertion.
- Cancellation is limited to pre-execution states. Execution-order close remains available only after completion; canonical \`COMPLETED\` is terminal because that status model has no separate \`CLOSED\` state.
- Execution material issue/return now locks the parent and material row. Issue requires RELEASED/IN_PROGRESS and a positive quantity; return is bounded by issued, unconsumed and unreturned quantity, with controlled returns still allowed after cancellation.
- Split/merge now require cancel permission on each source and create permission at the resulting scope. Split/merge preserve operational scope; merge requires matching product, UOM, BOM, routing, machine, scope, source and schedule. Each merge source receives its own link to the common result in the existing split/merge history table. Rework requires a completed/closed parent, positive quantity and create permission.
- Both production UIs expose approval separately from release, show approval attribution, and restrict cancellation controls to pre-execution states.

## Independent review

- Independent read-only reviewer: \`/root/m34_s03_t004_review\`.
- The reviewer identified stale approvals after plan edits, split/merge permission bypasses, material movement before release, incompatible merge inputs, missing creator attribution, canonical child/import bypasses, cancelled-order material reconciliation, and rework/merge-history gaps.
- Those findings were addressed in the source. The final read-only pass reported no remaining blockers. The reviewer did not edit files or run tests.

## Checks and limitations

- \`git diff --check\`: passed after the final source changes.
- \`node scripts/codex/validate-task-state.mjs\` and \`node scripts/codex/task-queue.mjs --check\`: passed at task start for the explicit CODEX task. They will be rerun at the task boundary.
- Automated tests, frontend type-check/build, Alembic upgrade/downgrade, and runtime/database checks were not run. No test PASS, migration PASS, live-factory behavior, or production deployment is claimed.

## Changed implementation paths

- \`backend/alembic/versions/20261104_0002_m22_order_approval_semantics.py\` (new)
- \`backend/app/api/v1/endpoints/bulk_import.py\`
- \`backend/app/api/v1/endpoints/production.py\`
- \`backend/app/api/v1/endpoints/production_execution.py\`
- \`backend/app/crud/production_advanced.py\`
- \`backend/app/models/production.py\`
- \`backend/app/models/production_execution.py\`
- \`backend/app/schemas/production.py\`
- \`backend/app/schemas/production_execution.py\`
- \`backend/app/services/production_service.py\`
- \`backend/app/services/production_execution_service.py\`
- \`frontend/src/app/dashboard/production/orders/[id]/page.tsx\`
- \`frontend/src/app/dashboard/production-execution/[id]/page.tsx\`
- \`frontend/src/app/dashboard/production-execution/page.tsx\`
- \`frontend/src/lib/production.ts\`
- \`frontend/src/lib/productionExecution.ts\`

\`TASKS.md\` lifecycle state is updated by the authorized task-queue transition after these implementation notes.
