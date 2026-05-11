# GAP-001 Accounting Core Implementation Notes

## Scope Completed

This note covers `GAP-001A` through `GAP-001J` for Enterprise-Grade Accounting Core Depth.

Implemented foundation areas:

- accounting core audit and schema design
- additive Alembic migration for fiscal years, posting controls, recurring journals, payment allocation, and currency revaluation
- matching SQLAlchemy ORM models
- matching Pydantic schemas
- service-layer helpers for journal validation, period/fiscal-year posting guards, posting account checks, posting state changes, reversal draft creation, and idempotent posting batches
- protected finance API endpoints for accounting controls
- frontend Accounting Controls page
- `finance.configure` permission for accounting setup and posting-rule configuration
- focused backend tests for routes, permission registry/seed, schemas, and journal validation

## Backend Paths

| Area | Path |
|---|---|
| Migration | `backend/alembic/versions/20260511_0010_enterprise_accounting_core.py` |
| ORM models | `backend/app/models/finance.py` |
| Pydantic schemas | `backend/app/schemas/finance.py` |
| Service helpers | `backend/app/services/finance_service.py` |
| API endpoints | `backend/app/api/v1/endpoints/finance.py` |
| Permission registry | `backend/app/core/module_registry.py` |
| Seed permissions/roles | `backend/app/db/seed.py` |
| Tests | `backend/tests/test_gap001_accounting_core.py` |

## Frontend Paths

| Area | Path |
|---|---|
| Finance API client | `frontend/src/lib/finance.ts` |
| Accounting dashboard link | `frontend/src/app/dashboard/finance/accounting/page.tsx` |
| Accounting Controls page | `frontend/src/app/dashboard/finance/accounting/controls/page.tsx` |
| Sidebar navigation | `frontend/src/components/nav-config.tsx` |

## New Permission

`finance.configure` is used for sensitive accounting setup surfaces:

- fiscal-year creation
- accounting-period creation
- period close-check configuration
- recurring journal template creation
- posting-rule creation
- Accounting Controls sidebar visibility

The permission is granted to:

- `cfo`
- `finance_manager`

Finance reports and read-only accounting lists remain protected by `finance.view`. Journal posting and reversal remain protected by `finance.approve`.

## API Surface Added

| Method | Path | Permission |
|---|---|---|
| `POST` | `/api/v1/finance/journal/{entry_id}/reverse` | `finance.approve` |
| `GET` | `/api/v1/finance/accounting/fiscal-years/` | `finance.view` |
| `POST` | `/api/v1/finance/accounting/fiscal-years/` | `finance.configure` |
| `GET` | `/api/v1/finance/accounting/period-close-checks/` | `finance.view` |
| `POST` | `/api/v1/finance/accounting/period-close-checks/` | `finance.configure` |
| `PATCH` | `/api/v1/finance/accounting/period-close-checks/{check_id}` | `finance.configure` |
| `GET` | `/api/v1/finance/accounting/recurring-journals/` | `finance.view` |
| `POST` | `/api/v1/finance/accounting/recurring-journals/` | `finance.configure` |
| `GET` | `/api/v1/finance/accounting/posting-batches/` | `finance.view` |
| `GET` | `/api/v1/finance/accounting/posting-rules/` | `finance.view` |
| `POST` | `/api/v1/finance/accounting/posting-rules/` | `finance.configure` |
| `GET` | `/api/v1/finance/accounting/payment-allocations/` | `finance.view` |
| `POST` | `/api/v1/finance/accounting/payment-allocations/` | `finance.create` |
| `GET` | `/api/v1/finance/accounting/currency-revaluations/` | `finance.view` |
| `POST` | `/api/v1/finance/accounting/currency-revaluations/` | `finance.create` |

## Verification Completed

- Alembic revision compiles.
- Alembic recognizes `20260511_0010` as the head.
- Alembic offline SQL generation passed.
- Finance models, schemas, services, and endpoints compile/import.
- Frontend TypeScript type-check passed with `npm.cmd run type-check`.
- Focused GAP-001 backend tests passed with `backend/venv/Scripts/python.exe -m pytest backend/tests/test_gap001_accounting_core.py -q`.

## Remaining Verification

Live migration verification is still pending because Docker/PostgreSQL was not running in this session.

Run later:

```powershell
cd backend
alembic upgrade head
```

or run through the normal Docker-backed startup flow once Docker Desktop is available.

## Remaining GAP-001 Work

The foundation is not yet a complete production accounting suite. Remaining follow-up work includes:

- deeper endpoint tests for database-backed create/post/reverse flows
- frontend workflow tests for Accounting Controls
- AR/AP aging pages and services
- cash-flow statement service and page
- automatic subledger posting integration from inventory, manufacturing, sales, procurement, tax, landed cost, and fixed assets
- final production migration verification against live PostgreSQL
