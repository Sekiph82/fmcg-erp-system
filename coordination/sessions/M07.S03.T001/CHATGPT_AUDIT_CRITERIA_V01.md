# M07.S03.T001 — Order-to-cash accounting closure verification criteria V01

## Authority and scope

The exact task is `M07.S03.T001 — Verify order-to-cash accounting closure` in root `TASKS.md`. No task-specific acceptance artifact exists yet. Applicable audits are `GAP-001_ACCOUNTING_CORE_AUDIT.md`, `GAP-002_POSTING_INTEGRATION_AUDIT.md`, and `GAP-004_E2E_WORKFLOW_TESTING_AUDIT.md`.

This is a baseline verification checkpoint. Its result must say whether the current order-to-cash chain closes through the general ledger. A verified gap is a negative finding; do not claim the accounting chain is complete just because the operational subledger works.

> Superseded for implementation scope by 'CHATGPT_AUDIT_CRITERIA_V02.md' after the owner directed that the safe, configurable software flow be implemented using virtual/synthetic assumptions. V02 preserves the no-fabricated-production-mapping boundary.

## Required verification

1. Trace the current sales path from a confirmed order through dispatch/stock issue, invoice creation, and customer payment. Record lifecycle states, source links, transaction behavior, permissions and persisted amounts.
2. Inspect whether issued invoices and customer payments create auditable posting events/batches and balanced posted journals, and whether journal links/statuses are reachable from the source records.
3. Add a task-specific synthetic PostgreSQL integration test proving the existing order/dispatch/invoice/payment operational subledger path. It must use a strict loopback-only disposable-database guard with task prefix `fmcg_m07_s03_t001_` and opt-in `M07_S03_T001_DISPOSABLE_TEST_DATABASE=1`.
4. Run relevant GAP-001/GAP-002 regressions, Python compile and `git diff --check`. Do not run GitHub Actions.
5. Use one independent source/evidence reviewer. Reviewer is read-only and must not run tests or access the database.
6. Remove the exact disposable container and verify it is absent.

## Scope and evidence boundaries

- This task verifies whether the current accounting chain is closed; it does not by itself authorize inventing or hard-coding account mappings, tax policy, payment-channel clearing accounts, or new posting approval rules.
- Use synthetic records only. Do not touch owner data or create real journal records.
- If invoice/payment processing reaches only the operational subledger, report the task verification complete with the closure result explicitly `NOT CLOSED`; do not record a green accounting completion.
- Preserve GAP-001/GAP-002 findings about missing automatic AR/revenue/tax integration and incomplete payment allocation. A local database test is not production or owner-data acceptance.

## Closure evidence

Record source/test lineage, baseline and fetched SHAs, exact test commands/results, PostgreSQL version and revision, database guard/cleanup, independent review, changed files and commit/push state in `CODEX_LOG_V01.md`.
