# M07.S03.T001 — Configured order-to-cash posting closure criteria V02

## Authority and assumptions

The exact task is `M07.S03.T001 — Verify order-to-cash accounting closure` in root `TASKS.md`. This version extends V01 after the owner directed that missing but safely assumable workflow behavior be implemented with virtual/synthetic fixtures.

Use the existing `AccountingPostingRule` records as the only account mapping authority. Implement the ordinary configured posting flow without creating default chart accounts, account codes, or assumed production mappings. This is a software configuration model; synthetic accounts/rules in the isolated test database are not owner or factory data.

Posting semantics for the implemented flow:

- Invoice `SALES_INVOICE_ISSUED`: debit the configured receivables asset account by persisted invoice total; credit the configured revenue account by persisted subtotal; credit the configured tax liability account by persisted tax amount when non-zero.
- Customer payment `CUSTOMER_PAYMENT_RECEIVED_CASH`, `..._BANK`, or `..._MPESA`: debit the method-specific configured clearing account and credit the same receivables asset account debited by the source invoice.
- A missing/ambiguous-required account mapping, inactive/non-postable account, closed posting period, or unbalanced entry must prevent the source transaction from being committed. Do not invent fallback accounts.
- Event, batch, journal, and source record writes share the caller's database transaction. Idempotency uses the existing operational-posting event/batch infrastructure. Keep the existing period behavior (`require_period=False`); closed periods still reject posting.
- Reject non-positive payments and payments greater than the locked invoice outstanding balance. Keep cash/bank/mpesa as the supported method set; do not imply a bank or payment-provider integration exists.

## Acceptance evidence

1. Trace and test confirmation → allocation → dispatch/stock issue → invoice → partial/final customer payment.
2. Prove that configured synthetic invoice, cash, bank, and M-Pesa rules create balanced `POSTED` journals with the exact configured account IDs, linked `POSTED` operational events and posting batches, and the same receivables account across invoice and receipts.
3. Exercise both customer payment API routes, including method propagation. Prove a missing channel rule, mismatched receivables mapping, and overpayment fail before the payment or invoice balance persists; verify source transactions remain unchanged after rollback.
4. Exercise fractional-cent invoice components and prove line subtotals, line taxes, invoice amounts, and the journal remain balanced at the configured 2-decimal invoice currency precision.
5. Keep the test strictly limited to a fresh loopback PostgreSQL database named `fmcg_m07_s03_t001_<20-32 lowercase hex>`, no password, and opt-in `M07_S03_T001_DISPOSABLE_TEST_DATABASE=1` plus exact database-name variable.
6. Run this integration test with applicable GAP-001/GAP-002 regressions, Python compile and `git diff --check`. Do not run GitHub Actions.
7. Use one independent source/evidence reviewer who does not edit, run tests, or access the database. Remove the exact task-owned container and verify absence.

## Boundaries

This closes the configured software path in the synthetic environment. It does not prove owner chart-of-account configuration, statutory tax treatment, payment-provider settlement, authorization in a live business, or real factory acceptance. Preserve any audit findings outside this exact path, including payment allocation, dunning, credit notes, and production use.
