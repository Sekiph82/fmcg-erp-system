# GAP-010 CRM / Sales Pipeline Schema Design

## Summary

GAP-010 should extend the existing Sales, CRM Pipeline, Quotation, Field Sales, and GAP-SEC-001 access-control foundations. It should not introduce a second CRM architecture.

The first implementation slice should be reconciliation-first and additive:

- keep the existing Sales/CRM/Quotation tables and APIs
- reconcile CRM territory migration ownership
- add explicit commercial scope fields to key customer/sales/quote/CRM records
- add response access hints for row-level UX
- add service helpers for view-vs-mutation scope decisions
- add endpoint authentication and scoped action enforcement

## Design Constraints

- Preserve existing `/api/v1/sales`, `/api/v1/crm`, and `/api/v1/quotes` paths.
- Preserve existing enum/status values unless a migration is required.
- Reuse GAP-SEC-001 helpers: `can_view_record`, `can_modify_record`, `can_view_scope`, `can_modify_scope`, and status-lock helpers.
- Use nullable additive columns to avoid destructive migration risk.
- Prefer relationship fields for company/branch/customer where the related tables already exist.
- Keep region/team/customer-group scopes compatible with the existing `AccessScope.scope_type` values:
  - `company`
  - `branch`
  - `sales_region`
  - `sales_team`
  - `customer_group`
  - `warehouse`
  - `assigned_customer`
- Do not hardcode role checks into frontend pages or endpoint bodies.

## Current Schema Findings

### Existing Tables / Live DB

Live development PostgreSQL currently reports these commercial tables:

- `crm_records`
- `crm_territories`
- `customers`
- `quotations`
- `sales_orders`

Live `crm_records` currently exposes:

- `assigned_team_id`
- `customer_id`
- `region_id`

Live `crm_territories` currently exposes:

- `id`
- `territory_code`
- `territory_name`
- `region`
- `parent_territory_id`
- `assigned_rep_ids`
- `active_flag`
- `notes`
- `created_at`
- `updated_at`

Commercial scope columns such as `company_id`, `branch_id`, `sales_team_id`, `customer_group_id`, and explicit quote approval fields are not currently present on `customers`, `sales_orders`, or `quotations`.

### Migration Ownership Risk

`backend/app/models/crm.py` defines `CRMTerritory` and `CRMRecord.territory_id`, and the live database has `crm_territories`, but source search did not find Alembic ownership for `crm_territories` or `crm_records.territory_id`.

GAP-010C should use an idempotent reconciliation migration, similar to GAP-008/GAP-009, so it can:

- create `crm_territories` if absent
- add `crm_records.territory_id` if absent
- create missing indexes/foreign keys if absent
- avoid failing on the current live database where the table already exists

## Proposed Data Model Changes

### Customers

Add nullable scope fields:

- `company_id` UUID FK to `companies.id`, nullable
- `branch_id` UUID FK to `branches.id`, nullable
- `sales_region_id` string, nullable
- `sales_team_id` string, nullable
- `customer_group_id` string, nullable

Keep existing:

- `region`
- `segment`
- `route_id`
- `distributor_id`

Reasoning:

- Existing `region` is useful and should remain for compatibility.
- `sales_region_id` allows a canonical scope identifier without breaking existing region text.
- `customer_group_id` supports customer-group ownership and future pricing/discount segmentation.
- `company_id` and `branch_id` align commercial records with multi-company access scopes and finance integration.

### Sales Orders

Add nullable scope/approval fields:

- `company_id` UUID FK to `companies.id`, nullable
- `branch_id` UUID FK to `branches.id`, nullable
- `sales_region_id` string, nullable
- `sales_team_id` string, nullable
- `customer_group_id` string, nullable
- `approval_status` string, nullable
- `discount_approval_required` boolean, default false
- `discount_approved_by_id` UUID FK to `users.id`, nullable
- `discount_approved_at` timestamp with timezone, nullable

Reasoning:

- Sales orders should inherit commercial scope from the customer at creation.
- Warehouse scope already exists through `warehouse_id`.
- Approval fields should remain lightweight until the global approval module is expanded.
- Core order status should remain `SOStatus`; approval status is a separate governance marker.

