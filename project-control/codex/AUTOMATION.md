# FMCG ERP Codex Automation Contract

## Task authority

The repository root `TASKS.md` is the only task authority. Never read or write `.hiveai`. A dashboard selection changes only displayed activity. The queue runner and heartbeat always resolve this repository root and read `TASKS.md` directly.

Before work, run `node scripts/codex/validate-task-state.mjs` and `node scripts/codex/task-queue.mjs --check`. Resume only the exact `Current Task` and require `Required Actor: CODEX`. When a task finishes, mark its canonical row `[x]`, set its status to `COMPLETE`, and choose the next dependency-ready M20 task from `TASKS.md` using acceptance criteria and dependencies. Write the exact ID and title to `Next Task/Action`; do not select solely by checkbox order. This owner-authorized selection does not require a routine owner prompt.

The task runner applies an owner answer only when both Q-ID and task ID match the open tracker question. It records the answer once in `Owner Decisions`, removes that question, and returns only the matching blocked row to READY. Report owner questions and required actions directly in this conversation; do not use the dashboard for queue operation.

## Review and evidence

Use one implementation executor and one independent read-only reviewer. A reviewer cannot edit task or source files. Do not claim review or test PASS without actual evidence. Use `SPEC`, `BUILD`, `REVIEW`, `APPROVE`, `MERGED`, and `ESCALATED` in job metadata only as those actions begin. Update `updatedAt` on every stage, round, or review change. `APPROVE` requires all applicable reviews to pass. `MERGED` requires accepted code published to the authorized target branch.

## Conversation handoff

At a task boundary, run `node scripts/codex/task-queue.mjs --apply-answers` and apply only exact Q-ID/task-ID matches once. After writing the dependency-ready successor, run `node scripts/codex/task-queue.mjs --spec`; it must return `SPEC_READY` for that exact canonical row. Before claiming or implementing it, synchronize local `main` with `origin/main`: fetch, inspect divergence and the working tree, preserve all owner changes, and reconcile without reset, clean, force-push, or rebase. The owner authorizes committing and pushing completed task work when required for synchronization, after local checks and independent review; suppress Actions and never dispatch GitHub Actions for M20 through 2026-10-30. If reconciliation is unsafe, stop that task and explain the specific conflict in Turkish.

## Publication and owner gates

Never fabricate human decisions, credentials, factory data, approval, or test evidence. Continue independent READY work while a task awaits an owner decision. Publication is authorized only for completed, locally verified, independently reviewed task work needed to synchronize the owner-authorized local checkout and GitHub main; never force-push. Do not run GitHub Actions for the current M20 work; the tracker defers remote CI through 2026-10-30.

## Commands

- Validate task authority: `node scripts/codex/validate-task-state.mjs`
- Inspect the explicit task: `node scripts/codex/task-queue.mjs --check`
- Claim the explicit READY task: `node scripts/codex/task-queue.mjs --claim`
- Apply matching inbox answers at a task boundary: `node scripts/codex/task-queue.mjs --apply-answers`
- Generate an explicit successor SPEC prompt: `node scripts/codex/task-queue.mjs --spec`
- Run queue tests: `node --test scripts/codex/task-queue.test.mjs`
- Run metadata transition tests: `node --test scripts/codex/job-state.test.mjs`
- Record a PASS review only with a repository evidence file: `node scripts/codex/job-state.mjs --task M20.S01.T003 --review rules=pass --evidence coordination/path/to/review-evidence.md`
- Verify App Server listing request scope: `node --test scripts/codex/app-server-client.test.mjs`
- Run dashboard tests: `node --test scripts/codex/dashboard-server.test.mjs scripts/codex/dashboard-ui.test.mjs`
