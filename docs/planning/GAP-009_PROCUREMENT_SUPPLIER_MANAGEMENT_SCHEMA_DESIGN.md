# GAP-009B - Procurement and Supplier Management Schema Design

Status: GAP-009B design complete  
Phase: Phase 3 - High-importance operational modules  
Business priority: High  
Technical area: Procurement / Suppliers

## Objective

Design the next safe data-model slice for procurement and supplier-management maturity. This is a design-only task. No migration or runtime code is added in GAP-009B.

The design must preserve the existing procurement architecture and extend it incrementally. The repo already has PR, PO, GRN, RFQ, blanket agreement, auto reorder, supplier payment, supplier evaluation, supplier master, supplier portal, invoice matching, and landed-cost surfaces.

## Existing Model Anchors

Use these existing models instead of creating replacements:

- `Supplier` in `backend/app/models/master.py`
- `PurchaseRequisition`
- `PRLine`
- `PurchaseOrder`
- `POLine`
- `GoodsReceipt`
- `GRNLine`
- `ImportShipment`
- `SupplierPayment`
- `RFQRequest`
- `RFQResponse`
- `BlanketPurchaseAgreement`
- `AutoReorderPolicy`
- `SupplierEvaluation`

Use existing enterprise scope models where available:

- `Company` from `backend/app/models/company.py`
- `Branch` from `backend/app/models/company.py`
- `CostCenter` from `backend/app/models/dimensions.py`
- Existing `department` string fields until a canonical department master exists.
- Existing `Product.category` enum for product category scope where a product is known.
- Existing `Material.material_type` as material category fallback until a procurement category master exists.

Do not introduce a competing procurement subsystem.

## Design Decisions

### 1. Add Explicit Procurement Scope Columns

Procurement needs broader visibility with scoped mutation. The current PR/PO scope bridge through free-text `department` is not enough.

Add additive nullable columns so existing data can migrate safely:

#### Purchase Requisitions

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- keep existing `department` string for backward compatibility and department scope

Reason:
PRs are usually the first procurement demand document, so this becomes the primary operational scope source for downstream POs, RFQs, and approvals.

#### Purchase Orders

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string copied from PR or provided directly

Reason:
POs can be created from PRs or directly. Direct PO creation must no longer rely on an empty `PurchaseOrder()` for scoped permission decisions.

#### Goods Receipts

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string

Reason:
GRNs currently have `warehouse_id`. Receiving also needs procurement scope and warehouse receiving scope. These fields should be copied from the PO on create.

#### Import Shipments

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string

Reason:
Shipment edits and landed-cost lifecycle need company/branch-aware procurement control.

#### RFQ Requests

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string

Reason:
RFQs may originate from PRs or be created directly. Award and PO conversion must respect the same scope.

#### Blanket Purchase Agreements

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string

Reason:
BPA releases should be limited by operational scope and agreement ownership.

#### Auto Reorder Policies

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string

Reason:
Auto-created PRs must inherit a deterministic scope.

#### Supplier Payments and Evaluations

Add:

- `company_id` nullable FK to `companies.id`
- `branch_id` nullable FK to `branches.id`
- `cost_center_id` nullable FK to `cost_centers.id`
- `department` nullable string where applicable

Reason:
Payments and evaluations are currently procurement-visible but need company/branch scoping and reporting filters.

### 2. Add Supplier Governance Fields Conservatively

Supplier master already includes useful fields. Add only fields that support procurement governance and access filtering.

Add to `Supplier`:

