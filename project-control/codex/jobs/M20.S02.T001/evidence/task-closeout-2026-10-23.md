# M20.S02.T001 — demand input projection closeout

## Scope and implementation

The MPS demand projection now reads only approved, warehouse-scoped forecast inputs when the source MRP run enables forecasts. Confirmed open sales-order quantities are netted against forecast within each planning bucket; cancelled orders and shipped quantities are excluded from open demand. When multiple approved forecast headers overlap for the same product and warehouse, projection stops before replacing plan lines because no forecast-selection precedence is defined.

The projection uses the source MRP run's safety-stock snapshot and honors its safety-stock toggle. A safety-only product can create a replenishment line, but inactive products are excluded from that path. Period-end inventory carries forward after subtracting confirmed and non-overlapping forecast consumption; the safety target is retained as an ending-stock target rather than treated as consumption.

The PostgreSQL fixture uses synthetic orders, forecasts, products, and MRP results. It covers confirmed/forecast netting across weekly buckets, partial shipment, cancellation, draft forecast exclusion, disabled forecast and safety-stock toggles, source safety-stock snapshots, safety-only replenishment, inactive-product exclusion, and fail-closed overlapping forecasts.

## Verification

- A task-owned PostgreSQL 16 Docker container was created for this run with a loopback-only published port and a `tmpfs` data directory. A fresh random database name used the required `fmcg_m20_t001_<20-32 hex>` format; migrations were applied to Alembic head before tests. The generated password was not retained or reported, and the container was removed after the run.
- `python -m pytest tests/test_m20_v03_acceptance.py tests/test_m20_remaining_engine.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_mps_sequences.py -q` from `backend/` — **65 passed, 68 warnings in 15.23s**.
- `python -m pytest backend/tests/test_m20_remaining_engine.py -q` — **27 passed in 1.96s**.
- `python -m py_compile backend/app/services/mps_advanced_service.py backend/tests/test_m20_v03_acceptance.py` — passed.
- `git diff --check` — passed.

The warnings were existing Pydantic and Starlette/httpx deprecations. They were not suppressed or counted as test failures.

## Independent review and limits

An independent read-only review found and reported an inactive-product regression in the safety-only selection path. That defect was fixed by joining the MRP safety candidates to active products, and a regression case now asserts an inactive safety-only product creates no MPS line. The reviewer re-read the fix and toggle coverage and reported no further concrete high-risk defects. The reviewer did not access a database or run tests.

Overlapping approved forecasts deliberately fail closed because this task's sources do not establish which forecast model should win. Choosing a preferred forecast model remains a business policy question if automatic selection is required.

No owner database or business records were used. GitHub Actions were not run.
