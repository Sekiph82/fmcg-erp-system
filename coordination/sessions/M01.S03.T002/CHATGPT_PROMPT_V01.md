# M01.S03.T002 — Execution Prompt V01

Execute only `M01.S03.T002 — Validate migration ownership on live-like database` from root `TASKS.md`.

Read `CHATGPT_AUDIT_CRITERIA_V01.md`, `coordination/AUDIT_INDEX.md` rule ERP-AL-013, the older `docs/planning/GAP-DB-001_LIVE_MIGRATION_VERIFICATION.md`, and latest M01 disposable PostgreSQL evidence. Reconcile historical heads against the current source before testing. Prove a single head, fresh full-chain upgrade, exact `alembic_version`, model/table parity, representative relational objects, and `alembic check` on a unique task-owned disposable PostgreSQL database. Record all failures and fixes honestly in `CODEX_LOG_V01.md`.

Use only loopback networking, an empty uniquely named disposable DB, synthetic data if needed, no persistent volume, and no owner/provider credentials. Do not touch the project's normal development database or any production/staging database. If a migration ownership defect is proven, fix it additively only when the exact change is unambiguous and data-safe; preserve newer and unrelated work. Run `node scripts/codex/task-queue.mjs --apply-answers` at the task boundary and use one independent read-only reviewer. Do not claim production acceptance.
