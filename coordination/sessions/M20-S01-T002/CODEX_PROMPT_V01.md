# M20.S01.T002 — Codex Master Execution Prompt V01

Repository: `Sekiph82/fmcg-erp-system`. Branch: `main` only. ChatGPT owns `TASKS.md` lifecycle and independent audits. Codex may not edit `TASKS.md`, `TASKS_HISTORY.md`, `CHATGPT_AUDIT_*` or legacy .hiveai trackers. Preserve dirty owner work; no reset, clean, force push or new branches.

**Task:** Preserve and prove existing MPS planning-board, capacity, campaign and what-if capabilities; do not rebuild existing features. Read canonical tracker, M20 master prompt, M20.S01.T001 V06 audit and source/backend/frontend.

1. Inventory all existing MPS models, services, endpoints, schemas, migrations, frontend routes/components and tests for planning board, work-center capacity, campaigns, and what-if scenarios. Produce a traceability matrix of feature → source path/symbol → API/UI route → current test → observed gap.
2. Add bounded deterministic preservation/regression tests covering existing behaviors, auth/RBAC and approval/release integration. Include realistic negative cases; avoid source-string-only tests. Only implement narrow fixes directly necessary to preserve the existing contract; defer broader M20.S02–S05 feature work.
3. Verify MPS release remains atomic and sequence-safe using the accepted PostgreSQL CI evidence; do not regress T001. Test MPS UI/API alignment and tenant/company/warehouse isolation where applicable. Never claim unsupported features exist.
4. Execute focused backend suites, real DB integration if available, frontend typecheck/build where possible, compile/import, Alembic heads, diff check. CI has known **seven unrelated backend failures** (eTIMS 2, registry route wrappers 5) and **frontend npm audit vulnerability gate**; report exact status, do not weaken tests or silently change unrelated dependencies.
5. Publish evidence matrix and factual log at `coordination/sessions/M20-S01-T002/CODEX_LOG_V01.md`, with source SHAs, changed files, test commands/results, CI URLs, remaining risks, protected tracker confirmation. Commit and push to `main`. Finish `AWAITING_CHATGPT_AUDIT`. Do not self-close T002 or start T003 without independent audit.
