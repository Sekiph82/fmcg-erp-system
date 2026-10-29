# M07.S03.T001 — Implementation prompt V01

Verify only `M07.S03.T001 — Verify order-to-cash accounting closure` from root `TASKS.md`, using `CHATGPT_AUDIT_CRITERIA_V01.md` in this session directory.

Read the latest applicable GAP-001, GAP-002 and GAP-004 audits. Trace the current SalesOrder → Shipment/stock issue → Invoice → Customer Payment source path and determine whether each financial source creates an operational posting event/batch and a balanced posted journal with source linkage. Do not treat invoice/payment status updates as GL closure.

Add a task-specific guarded PostgreSQL test for the existing synthetic order-to-payment subledger path. Require an empty password, loopback database, exact `fmcg_m07_s03_t001_<20-32 lowercase hex>` database name, `M07_S03_T001_DISPOSABLE_TEST_DATABASE=1` and a matching database-name variable. Run only against a fresh task-owned disposable PostgreSQL database, then run relevant GAP-001/GAP-002 tests, Python compile and `git diff --check`.

Use one independent source/evidence reviewer who does not edit, run tests or access the DB. Remove the exact task-owned container and verify it is absent. If the present code lacks automatic AR/revenue/tax journal posting, record the result as `NOT CLOSED` and preserve the precise GAP audit limits. Do not invent account codes, account mappings, tax or payment-clearing policy, or claim production/owner-data acceptance. Publish only task-owned files with `[skip ci]` after safe fetch/divergence checks; do not run GitHub Actions.
