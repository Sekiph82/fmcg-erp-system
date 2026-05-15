# GAP-009A - Procurement and Supplier Management Maturity Audit

Status: GAP-009A audit complete  
Phase: Phase 3 - High-importance operational modules  
Business priority: High  
Technical area: Procurement / Suppliers

## Objective

Audit the current procurement and supplier-management implementation before designing the next schema slice. This audit records what already exists, what is partial, what is missing, and which files should guide GAP-009B.

## Source Files Inspected

- `backend/app/models/procurement.py`
- `backend/app/models/master.py`
- `backend/app/api/v1/endpoints/procurement.py`
- `backend/app/services/procurement_service.py`
- `backend/app/schemas/procurement.py`
- `frontend/src/lib/procurement.ts`
- `frontend/src/app/dashboard/procurement`
- `frontend/src/app/dashboard/suppliers`
- `backend/app/db/seed.py`
- `backend/alembic/versions`

## Existing Implementation

The repository already has a real procurement foundation. It is not only a placeholder.

Backend procurement models include:

- Purchase requisitions and requisition lines.
- Purchase orders and purchase order lines.
- Goods receipts and GRN lines.
- Import shipments.
- Supplier payments.
- RFQ requests and supplier responses.
- Blanket purchase agreements.
- Auto reorder policies.
- Supplier evaluations.

Supplier master data exists in `backend/app/models/master.py` with supplier code, contact details, payment terms, active flag, lead time, preferred flag, performance score, compliance notes, preferred payment method, and M-Pesa phone support.

Procurement service logic already supports:

- PR creation, update, submit, approval/rejection, and conversion to PO.
- PO creation, update, approval, ordered/cancel transitions, and line updates.
- GRN creation and posting.
- GRN posting into inventory stock movements and stock balances.
- PO receipt progress updates.
- Inbound delivery schedule and delivery alert calculation.

Frontend procurement surfaces already exist for:

- Purchase requisitions.
- Purchase orders.
- RFQs.
- Deliveries.
- Reorder policies.
- Blanket agreements.
- Supplier pages.
- Procurement API client methods and TypeScript types.

Adjacent procurement-related modules also exist:

- Supplier portal.
- Three-way invoice matching.
- Landed cost allocation.
- Procurement suggestions and supplier item pricing.
- Supplier food-safety approval under QMS.
- Supplier sustainability scores under ESG.

## Current Permission and Scope Coverage

The procurement endpoint has started using the GAP-SEC-001 access-control foundation.

Current permission patterns include:

- `procurement.view`
- `procurement.view_all`
- `procurement.view_own_scope`
- `procurement.create_all`
- `procurement.create_own_scope`
- `procurement.edit_all`
- `procurement.edit_own_scope`
- `procurement.approve_all`
- `procurement.approve_own_scope`

The current scoped procurement helper resolves scope mainly from `PurchaseRequisition.department`, or from a PO's linked PR department. This is useful as an initial bridge, but it is too narrow for an enterprise procurement model.

Seed role coverage includes a procurement-manager-style role with broad view and scoped create/edit/approve permissions.

## Partial or Risky Areas

### Scope Model Is Too Narrow

Procurement scope is currently based mainly on a free-text `department` field. The requested ERP-wide scope model needs procurement to support company, branch, department, product category, supplier category, and potentially cost center.

Current procurement records do not consistently carry those normalized scope fields.

Examples:

- `PurchaseRequisition` has `department` as a nullable string, but no `company_id`, `branch_id`, `department_id`, `cost_center_id`, or category scope.
- `PurchaseOrder` can inherit scope through `pr_id`, but direct PO creation has no explicit normalized scope field.
- `GoodsReceipt` has `warehouse_id`, but procurement permission checks are not consistently linked to warehouse receive scope or PO/company scope.
- RFQ, BPA, supplier evaluation, import shipment, supplier payment, and reorder policy records do not consistently expose procurement scope for access control.

### Endpoint Protection Is Uneven

PR and PO lifecycle endpoints have started enforcing procurement permission and department scope.

Other procurement endpoints are mostly authenticated but not consistently permission/scoped:

- GRN list/create/detail/post.
- Import shipment list/create/detail/update.
- Supplier payments.
- Supplier evaluations.
- Supplier dashboard.
- Delivery schedule and alerts.
- RFQ, RFQ response, BPA, and reorder-policy actions.

This means broad authenticated access may still be wider than intended for operational procurement surfaces.

### Direct PO Create Scope Is Fragile

Direct PO creation currently checks `_require_procurement_action(current_user, PurchaseOrder(), "create")`. A new empty `PurchaseOrder()` has no department or other scope. Scoped procurement users may therefore be denied unless they have `procurement.create_all`, or the check may not represent the target operational scope clearly.

GAP-009B should decide whether direct PO create must require explicit company/branch/department scope on the request, or whether all POs should originate from scoped approved PRs.

### Workflow and Status Rules Need Tightening

The service has useful status rules for PR, PO, and GRN flows, but procurement needs a more consistent status-lock contract:

- Approved PRs should only allow controlled conversion/rejection paths.
- Ordered or received POs should restrict price, supplier, and core quantity edits.
- Posted GRNs should be immutable except through controlled reversal/adjustment flows.
- RFQs, awarded responses, active BPAs, and auto reorder policies need clear mutation rules.

