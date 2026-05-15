# GAP-010 CRM / Sales Pipeline Depth Audit

## Summary

GAP-010 is not starting from an empty sales module. The repository already has a substantial Sales & Distribution foundation, a separate CRM pipeline module, quotation workflows, field/van/secondary sales surfaces, customer statements, credit checks, margin reporting, M-Pesa integration hooks, and many frontend pages.

The main issue is uneven maturity. Core `/sales` customer and sales-order endpoints already received some scope-aware controls from GAP-SEC-001, but `/crm` pipeline endpoints are still unauthenticated and unscoped. The CRM data model has real lead/opportunity/stage/activity/win-loss concepts, but it is missing enterprise-grade commercial governance such as structured territories, sales teams, customer groups, approval limits, quote/order scope inheritance, and per-record access hints.

## Business Requirement

CRM and sales pipeline depth matters because the ERP must support the full commercial funnel, not only order entry:

- lead capture and qualification
- opportunity stage progression
- territory/team ownership
- customer account governance
- quotes, discounts, credit checks, and conversion to sales orders
- activity management and overdue follow-up
- pipeline forecast, win/loss analysis, and commercial KPIs
- regional visibility with scoped mutation controls
- safe integration into inventory, finance, logistics, and production demand

The target behavior should preserve the GAP-SEC-001 rule: users may view broad/global commercial data when permitted, but can only create, edit, approve, discount, convert, or close records inside assigned operational scope.

## Current Implementation Found

### Sales & Distribution

Existing backend implementation includes:

- Customer master with channel, customer type, region, segment, route/distributor links, credit limit, prepaid flag, and contact/address fields.
- Sales orders with DRAFT, CONFIRMED, ALLOCATED, PICKING, SHIPPED, INVOICED, and CANCELLED status progression.
- Sales order lines with product, quantity, price, tax, discount, allocation, shipped quantity, and cost price fields.
- Shipments and shipment lines with picking, dispatch, lot linkage, and stock movement creation on dispatch.
- Invoices, invoice lines, payments, overdue synchronization, customer statements, aged balance, and credit checks.
- M-Pesa transaction support and callback handling.
- Margin reporting and sales analytics by source, segment, and campaign.
- Some scoped access controls on customers and sales orders using sales region and warehouse scope helpers.

Existing frontend implementation includes:

- Sales dashboard.
- Customers page with list/create/edit flow and stable E2E selectors.
- Sales orders, order detail, shipments, shipment detail, invoices, invoice detail, collections, returns, quotes, pricing, delivery, POD, margin, customer statement, field sales, distributors, secondary sales, and reports pages.
- Sales API client covering customers, orders, shipments, invoices, M-Pesa, customer statement, credit check, and margin APIs.

### CRM Pipeline

Existing backend implementation includes:

- CRM pipeline stages.
- CRM records for leads and opportunities.
- Interest lines.
- Activities and activity completion.
- Competitors.
- Win/loss records.
- AI recommendations for lead prioritization, pipeline risk, and win/loss insight.
- Dashboard, forecast, pipeline report, win/loss report, territory performance, duplicate check, and record 360 summary services.
- Frontend CRM pages for dashboard, leads, opportunities, pipeline board, activities, qualification, forecast, win/loss, overdue queue, territory management, stage config, record detail, and AI agents.

### Quotations

Existing backend implementation includes:

- Quote lifecycle: DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED, CONVERTED.
- Quote lines, totals, revision, status transitions, dashboard, and conversion to sales order.
- Quote conversion creates a sales order and sales-order lines.

The quotation endpoints use authentication, but do not yet reuse the sales/CRM scope helpers.

## Backend Files Inspected

- `backend/app/models/sales.py`
- `backend/app/models/crm.py`
- `backend/app/models/quotation.py`
- `backend/app/schemas/sales.py`
- `backend/app/schemas/crm.py`
- `backend/app/schemas/quotation.py`
- `backend/app/services/sales_service.py`
- `backend/app/services/crm_pipeline_service.py`
- `backend/app/api/v1/endpoints/sales.py`
- `backend/app/api/v1/endpoints/crm_pipeline.py`
- `backend/app/api/v1/endpoints/quotation.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/alembic/versions/f9a0b1c2d3e4_crm_pipeline.py`
- `backend/alembic/versions/3c45d9071c98_initial_schema.py`
- Sales/CRM-related migration files found by repository search.

## Frontend Files Inspected

- `frontend/src/lib/sales.ts`
- `frontend/src/lib/crm_pipeline.ts`
- `frontend/src/components/nav-config.tsx`
- `frontend/src/app/dashboard/sales/page.tsx`
- `frontend/src/app/dashboard/sales/customers/page.tsx`
- `frontend/src/app/dashboard/sales/orders/page.tsx`
- `frontend/src/app/dashboard/sales/orders/[id]/page.tsx`
- `frontend/src/app/dashboard/sales/shipments/page.tsx`
- `frontend/src/app/dashboard/sales/invoices/page.tsx`
- `frontend/src/app/dashboard/sales/quotes/page.tsx`
- `frontend/src/app/dashboard/crm/page.tsx`
- `frontend/src/app/dashboard/crm/leads/page.tsx`
- `frontend/src/app/dashboard/crm/opportunities/page.tsx`
- `frontend/src/app/dashboard/crm/pipeline/page.tsx`
- `frontend/src/app/dashboard/crm/records/[id]/page.tsx`
- `frontend/src/app/dashboard/crm/territory/page.tsx`
- `frontend/src/app/dashboard/crm/stages/page.tsx`
- `frontend/src/app/dashboard/crm/ai/page.tsx`