- `supplier_category` nullable string, indexed
- `qualification_status` nullable enum/string with values such as `PENDING`, `APPROVED`, `CONDITIONAL`, `SUSPENDED`, `REJECTED`
- `risk_level` nullable enum/string with values such as `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `approved_from` nullable date
- `approved_until` nullable date
- `approved_by_id` nullable FK to `users.id`
- `approved_at` nullable datetime

Do not remove existing `is_active`, `is_preferred`, `performance_score`, or `compliance_notes`.

Why string/enums instead of a new category table now:

- The current repo does not clearly expose a supplier-category master model.
- GAP-009 should not block hardening work behind a broad master-data refactor.
- A later master-data gap can normalize `supplier_category` into a governed table if needed.

### 3. Add Procurement Approval Rules

Add a new additive table:

`procurement_approval_rules`

Recommended fields:

- `id`
- `rule_name`
- `document_type` (`PR`, `PO`, `RFQ`, `BPA`)
- `company_id` nullable FK
- `branch_id` nullable FK
- `cost_center_id` nullable FK
- `department` nullable string
- `supplier_category` nullable string
- `product_category` nullable string
- `min_amount` nullable numeric
- `max_amount` nullable numeric
- `currency` nullable string
- `approval_level` integer
- `approver_user_id` nullable FK to users
- `approver_role_id` nullable FK to roles
- `requires_all_matching_approvers` boolean default false
- `is_active` boolean default true
- `effective_from` nullable date
- `effective_to` nullable date
- `notes`
- timestamp fields

At least one of `approver_user_id` or `approver_role_id` should be set. Avoid requiring both.

This table does not need to implement the full multi-step workflow immediately. It gives GAP-009F/G a source of truth for amount-limit approval checks without hardcoding role names in endpoints.

### 4. Add Access Hints to Procurement Schemas

Create a reusable response schema:

`ProcurementAccessHint`

Fields:

- `can_view`
- `can_create`
- `can_edit`
- `can_delete`
- `can_approve`
- `can_receive`
- `can_post`
- `can_cancel`
- `can_export`
- `can_import`
- `view_only`
- `reason`

Attach `access: ProcurementAccessHint | None` to important read schemas:

- `PRRead`
- `PORead`
- `GRNRead`
- `ImportShipmentRead`
- `RFQRead`
- `BlanketAgreementRead`
- `AutoReorderPolicyRead`
- `SupplierEvaluationRead`
- `SupplierDashboardRow`

This supports frontend view-only badges and per-row button visibility without trusting frontend-only permission logic.

### 5. Centralize Procurement Scope Resolution

Add service/helper functions in a later GAP-009F slice, not in the migration:

- `procurement_record_scope(record)`
- `procurement_line_category_scope(record_or_line)`
- `can_view_procurement_record(user, record)`
- `can_mutate_procurement_record(user, record, action)`
- `build_procurement_access_hint(user, record)`
- `ensure_procurement_action_allowed(user, record, action)`
- `can_modify_procurement_status(record, action)`

Scope resolution priority:

1. Superuser or `*`.
2. `procurement.<action>_all`.
3. Explicit record scope match:
   - company
   - branch
   - cost center
   - department
   - supplier category
   - product category
   - warehouse receive scope for GRN receiving/posting
4. Deny by default.

View permissions must remain separate from mutation permissions.

### 6. Status Lock Rules

Use a consistent procurement status-lock design:

#### Purchase Requisition

- `DRAFT`: editable by scoped edit users.
- `PENDING_APPROVAL`: editable only for limited fields or by approvers.
- `APPROVED`: no core edit; allow convert to PO.
- `CONVERTED`: locked.
- `REJECTED`: allow limited correction/reset only if explicitly implemented later.
- `CANCELLED`: locked.

#### Purchase Order

- `DRAFT`: editable by scoped edit users.
- `APPROVED`: supplier, currency, and core lines should be locked; allow mark ordered/cancel where permitted.
- `ORDERED`: restrict core commercial edits; allow receiving.
- `PARTIALLY_RECEIVED`: no supplier/core quantity edits; allow remaining receipt and controlled cancel/close rules if later implemented.
- `RECEIVED`: locked except finance/invoice matching flows.
- `CANCELLED`: locked.

#### Goods Receipt

- `DRAFT`: editable by scoped receive users.
- `POSTED`: immutable; corrections must use inventory adjustment/reversal flow, not direct edit.

#### RFQ / BPA / Reorder Policies

- Awarded RFQs should lock supplier response scoring and only allow controlled PO creation.
- Active BPAs allow controlled updates until consumed or expired; cancelled/expired are locked.
- Reorder policies can be edited while active, but generated PRs should not be silently rewritten.

### 7. Migration Ownership Strategy

GAP-009C should be a reconciliation migration:

1. Confirm whether core procurement tables already exist in live development DB.
2. If they exist, add only missing columns/indexes/tables.
3. If Alembic does not own the core procurement table creation, do not recreate tables. Add an idempotent reconciliation migration similar to recent GAP-007/GAP-008 work.
4. Use inspector-aware helpers where possible so offline SQL and live upgrade both work.
5. Do not drop or rewrite procurement data.

Expected GAP-009C migration content:

- Add nullable scope columns to procurement tables listed above.
- Add supplier governance columns.
- Create `procurement_approval_rules`.
- Add indexes on:
  - scope columns
  - supplier category
  - qualification status
  - approval-rule matching columns
  - document status fields where missing and useful

### 8. Backend Model and Schema Follow-Up

GAP-009D should update ORM models to match the migration.

GAP-009E should update Pydantic schemas:

- Add scope fields to create/update/read schemas.
- Add access hints to read schemas.
- Add approval-rule create/update/read schemas.
- Add supplier governance fields to supplier schemas.
- Add validation that direct PO/RFQ/BPA creation has enough target scope to check permissions.

### 9. Endpoint and Frontend Follow-Up

GAP-009F/G should apply centralized procurement helpers to:

- PR list/detail/create/edit/submit/approve/convert.
- PO list/detail/create/edit/approve/order/cancel/line edits.
- GRN list/detail/create/post.
- Import shipments.
- Supplier payments.
- Supplier evaluations.
- Supplier dashboard.
- Delivery schedule and alerts.
- RFQ request/response/award flows.
- BPA create/update.
- Auto reorder policies.

GAP-009H should then update frontend UX:

- Show view-only badges.
- Hide/disable edit/approve/receive/post/cancel buttons by row-level `access`.
- Add stable selectors for future E2E coverage.
- Keep sidebar permission filtering aligned with backend module manifest.

## Acceptance Criteria for This Design

This design is ready for GAP-009C if:

- It reuses existing procurement models and avoids a duplicate subsystem.
- It defines additive, nullable scope fields that are safe for existing data.
- It defines a conservative supplier-governance extension.
- It defines an approval-rule table without hardcoded role logic.
- It defines access hints and status locks for follow-up schema/service/API work.
- It explicitly calls out migration reconciliation and no destructive DB changes.

## Conclusion

GAP-009B should proceed to an additive reconciliation migration. The highest-value next change is not a new procurement module; it is making the existing procurement module scope-aware, approval-aware, and supplier-governance-ready while preserving the working PR/PO/GRN/RFQ/BPA/reorder foundation.