### Approval Matrix Is Not Mature Yet

Procurement approval currently exists at the PR and PO level, but no clearly discoverable amount-limit approval matrix was found in the inspected procurement files.

Missing or unclear:

- Approval limits by company, branch, department, category, role, or user.
- Delegation rules.
- Multi-step approval chains.
- Escalation rules.
- Audit visibility into approval reasons and amount-threshold routing.

### Supplier Management Is Fragmented

Supplier master data, supplier portal, QMS food-safety approval, ESG supplier sustainability, procurement evaluations, and supplier item pricing exist in separate areas. That is a good foundation, but supplier governance is not yet unified.

Missing or unclear:

- Supplier onboarding workflow.
- Supplier qualification status owned by procurement.
- Supplier category management.
- Supplier risk/compliance summary visible in procurement.
- Approved supplier list by material/product category.
- Supplier scorecard rollup from delivery, quality, price, responsiveness, ESG, and food-safety signals.

### Procurement-Finance Integration Exists But Needs Governance

The repo has three-way invoice matching and landed cost modules, and GRN lines have accounting posting fields. This is promising.

Still needs design validation:

- PO-to-GRN-to-invoice matching status surfaced consistently in procurement.
- Landed cost allocation lifecycle connected to PO/GRN before final costing.
- Supplier payments connected cleanly to finance ledgers and approval/posting rules.
- Posted financial or inventory-affecting documents protected from direct mutation.

### Migration Ownership Is Not Obvious

Searches found later migrations referencing procurement tables through foreign keys and posting/linkage integrations. The inspected search did not clearly identify a primary Alembic migration that owns creation of the core procurement tables themselves.

This may mean the project originally relied on `create_all` for these tables or that the creation migration uses different naming patterns. GAP-009B/C must reconcile actual live Alembic ownership before adding new fields.

Do not assume the database is already safely migration-owned just because ORM models exist.

## Missing Enterprise Procurement Capabilities

High-priority missing or incomplete capabilities:

- Normalized procurement scope fields and scope resolution.
- Procurement access hints for list responses.
- Frontend view-only badges and per-row mutation disabling for procurement rows.
- Amount-limit approval matrix.
- Delegated approvals and escalation.
- Supplier onboarding and qualification workflow.
- Approved supplier list by item/category/site.
- Supplier category and product-category-based purchasing scope.
- Contract/BPA release control and consumption enforcement.
- RFQ award governance and PO creation from awarded supplier response.
- Auto reorder execution governance from stock/MRP signals to PR/PO.
- 3-way matching status visible in PO/GRN procurement flows.
- Landed cost status visible in import procurement flows.
- Strong posted/received document immutability and reversal paths.
- Procurement audit trail for critical status transitions and approval decisions.
- CSV import/export parity for procurement masters and open documents, if not already covered by the universal import/export engine.

## Recommended Direction for GAP-009B

GAP-009B should not create a parallel procurement architecture. It should extend the current implementation in controlled slices.

Recommended design decisions:

1. Reuse the existing PR, PO, GRN, RFQ, BPA, auto reorder, supplier evaluation, and supplier master models.
2. Add normalized procurement scope fields only where needed, likely:
   - `company_id`
   - `branch_id`
   - normalized `department_id` or a clear bridge from the existing `department` string
   - `supplier_category_id` if a category model exists or is introduced
   - `product_category` or `product_category_id` depending on current master-data conventions
   - `cost_center_id` if finance integration requires it
3. Create a central procurement scope resolver instead of repeating scope logic inside endpoints.
4. Tighten endpoint checks beyond PR/PO to GRN, shipments, RFQ, BPA, reorder policies, supplier payments, evaluations, dashboard, and delivery views.
5. Add access hints to important procurement list responses before making broad frontend UX changes.
6. Keep GRN inventory posting behavior intact and protect posted GRNs from direct edits.
7. Design approval amount limits before implementing approval-chain behavior.
8. Treat supplier governance as an incremental unification layer across procurement, QMS, ESG, and supplier portal records.

## Suggested GAP-009 Subtask Priorities

For the next tasks:

- GAP-009B should design the normalized scope and approval data model.
- GAP-009C should add only additive Alembic reconciliation fields/tables after confirming existing table ownership.
- GAP-009D/E should update models and schemas to expose scope, approval, and access-hint data.
- GAP-009F/G should centralize procurement service/endpoint enforcement before broad UI expansion.
- GAP-009H should add procurement frontend view-only/action visibility using backend access hints.
- GAP-009I should register or verify procurement role/permission coverage without weakening scoped access.
- GAP-009J should add focused tests for broad view versus scoped mutation.
- GAP-009K should document admin setup and operational workflow behavior.

## Audit Conclusion

GAP-009 is a maturity and hardening gap, not a blank-module build. The repo already has broad procurement functionality. The highest-value next work is to normalize procurement scope, harden every procurement endpoint with permission + scope + status rules, and connect supplier governance into one coherent procurement view.

GAP-009A acceptance criteria are met: existing implementation, partial coverage, missing capabilities, risky areas, source files, and next design direction are documented.
