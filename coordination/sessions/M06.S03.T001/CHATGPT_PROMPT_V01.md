# M06.S03.T001 — Implementation prompt V01

Implement only `M06.S03.T001 — Verify three-way-match transaction chain` from root `TASKS.md`, following `CHATGPT_AUDIT_CRITERIA_V01.md` in this directory.

At start, confirm the canonical root is `C:\Users\sekip\Desktop\fmcg-erp-system`, fetch and inspect `origin/main`, preserve all pre-existing local changes, and record the exact starting revision. Use a task-specific synthetic PostgreSQL database with the test's exact-name/passwordless-loopback guard. Do not use any existing application, owner, development, staging, or production database.

Read the existing procurement, purchase-invoice, invoice-match, and stock-ledger services and their relevant tests before changing source. Add direct database-backed tests for draft-versus-posted GRN matching, exact accepted quantity, overbilling hold, supplier/PO identity, repeat match/rerun behavior, and persisted transaction links. If a test exposes an in-scope defect, correct it narrowly without adding unapproved AP/GL or tolerance policy. The accepted GAP-002 audit states that AP/GRNI journal integration is incomplete; do not claim or invent it.

Run the focused task tests on a fresh disposable PostgreSQL database migrated to the single Alembic head, named regression tests, syntax compilation, and `git diff --check`. Record failures and corrections. Request one independent read-only review of the changed source/tests; the reviewer must not edit, run tests, or access the database. Remove only the exact task-owned disposable database/container and verify it is gone. Commit only task-owned source, tests, and evidence; suppress GitHub Actions using `[skip ci]`. Never run GitHub Actions for M20 through 2026-10-30.

Do not modify `TASKS.md` in implementation unless following the user's explicit queue-maintenance authorization. Do not stage or alter unrelated local owner work. Do not claim production, real-factory, live supplier, payment, AP/GL, or external-provider acceptance.
