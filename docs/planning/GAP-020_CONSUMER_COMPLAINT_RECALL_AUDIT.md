# GAP-020 Consumer Complaint and Recall Linkage — Audit

## Overview

This document audits the current state of consumer complaint management and product recall workflows in the FMCG ERP system. It records what is fully implemented, what is partially implemented, and what is structurally missing — specifically the linkage between the two systems.

**Gap Classification:** Tier 4 — FMCG-Specific & Regulatory  
**Priority:** High  
**Phase:** Phase 5 — FMCG Regulatory Polish  
**Status:** Audit complete. Fix scope defined in GAP-020B–L.

---

## Business Context

In FMCG operations, consumer complaints and product recalls are deeply connected. A consumer complaint about a SAFETY issue (foreign object, illness, contamination) should trigger immediate review of the lot/batch involved and potentially escalate to a full product recall. Regulatory bodies (Kenya KEBS, EU Food Safety Authority, FDA) require traceability from the first complaint to the full recall scope — including which customers received the affected lot, what quantities were shipped, and whether all products have been recovered or disposed of.

**Current problem:** In this ERP, complaints and recalls are two separate systems. A complaint can set a flag (`recall_triggered_flag = True`) but that flag does NOT automatically start a recall. An operator must manually open the Traceability module, create a new recall, and then manually type in the complaint reference. There is no automated linkage, no reverse lookup, and no audit trail connecting the two.

---

## System 1: Consumer Complaints

### Location
- Model: `backend/app/models/consumer_complaints.py`
- Endpoints: `backend/app/api/v1/endpoints/consumer_complaints.py`
- Frontend: `frontend/src/app/dashboard/quality/consumer-complaints/page.tsx`

### What It Does
The consumer complaint module captures complaints received from customers or consumers about product quality, safety, or packaging. Each complaint is assigned a reference number (e.g. `CC-20260515-0001`) and tracked through a resolution lifecycle.

### Data Model: `ConsumerComplaint`

| Field | Type | Purpose |
|---|---|---|
| `complaint_ref` | String (unique) | Auto-generated reference: `CC-YYYYMMDD-NNNN` |
| `consumer_name` | String | Name of person who complained |
| `consumer_contact` | String | Phone/email for follow-up |
| `consumer_location` | String | Where consumer purchased the product |
| `channel` | Enum | How complaint was received: PHONE / EMAIL / SOCIAL_MEDIA / IN_STORE / REGULATORY / OTHER |
| `product_name` | String | Product complained about |
| `lot_number` | String | Lot or batch number on the product label |
| `batch_id` | UUID (soft FK) | Optional link to internal batch record |
| `purchase_date` | String | When consumer bought the product |
| `purchase_location` | String | Retailer or market where purchased |
| `severity` | Enum | SAFETY / QUALITY / FOREIGN_OBJECT / LABEL_ISSUE / PACKAGING / OTHER |
| `description` | Text | Complaint narrative from consumer |
| `status` | Enum | NEW → ACKNOWLEDGED → INVESTIGATING → RESOLVED → COMPENSATED → ESCALATED → CLOSED |
| `assigned_to` | String | Staff member handling the complaint |
| `root_cause` | Text | Root cause identified during investigation |
| `corrective_action` | Text | Action taken to fix the issue |
| `recall_triggered_flag` | Boolean | True if severity is SAFETY or FOREIGN_OBJECT |
| `recall_ref` | String | Manual text field for recall reference (not a FK) |
| `regulatory_report_required` | Boolean | True if complaint requires reporting to authorities |
| `acknowledged_at` | Timestamp | When status changed to ACKNOWLEDGED |
| `resolved_at` | Timestamp | When status changed to RESOLVED or CLOSED |
| `compensation_notes` | Text | Notes on compensation offered to consumer |

**Auto-flag logic:** When a complaint is created with severity = SAFETY, the system automatically sets `recall_triggered_flag = True` and `regulatory_report_required = True`. This is purely a flag — it does not create a recall.

