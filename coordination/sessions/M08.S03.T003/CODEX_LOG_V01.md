# M08.S03.T003 — Implementation Log V01

## Scope

Verify and close the production, finished-goods quality, traceability, and production-costing paths exercised by the baseline integrity task. The root `TASKS.md` row is the authoritative task scope; it does not include a separate task-specific acceptance prompt. The existing GAP-002 audit is the applicable finance-integration boundary reference.

## Changes

- Production completion now requires a finished-goods lot identifier. Required recipe inputs must resolve to explicitly selected lots, or to a single unambiguous eligible lot; ambiguous multi-lot inputs fail closed. Consumed source lots are recorded in material consumption and stock movement rows, with source-to-finished-goods genealogy recorded in the same transaction.
- Completion creates a mandatory finished-goods inspection linked to the receipt's actual stock lot and immediately quarantines its inventory. QC acceptance rejects failed, incomplete, or empty mandatory result sets. A quarantined lot can be released only after a passed and accepted inspection, and only while its stock rows still exist.
- Production cost rollup rejects unfinished orders, serializes concurrent rollups by locking and refreshing the production order, and replaces only its own auto-derived entries while retaining manual cost entries.
- Production costing read endpoints require `finance.view`; finalization requires `finance.create`.
- Added T003 verification coverage and updated the T002 production/inventory regression expectations for the new finished-goods QC hold.

## Verification

Baseline source revision before these uncommitted changes: `e88fb32d5cfcba020be560d54016e4e8d76169ec` (`main`, matched `origin/main` at start of task).

Commands run in the canonical checkout:

1. Fresh disposable PostgreSQL 16 test database, Alembic upgrade to `20261029_0025 (head)`, then `M08_S03_T003_DISPOSABLE_TEST_DATABASE=1` focused T003 suite: **26 passed**.
2. Separate disposable database on the same task-owned PostgreSQL container, Alembic upgrade to `20261029_0025 (head)`, then the T002 atomicity regression suite: **5 passed**.
3. `python -m pytest tests/test_m08_s03_t003_qc_finance_closure.py tests/test_production_cost_yield_variance.py -q`: **27 passed, 7 skipped**. The skips are the deliberately database-gated cases; those were exercised in the disposable PostgreSQL run above.
4. `python -m compileall -q` over the changed application modules and both task test files: **passed**.
5. `git diff --check`: **passed**.
6. Verified the task-owned `fmcg-m08-s03-t003-*` container was removed after the run.

All database fixtures used synthetic rows in disposable local databases. No owner, factory, provider, or production data was used.

## Independent review

A separate read-only review identified gaps in production-to-QC lot linkage and quarantine, source-lot genealogy, and safe/idempotent costing rollup under incomplete orders and concurrent requests. Those findings were addressed by the changes above. This implementation log is not an independent audit verdict.

## Boundaries and remaining work

- This task does not implement automatic GL posting, an organization-wide inventory valuation policy, or accounting-period enforcement across production events. The current [GAP-002 posting integration audit](../../../docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md) records those as separate open integration gaps. No COA mapping or account policy was invented, and no claim is made that GAP-002 is closed.
- No schema migration was required. The database verification confirms this task against the current migration head only.
- Live factory processes, physical QC equipment, real operators, and external credentials/providers were not available or represented; synthetic tests do not constitute live operational acceptance.

## Changed implementation files

- `backend/app/services/production_service.py`
- `backend/app/services/quality_service.py`
- `backend/app/services/finance_service.py`
- `backend/app/api/v1/endpoints/production_costing.py`
- `backend/app/api/v1/endpoints/quality.py`
- `backend/app/schemas/production.py`
- `backend/tests/test_m08_s03_t003_qc_finance_closure.py`
- `backend/tests/test_m08_s03_t002_production_inventory_atomicity_db.py`
