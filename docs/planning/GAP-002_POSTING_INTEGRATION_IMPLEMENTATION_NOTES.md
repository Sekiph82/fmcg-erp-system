# GAP-002 Posting Integration Implementation Notes

## Task

`GAP-002K: Add or update documentation: Accounting-to-Inventory-to-Manufacturing Posting Integration`

## Implemented Scope

GAP-002 now has the foundation needed to connect operational inventory events to finance postings:

- audit document: `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`
- schema design: `docs/planning/GAP-002_POSTING_INTEGRATION_SCHEMA_DESIGN.md`
- additive Alembic migration: `backend/alembic/versions/20260511_0020_operational_posting_integration.py`
- ORM models and posting-link fields across finance, inventory, procurement, production, and landed-cost models
- Pydantic schemas for operational posting events, account mappings, and posting-link read fields
- finance service helpers for idempotency, mapping lookup, event creation, posting-link application, posted state, and failed state
- protected finance API endpoints for posting-event audit reads and inventory account mapping configuration
- Accounting Controls UI support for operational posting events and inventory account mappings
- focused backend tests in `backend/tests/test_gap002_posting_integration.py`

## What This Enables

Finance and operations now have a shared foundation for:

- linking `StockMovement`, GRN lines, material consumptions, finished-goods receipts, and landed-cost rows to posting batches and journals
- recording line-level operational posting events with idempotency keys
- configuring inventory, WIP, finished-goods, GRNI, landed-cost clearing, variance, and scrap accounts
- exposing posting audit records to finance users through API/UI
- blocking future GL posting service calls through accounting-period checks
- recording safe failure states instead of silently losing posting errors

## Important Current Limit

This implementation does not yet automatically post GL entries from live operational workflows.

The following flows still need final integration in later GAP-002 tasks or follow-up hardening:

- GRN posting should call the operational posting service and create Dr Inventory / Cr GRNI journals.
- Supplier invoice posting should clear GRNI to AP/tax accounts.
- Production material issue should post Dr WIP / Cr raw material inventory.
- Finished goods receipt should post Dr finished goods inventory / Cr WIP.
- Landed cost posting should link allocation and inventory adjustment rows to GL impact.
- Reversal/cancellation flows should create linked operational posting reversal events and journal reversals.

The current UI is therefore intentionally labeled and structured as audit/configuration support, not a claim that every operational workflow is already auto-posting to GL.

## API Endpoints Added

All endpoints are under the existing finance router.

| Endpoint | Permission | Purpose |
|---|---|---|
| `GET /api/v1/finance/accounting/operational-posting-events/` | `finance.view` | List operational posting audit events. |
| `GET /api/v1/finance/accounting/operational-posting-events/{event_id}` | `finance.view` | Inspect one posting event. |
| `GET /api/v1/finance/accounting/inventory-account-mappings/` | `finance.view` | List inventory account mappings. |
| `POST /api/v1/finance/accounting/inventory-account-mappings/` | `finance.configure` | Create an account mapping. |
| `PATCH /api/v1/finance/accounting/inventory-account-mappings/{mapping_id}` | `finance.configure` | Update an account mapping. |

No unsafe execute endpoint was added.

## Frontend Path

Operational posting controls were added to:

`frontend/src/app/dashboard/finance/accounting/controls/page.tsx`

The page now shows:

- inventory account mapping creation/listing
- operational posting event audit list
- existing fiscal-year, posting-rule, posting-batch, allocation, and currency revaluation controls

## Permissions

No new permission code was required.

- Posting event audit reads use `finance.view`.
- Account mapping writes use `finance.configure`.
- The finance module registry already includes `configure`.
- Seeded CFO and finance manager role templates already include `finance.configure`.

## Verification Commands Run

```powershell
python -m py_compile backend/alembic/versions/20260511_0020_operational_posting_integration.py
.\venv\Scripts\python.exe -m alembic heads
.\venv\Scripts\python.exe -m alembic history -r 20260511_0010:20260511_0020
.\venv\Scripts\python.exe -m alembic upgrade 20260511_0010:head --sql
python -m py_compile backend/app/models/finance.py backend/app/models/inventory.py backend/app/models/procurement.py backend/app/models/production.py backend/app/models/landed_cost.py backend/app/models/__init__.py
python -m py_compile backend/app/schemas/finance.py backend/app/schemas/inventory.py backend/app/schemas/procurement.py backend/app/schemas/production.py backend/app/schemas/landed_cost.py
python -m py_compile backend/app/services/finance_service.py
python -m py_compile backend/app/api/v1/endpoints/finance.py
npm.cmd run type-check
backend\venv\Scripts\python.exe -m pytest backend/tests/test_gap002_posting_integration.py -q
backend\venv\Scripts\python.exe -m pytest backend/tests/test_gap001_accounting_core.py backend/tests/test_gap002_posting_integration.py -q
```

## Known Blocker

Live `alembic upgrade head` could not be completed in this session because PostgreSQL refused the local connection:

`ConnectionRefusedError [WinError 1225]`

Rerun the live migration after Docker/PostgreSQL is available.

## Next Implementation Direction

The next safe work should keep moving in this order:

1. Run live Alembic upgrade against a running development database.
2. Add tests for the protected API endpoints with dependency overrides.
3. Wire GRN posting to create a posting event and draft/posted journal through the service helper.
4. Wire production material issue and finished-goods receipt in separate small slices.
5. Wire landed-cost allocation posting.
6. Add reversal/cancellation posting flows after forward posting is stable.