## Models / Schemas / Services / Endpoints Found

### Existing Models

- `Customer`, `SalesOrder`, `SOLine`, `Shipment`, `ShipmentLine`, `Invoice`, `InvoiceLine`, `Payment`, `MpesaTransaction`.
- `CRMRecord`, `CRMPipelineStage`, `CRMInterestLine`, `CRMActivity`, `CRMCompetitor`, `CRMWinLoss`, `CRMAIRecommendation`, `CRMTerritory`.
- `Quotation`, `QuotationLine`.

### Existing Services

- `sales_service.py` contains sales order confirmation, stock allocation, reservation release, shipment picking/dispatch, invoice creation, payment recording, overdue sync, customer statement, credit check, and margin calculations.
- `crm_pipeline_service.py` contains CRM stage setup, lead/opportunity CRUD helpers, qualification, conversion, close-won/lost, activity handling, duplicate checks, dashboards, forecasts, reports, territory performance, AI recommendation generation, and record 360 summaries.

### Existing Endpoints

- `/api/v1/sales/customers`
- `/api/v1/sales/orders`
- `/api/v1/sales/shipments`
- `/api/v1/sales/invoices`
- `/api/v1/sales/reports/*`
- `/api/v1/sales/analytics/*`
- `/api/v1/sales/customers/{id}/statement`
- `/api/v1/sales/customers/{id}/credit-check`
- `/api/v1/crm/*`
- `/api/v1/quotes/*`

## Existing Permissions / Roles / Scopes Found

Existing seed and registry coverage includes:

- Base `sales.view`, `sales.create`, `sales.edit`, `sales.approve`, `sales.export`.
- Scoped sales permissions such as `sales.view_all`, `sales.view_own_scope`, `sales.create_own_region`, and `sales.edit_own_region`.
- CRM-related role grants such as `crm.view`, `crm.create`, `crm.edit`, `crm.view_all`, and `crm.edit_own_region`.
- `pricing.request_discount`.
- Regional sales manager role with broad view plus own-region mutation permissions.
- Frontend nav uses mostly `sales.view` for CRM and Sales menu items, with a small number of `crm.view` entries under marketing.

Important: the `sales` module is a registry-owned critical module, but CRM pipeline is currently registered as an endpoint route rather than its own module definition. That means CRM route ownership, manifest visibility, and permission coverage are weaker than the core sales module.

## Existing Tests Found

Relevant test coverage is mostly indirect:

- GAP-SEC-001 tests include sales scope behavior for broad view plus own-region mutation.
- GAP-SEC-001 source-contract tests check that `sales.py` contains `_require_customer_action` and `_require_so_action`.
- E2E scaffolding includes Sales Customers page smoke selectors.
- Existing attack/security tests mention sales paths.

No focused GAP-010 tests were found for:

- CRM endpoint authentication.
- CRM scoped view/mutation.
- CRM stage mutation permissions.
- Quote scope enforcement.
- Sales shipment/invoice scope enforcement.
- Discount approval behavior.
- Territory/team/customer-group ownership.
- Pipeline forecast scoped visibility.

## Existing Documentation Found

The roadmap plan and E2E documentation mention sales and CRM generally, but there is no dedicated GAP-010 implementation/audit document before this file.

## Missing Pieces

### Critical

- `/api/v1/crm/*` endpoints do not currently depend on `get_current_user`, `require_any_permission`, or scoped access helpers. This leaves CRM stages, leads, opportunities, activities, territory management, reports, and AI recommendations exposed at the endpoint layer.
- CRM records do not expose access hints, so the frontend cannot show "View only" versus actionable pipeline records.
- CRM pipeline does not enforce region/team/territory/customer-group scope on create, update, qualify, convert, close-won/lost, activity completion, territory edits, or AI recommendation acknowledgement.
- Quote endpoints are authenticated but not permission/scoped-action protected.
- Sales shipment, invoice, payment, reports, analytics, statement, credit-check, and margin endpoints mostly require only authentication rather than sales view/action permissions and scope filtering.

### High Importance