### Quotations

Add nullable scope/approval fields:

- `company_id` UUID FK to `companies.id`, nullable
- `branch_id` UUID FK to `branches.id`, nullable
- `sales_region_id` string, nullable
- `sales_team_id` string, nullable
- `customer_group_id` string, nullable
- `crm_record_id` UUID FK to `crm_records.id`, nullable
- `approval_status` string, nullable
- `discount_approval_required` boolean, default false
- `discount_approved_by_id` UUID FK to `users.id`, nullable
- `discount_approved_at` timestamp with timezone, nullable

Reasoning:

- Quote-to-order conversion must propagate scope and CRM linkage.
- Quote status should remain `QuoteStatus`; approval status is separate.
- CRM link enables opportunity pipeline traceability.

### CRM Territories

Reconcile existing model and migration ownership. Keep current fields, then add nullable optional scope compatibility fields only if needed:

- `company_id` UUID FK to `companies.id`, nullable
- `branch_id` UUID FK to `branches.id`, nullable
- `sales_team_id` string, nullable
- `customer_group_id` string, nullable

Reasoning:

- The existing `region` and `assigned_rep_ids` fields are usable for current UI.
- Additional fields let access-control checks resolve company/branch/team/customer-group ownership without replacing current territory behavior.

### CRM Records

Add or reconcile nullable fields:

- `territory_id` UUID FK to `crm_territories.id`, nullable if missing
- `company_id` UUID FK to `companies.id`, nullable
- `branch_id` UUID FK to `branches.id`, nullable
- `sales_region_id` string, nullable
- `sales_team_id` string, nullable
- `customer_group_id` string, nullable
- `assigned_customer_id` UUID FK to `customers.id`, nullable

Keep existing string fields for compatibility:

- `customer_id`
- `distributor_id`
- `region_id`
- `assigned_rep_id`
- `assigned_team_id`

Reasoning:

- Do not break current API payloads that use string IDs.
- New typed and canonical scope fields can be introduced gradually.
- `assigned_customer_id` gives access-control helpers a real customer FK without deleting legacy `customer_id`.

### CRM Activities, Interest Lines, Competitors, Win/Loss, AI Recommendations

No direct scope columns are needed in the first slice. These should inherit scope through `crm_record_id`.

Endpoint/service logic should load the parent `CRMRecord` and enforce scope there.

## Proposed Schema / Response Contracts

Add reusable Pydantic models in existing schema files:

### `CommercialAccessHint`

Fields:

- `can_view`
- `can_create`
- `can_edit`
- `can_delete`
- `can_approve`
- `can_convert`
- `can_close`
- `can_discount`
- `can_export`
- `view_only`
- `reason`

### `CommercialScopeFields`

Fields:

- `company_id`
- `branch_id`
- `sales_region_id`
- `sales_team_id`
- `customer_group_id`

Apply optional scope fields and access hints to:

- `CustomerRead`
- `SORead`
- `SODetailRead`
- `ShipmentRead` where warehouse/customer scope decisions affect action UX
- `InvoiceRead` where finance/sales view scope decisions affect action UX
- `QuotationRead`
- `CRMRecordRead`
- `CRMTerritoryRead`

Request schemas should accept the new scope fields only where it is safe:

- customers: allow create/update of commercial scope fields for authorized users
- sales orders: inherit by default from customer, but allow explicit override only after scoped action check
- quotations: inherit by default from customer/CRM record
- CRM records: allow scope fields on create/update after scoped action check
- CRM activities and subordinate rows: no direct scope input; parent record owns scope

## Proposed Service Layer Design

Create a shared commercial service helper rather than duplicating rules in endpoints:

`backend/app/services/commercial_access_service.py`

Suggested helpers:

- `commercial_record_scopes(record) -> list[tuple[str, str]]`
- `inherit_customer_scope(target, customer)`
- `inherit_crm_scope(target, crm_record)`
- `inherit_quote_scope(sales_order, quote)`
- `build_commercial_access_hint(user, module, record)`
- `ensure_commercial_view(user, module, record)`
- `ensure_commercial_action(user, module, action, record)`
- `can_change_commercial_status(record_type, action, status)`
- `discount_requires_approval(discount_pct, customer, quote_or_order)`

