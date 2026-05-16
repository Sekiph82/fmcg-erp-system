# GAP-025 Multi-Company / Multi-Branch / Franchise Scaling — Schema Design

## Objectives

1. Promote `company` from `EndpointRouteDefinition` to `ModuleDefinition` with full permission_actions.
2. Replace mixed `admin.manage` / bare `get_current_user` endpoint guards with `company.*` guards.
3. Add `company_id` (nullable FK) to `warehouses` table for branch-level inventory isolation.
4. Add user-company membership check on read endpoints (own company only, unless company.view granted).
5. Add `RequirePermission` page guard to companies frontend page.
6. Add comprehensive permission tuples and role grants.
7. Add contract tests.

**Franchise model is out of scope** — no business requirements provided for franchise-specific fields. A future Franchise model would extend Branch or Company depending on the legal structure.

## Permission Family

| Action | Code | Purpose | Public |
|---|---|---|---|
| view | company.view | List and inspect companies user has access to | False |
| create | company.create | Create a new company entity | False |
| edit | company.edit | Update company details and branch details | False |
| delete | company.delete | Soft-delete a company or branch | False |
| export | company.export | Export company summary or user access reports | False |
| manage | company.manage | Full company admin — grant/revoke user access, set defaults | False |

`manage` supersedes edit/delete and is required for user access grants/revocations.

## Module Registry Update

Change `company` from `EndpointRouteDefinition` to `ModuleDefinition`:

```python
ModuleDefinition(
    key="company",
    label="Company & Branches",
    route_prefix="/companies",
    import_path="app.api.v1.endpoints.company",
    permission_actions=("view", "create", "edit", "delete", "export", "manage"),
    sidebar_group="Administration",
    icon_key="building",
    ai_mode=AIMode.RULE_BASED,
    critical=True,
)
```

## Endpoint Guard Mapping

| Endpoint | Old Guard | New Guard |
|---|---|---|
| GET /companies/ | get_current_user | company.view |
| POST /companies/ | admin.manage | company.create |
| GET /companies/{id}/ | get_current_user | company.view |
| PATCH /companies/{id}/ | admin.manage | company.edit |
| POST /companies/{id}/set-default | get_current_user | company.view (own context) |
| GET /companies/{id}/branches/ | get_current_user | company.view |
| POST /companies/{id}/branches/ | admin.manage | company.edit |
| PATCH /companies/{id}/branches/{bid}/ | admin.manage | company.edit |
| GET /companies/{id}/users/ | get_current_user | company.manage |
| POST /companies/{id}/users/ | admin.manage | company.manage |
| DELETE /companies/{id}/users/{uid}/ | admin.manage | company.manage |
| GET /companies/{id}/summary/ | get_current_user | company.view |

## Ownership Check

Read endpoints (`GET /companies/`, `GET /companies/{id}/`) should only return companies
where the requesting user has a `UserCompanyAccess` record (or user has `company.view` with admin-level scope).

Implementation: Add `_check_company_access(db, user_id, company_id)` helper that queries `UserCompanyAccess`.
Raise 403 if no access row found and user lacks superuser or broad company scope.

## Warehouse Multi-Tenancy

Add nullable `company_id` and `branch_id` to `warehouses` table.

```sql
ALTER TABLE warehouses ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE warehouses ADD COLUMN branch_id  UUID REFERENCES branches(id)  ON DELETE SET NULL;
```

Both nullable: existing warehouses remain functional. New warehouses should supply company_id.
Index on `(company_id)` for filtered queries.

ORM update (`backend/app/models/master.py`):
```python
company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
branch_id  = Column(UUID(as_uuid=True), ForeignKey("branches.id",  ondelete="SET NULL"), nullable=True, index=True)
```

## Role Grants

| Role | Permissions |
|---|---|
| owner | wildcard — all |
| admin | company.view, company.create, company.edit, company.delete, company.export, company.manage |
| company_admin | company.view, company.edit, company.manage |
| ceo | company.view, company.export |
| coo | company.view |
| cto | company.view |

`company_admin` role already exists in seed — update its grants.

## Migration Strategy

- Single additive reconciliation migration: `20260516_0050_multi_company_warehouse_reconciliation.py`.
- Adds `company_id` and `branch_id` nullable columns to `warehouses` table only.
- Uses `_has_column()` guard to detect if columns already exist.
- No changes to `companies`, `branches`, `user_company_access` tables (already exist in initial schema).

## Frontend Guard

Add `RequirePermission permission="company.view"` to `frontend/src/app/dashboard/companies/page.tsx`.

No new pages needed for this GAP. Branch management is inline in the company page.

## Files to Change

| File | Change |
|---|---|
| `backend/alembic/versions/20260516_0050_*` | New migration — warehouses.company_id/branch_id |
| `backend/app/models/master.py` | Warehouse model: add company_id, branch_id |
| `backend/app/core/module_registry.py` | Promote company to ModuleDefinition |
| `backend/app/db/seed.py` | Add 5 new company.* permission tuples; update role grants |
| `backend/app/api/v1/endpoints/company.py` | Replace all guards; add ownership helper |
| `frontend/src/app/dashboard/companies/page.tsx` | Add RequirePermission guard |
| `backend/tests/test_gap025_multi_company_branch.py` | New test file |