### Endpoints (6 total — prefix: `/api/v1/consumer-complaints`)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/` | Create a complaint. SAFETY severity auto-sets recall_triggered_flag. Returns warning message if recall flagged. |
| `GET` | `/` | List complaints with filters: severity, status, lot_number, product_name, recall_only=true/false |
| `GET` | `/stats` | Summary counts: total, open, recall_triggered; breakdown by severity and by status |
| `GET` | `/{complaint_id}` | Full complaint detail |
| `PATCH` | `/{complaint_id}` | Update status, assigned_to, root_cause, corrective_action, recall fields. Auto-stamps acknowledged_at and resolved_at on status change. |
| `GET` | `/by-lot/{lot_number}` | All complaints for a lot number. Returns: total count, safety_count, whether any recall was triggered, full list. |

### Schema Status
Schemas are defined as inline Pydantic `BaseModel` classes inside the endpoint file (`ComplaintIn`, `ComplaintUpdate`). No dedicated `backend/app/schemas/consumer_complaints.py` exists.

### Service Layer Status
No dedicated service file. All database logic (SELECT, INSERT, UPDATE) is written directly inside the endpoint functions. This is an anti-pattern relative to other modules (e.g. recall has a 930-line dedicated service).

---

## System 2: Product Recall

### Location
- Models: `backend/app/models/traceability.py` (lines 228–520)
- Service: `backend/app/services/recall_service.py` (~980 lines)
- Endpoints: `backend/app/api/v1/endpoints/traceability.py`
- Frontend: `frontend/src/app/dashboard/traceability/recalls/`

### What It Does
The recall module is a full regulatory-grade product recall workflow. It can trace which lots were affected, calculate which customers received those lots, manage recovery of products, track regulatory reporting, and run AI agents to suggest scope expansion and prioritise customer risk.

### Data Models (9 models)

| Model | Purpose |
|---|---|
| `RecallHeader` | Master recall record. Stores recall number, type, reason, trigger source, severity, status, scope summary, timeline metrics (time_to_trace_hours, time_to_contain_hours), and link to originating complaint via `linked_complaint_id`. |
| `RecallScopeLine` | One row per affected product-lot combination. Tracks quantities: in_stock, shipped, returned, scrapped, quarantined, reworked. Tracks risk_status (low/medium/high/critical) and whether a hold has been placed. |
| `RecallAction` | Action items assigned to staff: quarantine, shipment_block, customer_notify, lab_test, regulatory_notify, etc. Tracks due_date, completion, and evidence notes. |
| `RecallCustomerImpact` | One row per customer who received an affected lot. Stores qty_delivered, risk_level, priority_rank (for triage), and notification tracking. |
| `RecallReturnRecord` | Records product returns from each customer: qty_requested, qty_confirmed, qty_received, qty_destroyed_at_customer, qty_quarantined_on_return. Tracks discrepancies and follow-up flags. |
| `TRRecAIRecommendation` | AI-generated recommendations from 3 agents: scope_validator (finds isolated lots), risk_prioritizer (flags uncontained critical lines), investigation_assistant (suggests backward trace on source lot). |
| `RecallCommunicationTemplate` | Pre-written message templates for different audiences (CONSUMER, RETAILER, REGULATOR, INTERNAL, MEDIA) with channel (EMAIL/SMS/WHATSAPP) and language support. |
| `RecallStatusLog` | Immutable audit log of every status change: from_status, to_status, changed_by_id, timestamp, reason, system_note. |
| `RecallEvidence` | File attachments and notes attached to a recall: lab reports, photos, regulatory correspondence, customer complaints. Evidence type includes CUSTOMER_COMPLAINT. |

### Recall Lifecycle (Status Flow)
```
draft → under_review → active → contained → in_progress → completed → closed
                                                          ↓
                                                       cancelled (from any active state)
```

### Key Fields on `RecallHeader`

