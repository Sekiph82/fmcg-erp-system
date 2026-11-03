# M34.S02.T004 Disposable PostgreSQL Verification V03

- Database: `fmcg_m34_s02_t004_42c4af4386d544f0b89519af` (passwordless loopback, task-owned disposable PostgreSQL 16 container).
- Alembic: fresh database upgraded to `20261030_0010 (head)`; no schema migration was needed for this task because `consumed_quantity` and the release-order link already exist.
- Focused tests: `2 passed`; the integration test includes accepted/rejected receipt splits, overreceipt rejection, repeated-post protection, and concurrent receipt posting against two distinct purchase orders for one BPA.
- Final BPA quantity: 30.000 accepted units consumed; zero units remain reserved after the three release orders are received. Audit snapshots recorded running totals 10.000, 15.000, 22.000, and 30.000.
- Cleanup: runner verified the uniquely named task container was absent after completion.
- Transcript SHA-256: `2264B559DE64E4470B410CC3853098B6B2F8A99E51AEE88350DF55042DDB0177` (`disposable-postgres-run-V03.log`).
- Committed normalized transcript SHA-256: `AFF150A2A553B063328E300844BCE7B50521A66D6C5A1013A21FB6AD2FC023F8` (`disposable-postgres-transcript-V03-normalized.log`; trailing whitespace only was removed for `git diff --check`).
- Command-output SHA-256: `829BD9EE6D09672E736B0AA464A061546B8B41AE1FEA12CD3EB67F937F25B8C2` (`disposable-postgres-command-output-V03.log`).

The runner uses synthetic supplier, product, warehouse, PO, and receipt data and removes the disposable container on completion.
