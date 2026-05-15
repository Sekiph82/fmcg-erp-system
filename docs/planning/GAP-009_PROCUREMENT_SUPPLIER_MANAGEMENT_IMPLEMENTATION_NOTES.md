# GAP-009 - Procurement and Supplier Management Maturity Implementation Notes

Status: GAP-009K documentation complete  
Phase: Phase 3 - High-importance operational modules  
Business priority: High  
Technical area: Procurement / Suppliers

## Summary

GAP-009 hardens the existing procurement foundation rather than replacing it. The repo already had working purchase requisitions, purchase orders, goods receipts, RFQs, blanket agreements, auto reorder policies, supplier evaluations, supplier payments, and supplier master data. This slice adds procurement scope/governance structure, access hints, approval-rule foundations, and conservative role permissions.

## Implemented Scope

### Migration

Added `backend/alembic/versions/20260514_0030_procurement_scope_governance.py`.

The migration is additive and reconciliation-oriented:

- Adds procurement scope columns to procurement document tables:
  - `company_id`
  - `branch_id`
  - `cost_center_id`
  - `department`
- Adds supplier governance fields:
  - `supplier_category`
  - `qualification_status`
  - `risk_level`
  - `approved_from`
  - `approved_until`
  - `approved_by_id`
  - `approved_at`
- Adds `procurement_approval_rules` for amount/scope-based approval governance.
- Adds supporting indexes and foreign keys.
- Does not drop data, reset tables, or recreate existing procurement records.

Live local development verification was completed:

- `alembic upgrade head` succeeded.
- `alembic current` reports `20260514_0030 (head)`.
- Live schema query verified procurement scope columns, supplier governance columns, `procurement_approval_rules`, and Alembic version.

### Backend Models

Updated:

- `backend/app/models/master.py`
- `backend/app/models/procurement.py`

Added:

- `SupplierQualificationStatus`
- `SupplierRiskLevel`
- supplier governance ORM fields
- procurement document scope ORM fields
- `ProcurementApprovalDocumentType`
- `ProcurementApprovalRule`

### Backend Schemas

Updated:

- `backend/app/schemas/master.py`
- `backend/app/schemas/procurement.py`

Added:

- optional supplier governance fields in supplier schemas
- reusable `ProcurementScopeFields`
- reusable `ProcurementAccessHint`
- access hints on important procurement read schemas
- procurement approval-rule create/update/read schemas

New fields are optional to preserve current API compatibility.

### Service Helpers

Updated:

- `backend/app/services/procurement_service.py`

Added helper behavior:

- `inherit_procurement_scope`
- `can_change_procurement_status`
- `build_procurement_access_hint`
- `ensure_procurement_action_allowed`
- `procurement_document_amount`
- `find_procurement_approval_rules`

PR-to-PO conversion now copies procurement scope from the source PR to the generated PO.

### API Endpoints

Updated:

- `backend/app/api/v1/endpoints/procurement.py`

Key changes:

- PR/PO creation and mutation checks now use centralized procurement access helpers.
- GRN, shipment, supplier payment, supplier evaluation, RFQ, BPA, and reorder-policy routes now have stronger permission/scope checks in the current slice.
- Important list/detail responses can include row-level `access` hints.
- Added protected approval-rule endpoints:
  - `GET /api/v1/procurement/approval-rules`
  - `POST /api/v1/procurement/approval-rules`
  - `PATCH /api/v1/procurement/approval-rules/{rule_id}`

Approval-rule management requires `procurement.approve_all` or `roles.manage`.

### Frontend

Updated:

- `frontend/src/lib/procurement.ts`
- `frontend/src/app/dashboard/procurement/page.tsx`

Added:

- procurement scope and access-hint TypeScript types
- procurement approval-rule API client methods
- access hints on major procurement interfaces
- PR list access badge:
  - `View only`
  - `Actionable`

The frontend remains a UX helper only. Backend permission/scope enforcement remains the source of truth.

### Permissions and Roles

Updated:

- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`

Procurement module actions now include:

- `view`
- `create`
- `edit`
- `delete`
- `approve`
- `receive`
- `post`
- `cancel`
- `export`
- `import`

Added scope-aware procurement permission keys:

- `procurement.receive_all`
- `procurement.receive_own_scope`
- `procurement.post_all`
- `procurement.post_own_scope`
- `procurement.cancel_all`
- `procurement.cancel_own_scope`
- `procurement.delete_all`
- `procurement.delete_own_scope`
- `procurement.export_all`
- `procurement.export_own_scope`
- `procurement.import_all`
- `procurement.import_own_scope`

The procurement manager role receives conservative scoped grants for receive, post, cancel, export, and import. It does not receive global mutation rights.

## Tests and Checks

Added:

- `backend/tests/test_gap009_procurement_maturity.py`

Focused tests cover:

- migration source contract
- model fields and enums
- schema access hints and approval-rule contract
- service helper behavior
- endpoint/frontend/seed source contracts

Commands run:

- `python -m py_compile` for changed backend files
- `pytest tests/test_gap009_procurement_maturity.py -q`
- `alembic heads`
- `alembic history`
- offline SQL generation for the migration
- live Docker `alembic upgrade head`
- live schema verification query
- frontend `npm run type-check`

Known test warnings:

- Existing SQLAlchemy relationship overlap warnings appear for dimension/project models. They are unrelated to GAP-009.

## Admin Setup Notes

For scoped procurement users:

1. Assign procurement role permissions, such as:
   - `procurement.view_all`
   - `procurement.create_own_scope`
   - `procurement.edit_own_scope`
   - `procurement.approve_own_scope`
   - `procurement.receive_own_scope`
   - `procurement.post_own_scope`
2. Assign `AccessScope` rows for the relevant operational scopes:
   - `company`
   - `branch`
   - `cost_center`
   - `department`
   - future supplier/product category scopes as configured
3. Use `procurement.approve_all` or `roles.manage` only for users who should manage approval-rule configuration.

## Remaining Follow-Ups

The current slice is a foundation and partial rollout. Remaining production-hardening work includes:

- Populate scope fields consistently when legacy records are missing company/branch/cost-center data.
- Extend frontend scope fields into create/edit forms where operational users need explicit target scope selection.
- Add a dedicated approval-rule admin UI.
- Apply access hints to more procurement subpages beyond the PR list.
- Add deeper endpoint tests with real database fixtures and scoped user personas.
- Connect approval-rule lookup into PR/PO approval decisions.
- Add supplier qualification workflow screens and supplier scorecard rollups.
- Link supplier governance data across QMS, ESG, supplier portal, and procurement dashboards.
- Add controlled reversal/correction flows for posted GRNs instead of direct edits.
- Add report/export behavior that respects the same procurement scopes.

## Operational Rule

Broad procurement visibility and mutation authority remain separate.

A user may view broad procurement records when granted `procurement.view_all`, but create/edit/approve/receive/post/cancel actions must still pass permission, scope, and workflow-status checks.