| Field | Meaning |
|---|---|
| `recall_no` | Auto-generated unique reference (e.g. RCL-20260515-001) |
| `trigger_source` | qc / complaint / supplier_notice / audit / regulatory / manual |
| `linked_complaint_id` | UUID pointing to ConsumerComplaint — soft link only, no FK constraint |
| `source_lot_id` | The lot that triggered the recall — starting point for scope calculation |
| `total_affected_qty` | Sum across all RecallScopeLines |
| `recovery_pct` | Calculated from returns vs total shipped |
| `time_to_trace_hours` | How long it took to identify full scope after initiation |
| `time_to_contain_hours` | How long it took to place holds on all affected stock |

### Service Functions (recall_service.py — 30+ functions)

| Function | Purpose |
|---|---|
| `initiate_recall` | Creates RecallHeader. Accepts linked_complaint_id. Sets status to draft. |
| `calculate_scope` | Forward traces source_lot_id through shipments. Creates RecallScopeLines for each affected product-lot. |
| `contain_recall` | Places stock holds on all in-scope lots. Updates RecallScopeLine.hold_placed. |
| `build_customer_impact` | Generates RecallCustomerImpact rows by querying what was shipped to each customer from affected lots. |
| `notify_customer` | Marks notification_sent=True and records timestamp and method. |
| `record_return` | Creates RecallReturnRecord. Calls _update_recall_recovery to recalculate recovery_pct. |
| `close_recall` | Sets status to closed. Validates all required actions are complete. |
| `generate_regulatory_report` | Produces structured report data: scope summary, customer impact, recovery status, timeline. |
| `run_recall_ai_agents` | Runs all 3 AI agents sequentially. |
| `_run_scope_validator` | AI: checks for isolated lots (same product, same supplier batch) not in current scope. |
| `_run_risk_prioritizer` | AI: identifies high/critical scope lines where hold has not been placed. |
| `_run_investigation_assistant` | AI: suggests expanding scope by tracing backwards through supplier batches. |

### Endpoints (26 total — prefix: `/api/v1/traceability/recalls`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/dashboard` | Summary dashboard: active recalls, avg recovery, time metrics |
| `POST` | `/` | Initiate recall. Accepts linked_complaint_id in payload. |
| `GET` | `/` | List recalls with status filter |
| `GET` | `/{recall_id}` | Full recall detail |
| `PATCH` | `/{recall_id}/status` | Update recall status with reason |
| `POST` | `/{recall_id}/scope-calculate` | Run forward lot trace to populate RecallScopeLines |
| `POST` | `/{recall_id}/contain` | Place stock holds on all in-scope lots |
| `POST` | `/{recall_id}/actions` | Create a recall action (quarantine, notify, etc.) |
| `POST` | `/actions/{action_id}/complete` | Mark action complete with evidence |
| `GET` | `/{recall_id}/actions` | List recall actions |
| `POST` | `/{recall_id}/customer-impact/build` | Generate customer impact rows from scope |
| `GET` | `/{recall_id}/customer-impact` | List customer impact rows |
| `POST` | `/customer-impact/{impact_id}/notify` | Mark customer notified |
| `POST` | `/{recall_id}/returns` | Record product return from a customer |
| `GET` | `/{recall_id}/returns` | List return records |
| `POST` | `/{recall_id}/close` | Close recall (validates completeness) |
| `GET` | `/{recall_id}/regulatory-report` | Generate regulatory report data |
| `POST` | `/{recall_id}/run-ai-agents` | Run all 3 AI agents |
| `GET` | `/{recall_id}/ai-recommendations` | List AI recommendations |
| `POST` | `/ai-recommendations/{rec_id}/review` | Accept or reject AI recommendation |
| `GET` | `/recall-templates` | List communication templates |
| `POST` | `/recall-templates` | Create communication template |
| `PATCH` | `/recall-templates/{template_id}` | Update template |
| `GET` | `/{recall_id}/audit-log` | Immutable status change log |
| `GET` | `/{recall_id}/evidence` | List attached evidence |
| `POST` | `/{recall_id}/evidence` | Attach evidence (lab report, photo, etc.) |

---

## Current Linkage Between Systems

