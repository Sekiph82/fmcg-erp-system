# M13.S03.T001 — Landed-cost posting chain acceptance criteria V01

## Authority and baseline

The exact task is `M13.S03.T001 — Verify landed-cost posting chain` in root `TASKS.md`. The latest applicable repository audit found that allocation rows and `LCInventoryAdjustment` records exist, but reliable inventory valuation updates and GL links were missing: `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md` and `docs/planning/GAP-001_ACCOUNTING_CORE_AUDIT.md`.

## Acceptance

1. Use only a uniquely named task-owned loopback PostgreSQL database and synthetic company, supplier, GRN, material, cost layer, accounts, and posting configuration. Require an exact task opt-in before database writes. Do not access production, owner, or live provider records.
2. Exercise the actual landed-cost API/service flow: create a document and cost line, link a posted synthetic GRN, allocate, post, then inspect inventory valuation, journal, posting batch and source links in PostgreSQL. Multi-line rounding must omit zero-value allocation rows and preserve the exact cost total so they cannot block a valid posting.
3. Reuse configured `InventoryAccountMapping` accounts and valuation method. A mapping for a different material/product/category must never win merely because its stock type matches. Do not hardcode production account IDs or account codes. If the required inventory/clearing/expense mapping or source cost layer is absent, fail closed without leaving the header or allocations partially posted.
4. For the configured FIFO receipt layer, capitalize the allocated unit cost to that receipt's remaining cost layer, preserve stock quantity, and store before/after values on `LCInventoryAdjustment`. Any amount attributable to already-consumed quantity must be accounted to configured COGS; if the mapping is absent, fail closed. For a non-capitalizable charge, `LandedCostLine.account_code` must resolve to an active, postable `EXPENSE` chart account; debit it and credit that receipt's configured landed-cost clearing account. Missing or invalid configuration fails closed.
4a. Negative cost/credit lines are not silently discarded. Until a separately configured landed-cost credit/reversal flow exists, reject a document containing a negative line before replacing allocations or posting any accounting state.
5. Create balanced, posted finance journal entries and idempotency batches for allocation lines; link the allocation and inventory-adjustment rows to their journal/batch. A repeated post must not duplicate valuation or GL impact.
6. Posting must require `finance.post` and an open accounting period covering the bill date. Missing/closed period and missing account mappings must leave all posting state and valuation unchanged.
7. Preserve transaction atomicity: any invalid line or failed journal validation must not leave cost layers, header, adjustment, allocation, batch, event or journal partially committed.
8. No schema migration is expected; reuse existing posting fields, `CostLayer`, `InventoryAccountMapping`, `AccountingPostingBatch`, and journal helpers. If the implementation requires changing an accounting policy beyond those configured fields, stop and record the exact decision needed.
9. Record exact commit, PostgreSQL version, migrations, final/failed test runs, permission and rollback outcomes, cleanup, and independent review in `CODEX_LOG_V01.md`. Do not claim live or production acceptance.
