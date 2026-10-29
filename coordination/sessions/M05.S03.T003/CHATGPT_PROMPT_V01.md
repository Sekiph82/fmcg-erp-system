# M05.S03.T003 — Execution Prompt V01

Execute only `M05.S03.T003 — Validate negative-stock/concurrency safeguards` from root `TASKS.md` and this directory's `CHATGPT_AUDIT_CRITERIA_V01.md`. Use the generated `--spec` prompt as the task scope.

Read the active audit criteria and referenced task evidence, then trace the production code and API transaction paths before editing. Directly test and, only if proven necessary, narrowly correct: negative stock issue guard; duplicate concurrent GRN post; duplicate concurrent production completion; and competing production orders consuming limited stock. Use independent sessions and demonstrate PostgreSQL lock waits for concurrency tests. Preserve T001 sales allocation/dispatch behavior and T002 transactional behavior.

Use only a fresh disposable PostgreSQL database with passwordless loopback access and the exact M05.S03.T003 name enforced by the new test guard. Never write to a normal dev, owner, staging, or production DB. Keep rows and actors synthetic. Do not invent accounting, valuation, factory, staffing, approval, or retry policies. Do not inspect `.hiveai`, Codex private databases, or AppData; do not use/open the dashboard; do not modify FormuLab or create another checkout. Do not run GitHub Actions for M20 through 2026-10-30.

At the task boundary run `node scripts/codex/task-queue.mjs --apply-answers` once and apply only exact matching Q-ID/task-ID decisions. Use one implementation executor and one independent read-only reviewer. Record actual commands/results, all failed attempts and fixes, changed files, hashes, DB/container containment and cleanup, exact commit/push, and review in `coordination/sessions/M05.S03.T003/CODEX_LOG_V01.md`. Do not self-claim an independent audit verdict or production acceptance.
