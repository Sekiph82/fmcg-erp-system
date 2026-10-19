# M20.S01.T001 — Codex V05 Remediation and PostgreSQL Evidence

Builder: Codex. Auditor and tracker owner: ChatGPT. Branch: `main` ONLY. Source of truth: GitHub `main`. Preserve dirty owner work. Do not create branches, reset, clean, or modify `TASKS.md`, `TASKS_HISTORY.md`, `CHATGPT_AUDIT_*` or old `.hiveai` control-plane files.

## Frozen V04 audit state
V04 implementation `158d281`, log `f8f6404`. Source shows all-or-none preflight and PostgreSQL advisory lock. Builder reported clean comparison `173 passed, 4 failed` at base and `173 passed, 3 failed, 2 skipped` at V04. **The two PostgreSQL tests were SKIPPED, so database rollback and concurrency are NOT PROVEN.** Three GAP-012/013/014 failures are reported as baseline, not independently resolved. Task remains IN_PROGRESS.

## Required corrections and proof
1. **Make PostgreSQL-backed rollback and concurrency tests executable and run them in an actual PostgreSQL environment** (CI service, hosted runner or a working non-destructive local DB). Never accept a skip as proof. Inspect test fixtures first: correct ID assignment/flush order for Product→Recipe and Plan→Line; correct session lifetime, patch target, transaction boundary, committed state checks, cleanup and imports. Fix test bugs rather than bypassing assertions. Capture exact test IDs, XML/log, pass/fail/skip and GitHub Actions run URL or verifiable execution evidence. If no DB runtime is accessible, report BLOCKED_DB_PROOF; do not assert PASS.
2. **Rollback proof**: trigger failure after at least one real PO insert/flush, then verify using an independent SQLAlchemy session that no new PO, line linkage, or RELEASED status persisted. Validate endpoint transaction semantics with the real dependency/session lifecycle.
3. **Concurrency and numbering**: exercise two real concurrent releases; ensure distinct order numbers and correct committed link/status. Audit `count(PO-MPS-*)+1` after gaps/deletion: advisory lock serializes callers but does not prevent number reuse after deletes. Reuse canonical DB sequence/allocator if available, otherwise minimally implement collision-safe monotonic allocation (or bounded unique-conflict retry with proof). Never alter unrelated PO numbering. Include gap/deletion and concurrent tests.
4. **Regression attribution**: preserve exact clean base/head commands, failure names and tracebacks for GAP-012/013/014. Do not silently weaken tests. Report these as separate baseline issues if unchanged.
5. Run focused MPS tests, MRP/production/permission regression, compile/import, Alembic heads and `git diff --check`. No invented live/provider test success or production certification.

## Mandatory output
Commit implementation and factual evidence to `main`. Write **exactly** `coordination/sessions/M20-S01-T001/CODEX_LOG_V05.md` with start/final SHAs, changed files, test commands/results, actual PostgreSQL runtime proof or explicit blocker, CI URLs/artifacts, regressions, outstanding risks, and confirmation protected tracker/auditor files untouched. This is a builder log, NOT an audit. End `AWAITING_CHATGPT_AUDIT` with log link. Do not start T002 until ChatGPT independently accepts T001 and updates tracker.