Module mapping:

- Customers: `sales` and `crm` may both view; mutation defaults to `sales` for customer master and `crm` for CRM records.
- Sales orders: `sales`.
- Shipments: `sales` plus warehouse dispatch scope.
- Invoices/payments: `sales` for customer-facing collection, `finance` for posting/accounting flows.
- Quotes: `sales` with CRM linkage.
- CRM records/activities/territories: `crm`.

## Scope Resolution Rules

The first available scope should be considered actionable, with mutation requiring the requested action in at least one relevant scope:

1. Superuser bypass.
2. `module.action_all`.
3. Exact scope permission such as `sales.edit_own_region`, `crm.edit_own_region`, or `sales.edit_own_scope`.
4. Matching `AccessScope` row for:
   - `sales_region`
   - `sales_team`
   - `customer_group`
   - `assigned_customer`
   - `company`
   - `branch`
   - `warehouse` for shipment/order allocation and dispatch
5. Deny by default.

View rules:

- `sales.view` and `sales.view_all` preserve broad Sales visibility.
- `crm.view` and `crm.view_all` preserve broad CRM visibility.
- `sales.view_own_scope` and `crm.view_own_region` filter records by effective scopes.

Mutation rules:

- customers: region/team/customer-group/company/branch scope
- CRM records: region/team/territory/customer/company/branch scope
- activities/competitors/interest lines/win-loss: parent CRM record scope
- quotes: customer/CRM record scope
- sales orders: customer/region plus warehouse for allocation
- shipments: sales order/customer plus warehouse for picking/dispatch
- invoices/payments: customer/order scope for sales collection; finance scope for posting flows

## Workflow / Status Locks

Recommended first-slice status locks:

### CRM Records

- `OPEN`: editable by scoped users
- `ON_HOLD`: editable only for reopen/notes/activity actions
- `WON`, `LOST`, `ARCHIVED`: locked except reopen/admin correction

### CRM Activities

- `PLANNED`, `RESCHEDULED`, `NO_RESPONSE`: editable/completable by scoped users
- `COMPLETED`, `CANCELLED`: locked except admin correction

### Quotations

- `DRAFT`: editable/sendable by scoped users
- `SENT`: accept/reject/expire/revise allowed by scoped users
- `ACCEPTED`: convertible by scoped users if discount approval state allows
- `REJECTED`, `EXPIRED`, `CONVERTED`: locked except revise where allowed by existing rules

### Sales Orders

- Keep existing rule: only `DRAFT` orders are directly editable.
- `CONFIRMED`: allocation/cancel only through controlled actions.
- `ALLOCATED`, `PICKING`: shipment flow only.
- `SHIPPED`, `INVOICED`, `CANCELLED`: locked for direct edit.

## Migration Scope For GAP-010C

GAP-010C should add one additive reconciliation migration.

Suggested migration ID:

- `20260515_0010_crm_sales_scope_reconciliation.py`

Migration responsibilities:

1. Create `crm_territories` if missing.
2. Add `crm_records.territory_id` if missing.
3. Add scope columns to `customers`, `sales_orders`, `quotations`, `crm_records`, and `crm_territories` if tables exist.
4. Add quote/order approval columns.
5. Add FKs where safe:
   - `company_id -> companies.id`
   - `branch_id -> branches.id`
   - `assigned_customer_id -> customers.id`
   - `crm_record_id -> crm_records.id`
   - approval user columns -> `users.id`
6. Add indexes for all new scope and linkage fields.
7. Use idempotent helpers so live dev DBs that already contain CRM territory tables do not fail.

Do not:

- drop tables
- rewrite existing CRM string columns
- backfill with guessed IDs
- make new scope columns non-null in this slice

## Backend Model Changes For GAP-010D

Add matching ORM fields and relationships:

