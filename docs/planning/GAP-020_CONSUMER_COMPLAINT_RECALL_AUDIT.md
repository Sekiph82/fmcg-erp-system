# GAP-020 Consumer Complaint and Recall Linkage — Audit

## Summary

Consumer complaints and recall workflows **exist structurally** but are decoupled. Complaints are a lightweight CRUD module; recalls are a full stateful workflow under traceability. Their linkage is a fragile one-way UUID bridge with no automatic trigger, no bidirectional queries, and no permission framework for complaints.

---

## What Exists (Complete)

### Consumer Complaints (`backend/app/models/consumer_complaints.py`)
1 model: `ConsumerComplaint`
- Key fields: `complaint_ref`, `consumer_name`, `consumer_contact`, `channel`, `product_name`, `lot_number`, `batch_id` (soft FK), `severity` (SAFETY/QUALITY/FOREIGN_OBJECT/LABEL_ISSUE/PACKAGING/OTHER), `status` (NEW→INVESTIGATING→RESOLVED→CLOSED), `recall_triggered_flag`, `recall_ref`, `root_cause`, `corrective_action`, `regulatory_report_required`
- Auto-flags SAFETY severity as `recall_triggered_flag=True` at creation

### Recall Models (in `backend/app/models/traceability.py`)
9 models: `RecallHeader`, `RecallScopeLine`, `RecallAction`, `RecallCustomerImpact`, `RecallReturnRecord`, `TRRecAIRecommendation`, `RecallCommunicationTemplate`, `RecallStatusLog`, `RecallEvidence`
- `RecallHeader.linked_complaint_id` (UUID, nullable — soft link to complaints)
- `RecallHeader.trigger_source` enum includes `complaint`
- Full stateful workflow: draft → under_review → active → contained → completed → closed

### Consumer Complaints Endpoints (6 total, prefix `/api/v1/consumer-complaints`)
- `POST /` — create with auto-flag
- `GET /` — list with severity/status/recall filters
- `GET /stats` — severity/status breakdown + recall_triggered count
- `GET /{complaint_id}` — detail
- `PATCH /{complaint_id}` — update
- `GET /by-lot/{lot_number}` — complaints for lot + recall flag

### Recall Endpoints (26 total, prefix `/api/v1/traceability/recalls`)
Full workflow: initiate, scope calculate, contain, actions, customer impact, notifications, returns, close, regulatory report, AI agents (3), evidence, communication templates, status log

### Recall Service (`backend/app/services/recall_service.py`)
30+ functions: `initiate_recall`, `calculate_scope`, `contain_recall`, `build_customer_impact`, `notify_customer`, `record_return`, `close_recall`, `generate_regulatory_report`, `run_recall_ai_agents`, 3 AI agents (scope_validator, risk_prioritizer, investigation_assistant)

### Frontend
- `frontend/src/app/dashboard/quality/consumer-complaints/page.tsx` — complaint list, stats, update; shows recall_triggered_flag
- `frontend/src/app/dashboard/traceability/recalls/page.tsx` — recall list
- `frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx` — recall detail
- `frontend/src/app/dashboard/traceability/mock-recall/page.tsx` — demo

---

## What Is Missing / Gaps

### 1. No Module Registration for Consumer Complaints — CRITICAL
`consumer_complaints` is `EndpointRouteDefinition` only. No permission codes generated. No sidebar group, no AI mode.

**Fix**: Promote to `ModuleDefinition` with actions `("view", "create", "edit", "escalate", "close", "report")`.

### 2. No Seed Permissions for Consumer Complaints — CRITICAL
No `consumer_complaints.*` tuples in `backend/app/db/seed.py`. Endpoints accessible without explicit permission grant.

### 3. Minimal Recall Permissions
Only `traceability.recall_initiate` and `traceability.recall_close` exist. No `recall.view`, `recall.manage`, `recall.report` etc. Recall is buried under traceability module, not surfaced as its own permission domain.

### 4. No Dedicated Schema File for Consumer Complaints
Schemas defined as inline `BaseModel` classes in endpoints. No reusable `backend/app/schemas/consumer_complaints.py`.

### 5. No Service Layer for Consumer Complaints
All complaint logic embedded in endpoint handlers. No dedicated service module.

### 6. Complaint → Recall Linkage Is One-Way and Manual
- `RecallHeader.linked_complaint_id` exists but is not an FK constraint.
- No reverse: cannot query "all recalls triggered by this complaint."
- Auto-flag at complaint creation does NOT automatically create a RecallHeader.
- No service function: `initiate_recall_from_complaint(complaint_id)`.

### 7. No Lot-Complaint-Recall Trace Chain
`calculate_scope` uses forward lot tracing but does not query complaints history for the same lot to suggest expanded scope.

### 8. Nav-Config Guards Need Audit
Consumer complaints nav items likely use wrong permission code (no `consumer_complaints.*` codes exist).

---

## Migration Assessment

No new columns needed for module promotion. The `linked_complaint_id` UUID field on `RecallHeader` exists. An explicit FK constraint would require a migration; that is deferred as a known limitation.

---

## Files

| File | Status |
|---|---|
| `backend/app/models/consumer_complaints.py` | Complete — 1 model |
| `backend/app/models/traceability.py` | Complete — 9 recall models |
| `backend/app/schemas/consumer_complaints.py` | MISSING — inline schemas only |
| `backend/app/services/recall_service.py` | Complete — 30+ functions |
| `backend/app/api/v1/endpoints/consumer_complaints.py` | Complete — 6 endpoints |
| `backend/app/api/v1/endpoints/traceability.py` | Complete — 26 recall endpoints |
| `backend/app/core/module_registry.py` | Gap: consumer_complaints in EndpointRouteDefinition |
| `backend/app/db/seed.py` | Gap: no consumer_complaints permissions |
| `frontend/src/app/dashboard/quality/consumer-complaints/` | Complete — 1 page |
| `frontend/src/app/dashboard/traceability/recalls/` | Complete — 3 pages |

---

## Recommended Fix Scope (GAP-020B–L)

1. **GAP-020B (Schema Design)**: No new tables. Promote consumer_complaints, add schema file.
2. **GAP-020C (Migration)**: SKIP — no schema changes.
3. **GAP-020D (Models)**: SKIP — models complete.
4. **GAP-020E (Schemas)**: Add `backend/app/schemas/consumer_complaints.py` with `ComplaintCreate`, `ComplaintUpdate`, `ComplaintRead`.
5. **GAP-020F (Services)**: Add `backend/app/services/consumer_complaint_service.py` with `create_complaint`, `list_complaints`, `get_complaint`, `update_complaint` — extract from endpoint handlers.
6. **GAP-020G (Endpoints)**: Update complaint endpoints to use service layer (thin handlers).
7. **GAP-020H (Frontend)**: SKIP — pages complete.
8. **GAP-020I (Permissions)**: Promote consumer_complaints to MODULE_DEFINITIONS; seed 6 permissions; fix nav-config.
9. **GAP-020J (Tests)**: Write focused tests for module contract, schema contract, and linkage.
10. **GAP-020K (Docs)**: Implementation notes.
11. **GAP-020L (Checks)**: Final compile/test checks.

**Known limitations (deferred)**:
- Automatic RecallHeader creation from complaint (requires UX/workflow decision)
- Explicit FK constraint on linked_complaint_id (requires migration)
- Lot-complaint-recall trace chain in calculate_scope
