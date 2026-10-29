# M05.S03.T001 — Execution Prompt V01

Execute only `M05.S03.T001 — Validate reservation/allocation consistency` from root `TASKS.md`.

Read `CHATGPT_AUDIT_CRITERIA_V01.md`, `coordination/AUDIT_INDEX.md` rules ERP-AL-003/004/011/012, `coordination/AUDIT_POLICY.md`, the applicable GAP-010 sales and GAP-008 WMS audits, the legacy row-lock warning, and the current sales/inventory services and models. Validate actual reservation behavior, rollback, cancellation, dispatch and concurrency with synthetic disposable-PostgreSQL scenarios. Do not infer production usage from fixtures.

Keep changes narrow. Preserve row locks unless PostgreSQL concurrency tests prove an alternative safe. Verify each invariant directly and make each negative test fail for the intended guard. If a correction requires an unapproved reservation policy or schema redesign, document the blocker instead of guessing. Do not use real customer, employee, factory or owner DB data; do not run external integrations or GitHub Actions.

At the task boundary run `node scripts/codex/task-queue.mjs --apply-answers` and apply only exact Q-ID/task-ID matches once. Use one executor and one independent read-only reviewer. Record all commands, failures, cleanup and truthful limits in `CODEX_LOG_V01.md`. On completion, close this exact row in TASKS.md and select only the next dependency-ready canonical task.