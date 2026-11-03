# M34.S02.T003 Disposable PostgreSQL Verification V10

- Database: `fmcg_m34_s02_t003_1cb852b08b1644f8aa9c7ff7` (passwordless loopback, task-owned disposable PostgreSQL 16 container).
- Alembic: upgraded from the empty baseline through `20261030_0010`; downgraded to `20261030_0009`; upgraded back to `20261030_0010`.
- Focused tests: `3 passed in 5.24s`, including scoped draft call-off creation, commitment serialization after consumption, price-break locking while a release order exists, and duplicate PO-number conflict handling across two agreements.
- Schema check: `purchase_orders.bpa_id` foreign key references `blanket_purchase_agreements(id)` with `ON DELETE RESTRICT`.
- Cleanup: runner verified the uniquely named task container was absent after completion.
- Transcript SHA-256: `6724E1E340ED0B9F0F08742B0249E1BE50D0389CEE8D8D3172F0D7B865B5EC43` (`disposable-postgres-run-V10.log`).
- Committed normalized transcript SHA-256: `CCB3565B30BAA3309EA0FF3828A0AB7BD75D72E29AAF19B055C475D9E01F0022` (`disposable-postgres-transcript-V10-normalized.log`; only trailing whitespace was removed for `git diff --check`).
- Command-output SHA-256: `00C0EF2EB38834BF6ABE9BFC2F27A7147E03C343B9FC14C779844A493C85490E` (`disposable-postgres-command-output-V10.log`).

The earlier V08 attempt exposed a test expectation mismatch (`422` was the correct invalid commitment response); the test was corrected. V10 is the final run after the independent review findings were also addressed.
