# GAP-025 Multi-Company / Multi-Branch / Franchise Scaling — Audit

## Scope

Inspect current multi-company, multi-branch, and franchise implementation.
Identify gaps before schema design and implementation.

## What Exists

### ORM Models (`backend/app/models/company.py`)

| Model | Table | Key Fields | Notes |
|---|---|---|---|
| Company | companies | id, name, short_code, tax_pin, country, base_currency, is_default, is_active, logo_url | Full; soft-delete via is_active |
| Branch | branches | id, company_id (FK), name, branch_code, branch_type (FACTORY/WAREHOUSE/OFFICE/RETAIL), is_default, is_active | Unique(company_id, branch_code) |
| UserCompanyAccess | user_company_access | user_id (FK), company_id (FK), role (ADMIN/USER/VIEWER), is_default, granted_by_id | Multi-company user access |

**No Franchise model exists.**

### Endpoints (`backend/app/api/v1/endpoints/company.py`)

| Endpoint | Method | Guard |
|---|---|---|
| GET /companies/ | List all companies user has access to | bare get_current_user |
| POST /companies/ | Create company | require_permission("admin", "manage") |
| GET /companies/{id}/ | Get company details + branches + users | bare get_current_user |
| PATCH /companies/{id}/ | Update company | require_permission("admin", "manage") |
| POST /companies/{id}/set-default | Set default company | bare get_current_user |
| GET /companies/{id}/branches/ | List branches | bare get_current_user |
| POST /companies/{id}/branches/ | Create branch | require_permission("admin", "manage") |
| PATCH /companies/{id}/branches/{bid}/ | Update branch | require_permission("admin", "manage") |
| GET /companies/{id}/users/ | List user access grants | bare get_current_user |
| POST /companies/{id}/users/ | Grant user access | require_permission("admin", "manage") |
| DELETE /companies/{id}/users/{uid}/ | Revoke user access | require_permission("admin", "manage") |
| GET /companies/{id}/summary/ | KPI summary (budgets, POs, SOs) | bare get_current_user |

**Permission guard problem:** Write ops use `require_permission("admin", "manage")` — unrelated to company module.
Read ops use bare `get_current_user` — no permission check at all.

### Module Registry

`company` is an `EndpointRouteDefinition` (line 486), NOT a `ModuleDefinition`.
No `permission_actions` defined. No module-level permission guards possible from registry.

### Permissions Seed

Only 1 tuple seeded:
```python
("company", "manage", "Manage Company Setup", "Manage company and branch setup", False)
```

No `company.view`, `company.create`, `company.edit`, `company.delete`, `company.export` tuples.
`company.manage` is in `company_admin` role only; admin role does not have it.

### Frontend (`frontend/src/app/dashboard/companies/page.tsx`)

- Single companies page exists: full CRUD for companies + branch creation + user access revocation
- No dedicated branch management UI beyond inline branch creation
- No franchise pages
- No `RequirePermission` guard on the companies page

### Schemas (`backend/app/schemas/company.py`)

| Schema | Fields |
|---|---|
| CompanyCreate | name, short_code, tax_pin, country, base_currency |
| CompanyRead | all fields + branch_count, user_count |
| CompanyUpdate | name, tax_pin, is_active, logo_url |
| BranchCreate/Read | name, branch_code, branch_type, is_default, address fields |
| UserAccessGrant/Read | user_id, role |
| CompanySummary | branch_count, user_count, total_budgeted, open_po_count, open_so_count |

Schemas are functional. No FranchiseCreate/Read exists.

### Multi-Tenancy in Data Models

Company/branch FK coverage across key modules:

| Module | company_id | branch_id | Notes |
|---|---|---|---|
| Sales (SalesOrder) | ✓ | ✓ | Present |
| Finance (Budget) | ✓ | ✓ | Present |
| Procurement (PurchaseOrder) | ✓ | ✓ | Present |
| HR (Employee) | ✓ | ✓ | Present |
| Inventory (Warehouse) | ✗ | ✗ | No company_id/branch_id — shared across tenants |
| Master (Product) | ✗ | — | Tenant-unaware; shared product catalog |

No automatic row-level security. Each endpoint must manually filter by company_id in WHERE clauses.
Endpoints in `company.py` do not verify that the requesting user has access to the requested company — the association check is implicit through UserCompanyAccess query.

### Migration Status

No dedicated company/branch Alembic version file exists in `backend/alembic/versions/`.
`companies`, `branches`, and `user_company_access` tables are created in the initial schema migration (pre-versioned in this worktree).

### Tests

No `backend/tests/test_gap025_*.py` or any test file for company/branch isolation.

## Gaps Summary

| # | Gap | Severity |
|---|---|---|
| 1 | Company endpoints use bare `get_current_user` for reads — no permission enforcement | High |
| 2 | Write endpoints use `require_permission("admin", "manage")` — wrong module, wrong action | High |
| 3 | `company` is EndpointRouteDefinition not ModuleDefinition — no permission_actions | High |
| 4 | Only 1 seed permission tuple (`company.manage`) — no view/create/edit/delete/export segregation | High |
| 5 | No `RequirePermission` guard on companies frontend page | High |
| 6 | Warehouse has no `company_id`/`branch_id` — inventory isolation impossible | Medium |
| 7 | Product is tenant-unaware (shared master data) | Medium |
| 8 | No Franchise model, endpoints, schemas, or UI | Medium |
| 9 | No user-company access ownership check in endpoints (any auth'd user can read any company) | Medium |
| 10 | No migration for company/branch in versioned migration chain | Low |
| 11 | No tests for company/branch/multi-tenant isolation | Medium |

## Recommended Implementation Sequence

- **GAP-025B** — Schema design: permission family, module promotion, role grants, Warehouse multi-tenancy fields
- **GAP-025C** — Alembic reconciliation migration (Warehouse company_id/branch_id columns only; company/branch tables already exist in initial schema)
- **GAP-025D** — Update Warehouse ORM model to add company_id/branch_id
- **GAP-025E** — Expand schemas: company/branch permission-aware schemas if needed, FranchiseCreate stub
- **GAP-025F** — No new service layer needed; verify user-company ownership check in endpoint helper
- **GAP-025G** — Fix endpoint guards: promote `company` to `ModuleDefinition`, replace `admin.manage` with `company.*` guards, add ownership check on read endpoints
- **GAP-025H** — Add `RequirePermission` guard to companies frontend page; add branch management subpage
- **GAP-025I** — Add `company.view/create/edit/delete/export` permission tuples + role grants
- **GAP-025J** — Create `backend/tests/test_gap025_multi_company_branch.py`
- **GAP-025K** — Implementation notes doc
- **GAP-025L** — Final checks, update TASKS.md + CODEX_PROGRESS.md