### What Works
- `RecallHeader.linked_complaint_id` stores the UUID of a complaint
- `RecallHeader.trigger_source` can be set to `complaint` when initiating
- The recall dashboard and detail view can display the linked complaint ID
- A complaint's `recall_ref` field can store a free-text recall reference

### What Does NOT Work

**1. No automatic recall creation from complaint**

When a consumer complaint is saved with severity = SAFETY:
```
ComplaintIn(severity=SAFETY) → recall_triggered_flag = True
```
Nothing else happens. No RecallHeader is created. The operator sees a warning message: *"SAFETY severity — recall flag auto-triggered. Review traceability module."* They must then manually navigate to Traceability, create a new recall, and type in the complaint ID by hand.

**2. No reverse query**

If you have a `ConsumerComplaint` record, you cannot ask: *"Has a recall been initiated for this complaint?"* There is no endpoint `GET /consumer-complaints/{id}/recall` and no DB query path from complaint to RecallHeader. The `recall_ref` field is a text field — it does not join to any recall table.

**3. No FK constraint**

`RecallHeader.linked_complaint_id` is a raw `UUID` column with no `ForeignKeyConstraint`. The database does not enforce that the UUID refers to a real `ConsumerComplaint.id`. A recall can be created with a non-existent complaint ID and no error is raised.

**4. No audit trail for escalation**

When a complaint is escalated to a recall, there is no immutable log entry recording: *"Complaint CC-001 escalated to recall RCL-001 at 2026-05-15T10:30 by user X."* The recall has a `RecallStatusLog` but it only tracks recall status changes, not the complaint-to-recall transition.

**5. No lot-based complaint surfacing in scope calculation**

When `calculate_scope` runs for a recall on lot `LOT-2026-001`, it traces forward through shipments. It does NOT query whether any prior complaints mention `lot_number = "LOT-2026-001"`. Those complaints could expand the known scope of the recall.

---

## Module Registration Gaps

### Consumer Complaints — CRITICAL
```python
# Current (wrong):
EndpointRouteDefinition(key="consumer_complaints", route_prefix="/consumer-complaints", ...)

# Needed:
ModuleDefinition(key="consumer_complaints", permission_actions=("view","create","edit","escalate","close","report"), ...)
```
Because it is an `EndpointRouteDefinition`, the `registry_permission_codes()` function does not generate any `consumer_complaints.*` codes. This means:
- No RBAC enforcement possible on complaint endpoints
- Admin role has no explicit grant for consumer complaints
- Sidebar nav item cannot be protected by a real permission code

### Recall — Partial
Recall endpoints live under the `traceability` EndpointRouteDefinition (not a ModuleDefinition). Only two scoped permissions exist:
- `traceability.recall_initiate` — granted to Quality Assurance Manager role
- `traceability.recall_close` — not yet assigned to any role seed

There is no `recall.view`, `recall.manage`, `recall.report` permission domain.

---

## Seed Permission Gaps

```python
# seed.py — consumer_complaints: MISSING (0 tuples)
# seed.py — recall: only 2 tuples under traceability
("traceability", "recall_initiate", ...)
("traceability", "recall_close", ...)
```

---

## Frontend Nav-Config Guards

The consumer complaints nav item in `frontend/src/components/nav-config.tsx` is gated by `quality.view` — a permission from a different module entirely. Since `consumer_complaints.*` codes do not exist, the only alternatives are a hardcoded `true` or borrowing another module's code. Both are incorrect.

---

## File Inventory

