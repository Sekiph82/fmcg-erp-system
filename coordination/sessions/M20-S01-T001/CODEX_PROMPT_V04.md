# M20.S01.T001 — Codex Remediation V04

Builder: Codex. Repository `Sekiph82/fmcg-erp-system`; `main` only.
Read `CHATGPT_AUDIT_V03.md` and the current `TASKS.md` (READ ONLY).
Do not edit tracker, history, any auditor files, or old `.hiveai` control plane. Preserve owner files; no destructive sync or new branches.

Resolve frozen V03 findings F-V03-001..004 with minimum architecture-consistent changes:
1. Prove **actual SQLAlchemy transaction rollback** on late failure using PostgreSQL-backed CI/test service or an existing real transactional fixture. Test persisted PO count, MPSLine linkage, MPSPlan status before/after. Never substitute a fake `begin()` rollback for real DB proof.
2. Reproduce the identical relevant regression suite in isolated clean exact-base and exact-V04-head environments. Classify each failure by test name, traceback, base/head status. Do not alter unrelated tests to manufacture green.
3. Establish and test coherent release atomicity: prefer all-or-none release when any positive unreleased line is blocked or has no approved effective recipe; preserve approved plan and zero new POs, with truthful blocker counters. If existing architecture requires partial release, document and prove safe idempotent retry and no false fully released state.
4. Investigate and fix PO number collision using an existing safe allocator if one exists; otherwise minimal unique allocation with transactional concurrency proof. Do not broaden into production redesign.
5. Run focused V01/V02/V03/V04, relevant MRP/production/auth/regression tests, compile/import, Alembic heads, `git diff --check`. Do not weaken tests or claim unavailable environments passed.

Commit implementation to `main`. Publish factual log at `coordination/sessions/M20-S01-T001/CODEX_LOG_V04.md`, including start/end SHAs, changed files, exact commands/results, clean base/head comparison, DB evidence, failures, limitations, and protected tracker diff checks. Log is not an audit. End `AWAITING_CHATGPT_AUDIT`; do not advance to T002.