- CRM territory model exists in ORM/service/schema, but migration ownership for `crm_territories` and `crm_records.territory_id` was not found in Alembic search. This is a live schema risk that must be reconciled before relying on territory workflows.
- CRM uses string IDs for `customer_id`, `distributor_id`, `region_id`, `country_id`, `channel_id`, `assigned_rep_id`, and `assigned_team_id`, while adjacent modules use UUID foreign keys for many similar concepts. This limits relational integrity and scope resolution.
- Sales customer scope is currently based mainly on `Customer.region` string. There is no first-class sales region/team/customer-group table for enterprise ownership rules.
- Sales order mutation checks use customer region and warehouse, but list/report endpoints do not consistently apply the same filtering.
- Quote-to-sales-order conversion does not inherit sales scope, CRM record linkage, region/team assignment, campaign attribution, or approval context.
- No formal discount approval workflow was found for sales orders/quotes despite `sales.approve` and `pricing.request_discount`.

### Medium Importance

- Frontend CRM pages use a standalone Axios instance in `crm_pipeline.ts` instead of the shared `apiClient`, so cookie/auth behavior may diverge from the hardened auth path.
- CRM frontend pages show action controls without permission/scope checks.
- CRM AI agents are operational rule-based generators, but page-level mock/live mode and high-risk action disabling are not consistently present.
- Customer create/edit UI omits some backend fields such as region, segment, customer type, prepaid flag, delivery fields, and active flag.
- Navigation exposes many sales-related pages behind a single `sales.view` permission, which is too coarse for mature pricing, contracts, portal, commissions, and CRM admin surfaces.

## Partial / Incomplete Pieces

- Scoped sales access is partially implemented for customers and sales orders, but not consistently across the entire sales domain.
- CRM has rich domain objects, but lacks security and schema reconciliation.
- Territory management is present in UI/service/model, but likely blocked by missing migration coverage.
- E2E tests can smoke the sales customers page, but do not verify CRM/sales workflow correctness or scope controls.
- Quotation workflow is realistic for status transitions, but not yet integrated with CRM opportunity governance or scoped sales permissions.

## Risks

| Risk | Impact |
|---|---|
| Unauthenticated CRM endpoints | Any caller can create/modify CRM records, stages, territories, activities, and AI recommendations if the app is reachable. |
| Missing CRM migration reconciliation | Territory pages/endpoints can fail at runtime if live DB lacks `crm_territories` or `crm_records.territory_id`. |
| Inconsistent scope enforcement | Users may view broad data correctly but mutate records outside assigned region/team through CRM, quotes, shipments, invoices, or reports. |
| String-based ownership fields | Hard to enforce referential integrity, module manifest scopes, and cross-module reporting. |
| Coarse frontend nav permission | Users may see CRM/pricing/admin-like sales pages that should require finer permissions. |
| Quote conversion not scope-aware | Accepted quotes could create sales orders outside the user’s commercial scope. |

## Recommended Direction For GAP-010B

GAP-010B should design a reconciliation-first schema plan rather than a new parallel CRM architecture.

Recommended model direction:

- Keep existing Sales, CRM, and Quotation models.
- Add missing CRM migration coverage for `crm_territories` and `crm_records.territory_id` if live migration history confirms they are absent.
- Add explicit commercial scope fields where needed:
  - `company_id`
  - `branch_id`
  - `sales_region`
  - `sales_team_id`
  - `customer_group_id`
  - `assigned_customer_id`
- Add reusable access-hint schemas for sales/CRM records.
- Add structured discount/approval fields to quotes and sales orders only if they are not already covered by pricing/approval modules.
- Add quote/sales/CRM scope inheritance rules.
- Prefer service-layer helpers for:
  - CRM record scope resolution.
  - Sales document scope resolution.
  - Quote mutation/status locks.
  - Pipeline stage/action locks.
  - Access hint construction.
- Do not replace the existing Sales/CRM modules or duplicate GAP-SEC-001 access-control architecture.

Recommended endpoint direction:

- Add auth/permission dependencies to every `/crm` endpoint.
- Apply broad-view versus own-scope filtering to CRM lists, dashboards, forecasts, reports, and 360 views.
- Require scoped mutation for record create/update, lead qualification, opportunity conversion, close-won/lost, activities, territory mutation, and AI recommendation acknowledgement.
- Reuse scope checks in quotation and sales shipment/invoice/report endpoints.

Recommended frontend direction:

- Move `crm_pipeline.ts` to the shared `apiClient`.
- Add permission/scope helpers to CRM pages.
- Show view-only badges and disable drag/drop/action buttons for records outside mutation scope.
- Keep the current CRM page set, but wire it to access hints and finer permissions.

## Acceptance Criteria For GAP-010 Completion

- CRM endpoints require authentication and appropriate permissions.
- CRM and sales lists support broad view and scoped view.
- CRM and sales mutations are denied outside assigned operational scope.
- CRM territory schema is reconciled with Alembic and verified.
- Quotes and quote-to-order conversion respect sales/CRM scope and status locks.
- Key sales/CRM responses include access hints where frontend row-level action UX needs them.
- Frontend CRM and sales pages use shared auth-aware API client behavior.
- Sidebar and action buttons reflect permissions without being the security boundary.
- Focused tests cover CRM auth, scoped mutation, quote conversion guards, and sales report/list filtering.
- Documentation records admin setup, permissions, scope assignment, and remaining limitations.