| File | Status | Notes |
|---|---|---|
| `backend/app/models/consumer_complaints.py` | Complete | 1 model, all fields present |
| `backend/app/models/traceability.py` | Complete | 9 recall models, full state machine |
| `backend/app/schemas/consumer_complaints.py` | **MISSING** | Schemas are inline in endpoint file |
| `backend/app/schemas/traceability.py` (recall) | Partial | Recall schemas exist but not centrally audited |
| `backend/app/services/recall_service.py` | Complete | ~980 lines, 30+ functions, 3 AI agents |
| `backend/app/services/consumer_complaint_service.py` | **MISSING** | Logic is inline in endpoints |
| `backend/app/api/v1/endpoints/consumer_complaints.py` | Complete | 6 endpoints, functional |
| `backend/app/api/v1/endpoints/traceability.py` | Complete | 26 recall endpoints, full workflow |
| `backend/app/core/module_registry.py` | **Gap** | consumer_complaints = EndpointRouteDefinition |
| `backend/app/db/seed.py` | **Gap** | No consumer_complaints permission tuples |
| `frontend/src/app/dashboard/quality/consumer-complaints/page.tsx` | Complete | List, stats, update |
| `frontend/src/app/dashboard/traceability/recalls/page.tsx` | Complete | Recall list |
| `frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx` | Complete | Recall detail |
| `frontend/src/app/dashboard/traceability/mock-recall/page.tsx` | Complete | Demo/test page |
| `frontend/src/components/nav-config.tsx` | **Gap** | Consumer complaints gated by wrong permission |

---

## Gap Summary

| # | Gap | Severity | Fix Required |
|---|---|---|---|
| 1 | consumer_complaints not in MODULE_DEFINITIONS | Critical | GAP-020I |
| 2 | No seed permissions for consumer_complaints | Critical | GAP-020I |
| 3 | Nav-config uses quality.view instead of consumer_complaints.view | Critical | GAP-020I |
| 4 | No FK constraint on RecallHeader.linked_complaint_id | Medium | Deferred (needs migration) |
| 5 | No auto-creation of recall from SAFETY complaint | Medium | Deferred (UX decision needed) |
| 6 | No reverse query: complaint → recall | Medium | Deferred |
| 7 | No audit trail for complaint-to-recall escalation | Medium | Deferred |
| 8 | No dedicated schema file for consumer_complaints | Low | GAP-020E |
| 9 | No service layer for consumer_complaints | Low | GAP-020F |
| 10 | Lot complaint history not queried during recall scope calculation | Low | Deferred |

---

## Recommended Fix Scope (GAP-020B–L)

| Sub-task | Decision | Output |
|---|---|---|
| GAP-020B — Schema Design | No new tables needed. Module promotion only. | Design doc |
| GAP-020C — Migration | SKIP — no schema changes | — |
| GAP-020D — Models | SKIP — models complete | — |
| GAP-020E — Schemas | Add `backend/app/schemas/consumer_complaints.py` | `ComplaintCreate`, `ComplaintUpdate`, `ComplaintRead` |
| GAP-020F — Services | Add `backend/app/services/consumer_complaint_service.py` | Extract 4 functions from endpoint handlers |
| GAP-020G — Endpoints | Thin out endpoint handlers to call service | Updated `consumer_complaints.py` |
| GAP-020H — Frontend | SKIP — pages complete | — |
| GAP-020I — Permissions | Promote to MODULE_DEFINITIONS; seed 6 permissions; fix nav-config | module_registry.py, seed.py, nav-config.tsx |
| GAP-020J — Tests | Module contract + schema contract + linkage tests | `test_gap020_consumer_complaint_recall.py` |
| GAP-020K — Docs | Implementation notes | `GAP-020_IMPLEMENTATION_NOTES.md` |
| GAP-020L — Checks | py_compile + pytest + registry smoke check | All pass |

---

## Known Limitations (Deferred — Out of Scope for GAP-020)

| Limitation | Reason Deferred |
|---|---|
| Auto-create RecallHeader when complaint is flagged SAFETY | Requires UX/workflow design decision — who approves, what defaults to use |
| Explicit FK constraint (linked_complaint_id → consumer_complaints.id) | Requires Alembic migration; low risk since soft-link UUID works for current use |
| Reverse lookup endpoint: GET /consumer-complaints/{id}/recall | Deferred to a future recall linkage enhancement sprint |
| Lot-complaint cross-reference in calculate_scope | Requires scope calculation refactor; separate initiative |
| Regulatory-specific complaint classification (KEBS Form C, FDA MedWatch) | Requires regulatory rules engine; separate initiative |