- `Customer.company_id`, `Customer.branch_id`, `Customer.sales_region_id`, `Customer.sales_team_id`, `Customer.customer_group_id`
- `SalesOrder.company_id`, `SalesOrder.branch_id`, `SalesOrder.sales_region_id`, `SalesOrder.sales_team_id`, `SalesOrder.customer_group_id`, approval fields
- `Quotation.company_id`, `Quotation.branch_id`, `Quotation.sales_region_id`, `Quotation.sales_team_id`, `Quotation.customer_group_id`, `crm_record_id`, approval fields
- `CRMTerritory.company_id`, `CRMTerritory.branch_id`, `CRMTerritory.sales_team_id`, `CRMTerritory.customer_group_id`
- `CRMRecord.company_id`, `CRMRecord.branch_id`, `CRMRecord.sales_region_id`, `CRMRecord.sales_team_id`, `CRMRecord.customer_group_id`, `assigned_customer_id`

Keep relationships conservative to avoid mapper churn:

- Add company/branch/customer/user relationships only where needed for API output or service rules.
- Avoid eager relationship webs unless current module patterns need them.

## API Changes For GAP-010G

Harden `/api/v1/crm/*`:

- Add authentication to every route.
- Add `crm.view` / `crm.view_all` / `crm.view_own_region` for reads.
- Add `crm.create`, `crm.create_own_region`, `crm.edit`, `crm.edit_own_region`, `crm.approve`, or matching scoped permissions for writes.
- Stage config should require a stronger permission such as `crm.configure` or `roles.manage`.
- AI recommendation run endpoints should require CRM view plus AI/admin permission if available, and should be disabled in mock/high-risk contexts later.

Harden `/api/v1/quotes/*`:

- Add sales/CRM view checks to list/detail/dashboard.
- Add scoped create/edit/send/accept/reject/revise/convert checks.
- Convert should inherit scope fields from quote to sales order.

Extend `/api/v1/sales/*`:

- Apply scope filtering to shipments, invoices, reports, analytics, statement, credit-check, and margin endpoints.
- Add access hints to customer/order/quote rows first; add shipment/invoice hints where action buttons need them.

## Frontend Changes For GAP-010H

- Move `frontend/src/lib/crm_pipeline.ts` from its standalone Axios instance to shared `apiClient`.
- Extend `frontend/src/lib/sales.ts`, `frontend/src/lib/crm_pipeline.ts`, and quotation client types with scope/access fields.
- Use auth helpers to hide/disable create/edit/drag/drop/convert/close controls.
- Add view-only badges to:
  - CRM pipeline cards
  - CRM lead/opportunity rows
  - sales customers
  - sales orders
  - quotations
- Preserve existing page layouts and table/modal patterns.

## Permissions / Roles For GAP-010I

Register or seed missing permissions:

- `crm.view`
- `crm.create`
- `crm.edit`
- `crm.approve`
- `crm.configure`
- `crm.export`
- `crm.view_all`
- `crm.view_own_region`
- `crm.create_own_region`
- `crm.edit_own_region`
- `crm.approve_own_region`
- `sales.create_own_region`
- `sales.edit_own_region`
- `sales.approve_own_region`
- `sales.discount_approve`
- `quotes.view`
- `quotes.create`
- `quotes.edit`
- `quotes.approve`
- `quotes.convert`
- `quotes.view_all`
- `quotes.create_own_region`
- `quotes.edit_own_region`
- `quotes.convert_own_region`

Role direction:

- Regional Sales Manager: broad sales/CRM view, own-region create/edit/convert, discount request.
- Sales Rep: own-region/customer view and scoped create/update.
- Sales Manager: add approve/discount permissions only if business role requires it.
- Read Only Auditor: broad read, no mutation.

## Tests For GAP-010J

Add focused tests for:

- CRM endpoint source contract requires `get_current_user` or permission dependency.
- CRM records outside assigned region are viewable only with broad view and not editable without matching scope.
- CRM stage config requires configure/admin permission.
- Quote conversion inherits scope to sales order.
- Sales reports and statements do not bypass scoped view rules.
- Access hints mark out-of-scope rows as view-only.
- Permission seed includes CRM/quote scoped permissions and conservative role grants.

## Acceptance Criteria For GAP-010B

- Design reuses current models and access-control system.
- Migration scope is additive and idempotent.
- CRM territory migration reconciliation is explicitly planned.
- Schema additions cover view-vs-mutation scope behavior.
- Service/API/frontend/test follow-up tasks have clear boundaries.
- No feature is marked implemented by this design document.
