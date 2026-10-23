# M20.S02.T002 — demand and dated supply closeout

## Scope and implementation

MPS demand projection now reconciles exact-warehouse on-hand and reserved inventory with confirmed sales demand, approved forecasts, and dated open supply. It carries available stock across daily receipts and demand, then calculates the period's production requirement against the source MRP safety-stock target. Forecast quantities retain the existing rounded MPS-period totals while being distributed across dates, so dated netting does not shift quantity across a period boundary. Largest-remainder allocation conserves rounded quantities without producing negative daily remainders; a positive amount with no allocation weights fails closed.

Open purchase orders use only the unreceived ordered quantity and convert to the product UOM. A branch PO is assigned only when that branch has one active warehouse; a company-only PO is assigned only when the company has one active warehouse. Ambiguous destinations, overdue receipts, and receipts beyond the plan horizon are returned with explicit exclusion reasons rather than guessed or double-counted. WIP and other approved MPS supply are warehouse-scoped; MPS supply linked to a production order is excluded to prevent counting the same supply twice. The API response and frontend TypeScript contract include dated supply breakdowns and excluded purchase orders.

The new PostgreSQL fixture uses synthetic companies, branches, warehouses, products, orders, purchase orders, WIP, UOM conversion, and approved MPS plans. It verifies warehouse/company isolation, reservation netting, delayed receipts against earlier demand, unambiguous and ambiguous PO destinations, UOM conversion and fail-closed behavior, WIP/MPS warehouse scoping, released-order double-count protection, and validation before existing plan lines are replaced.

## Verification

- A fresh PostgreSQL 16 task-owned Docker container used a random `fmcg_m20_t002_<20-32 hex>` database name, loopback-only published port, and `tmpfs` data directory. Alembic migrations reached head before the PostgreSQL integration suites ran. The temporary password was not recorded; the container and database were removed after the run.
- MPS PostgreSQL and regression suites (`test_m20_v03_acceptance.py`, `test_m20_remaining_engine.py`, `test_m20_s01_t001_v02_mps_remediation.py`, `test_mps_sequences.py`) — **67 passed, 68 warnings in 21.45s** on the final code.
- `python -m pytest backend/tests/test_m20_remaining_engine.py -q` — **28 passed in 2.00s** on the final code.
- `python -m py_compile backend/app/services/mps_advanced_service.py backend/tests/test_m20_v03_acceptance.py` — passed.
- `npm run type-check --prefix frontend` — passed.
- `git diff --check` — passed.

The PostgreSQL suite warnings are existing Pydantic v2 and Starlette/httpx deprecations. They were not suppressed or counted as failures. The test command used Python's Windows selector event loop for the async PostgreSQL driver; the repository migrations and tests ran against the disposable database.

## Independent review and limits

An independent read-only code review checked warehouse stock, PO company/branch assignment, UOM/date handling, WIP, existing MPS supply, receipt sequencing, response breakdown consistency, and allocation edge cases. The reviewer found small-quantity rounding edge cases; the allocator now uses nonnegative largest-remainder distribution and rejects positive allocations without weights. The final review reported no concrete defects and did not run tests or access a database.

The current purchase-order schema does not always identify a unique destination warehouse. Those open POs remain visible in the response with `PURCHASE_ORDER_DESTINATION_AMBIGUOUS` and are excluded from supply until their destination is explicit. No owner database, business records, credentials, GitHub Actions, push, or merge were used in verification.
