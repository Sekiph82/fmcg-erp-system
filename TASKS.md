# TASKS — FMCG ERP (Kenya) · Production Module

## Current Phase
Phase 11 — Quality Checkpoints + Release Logic + HACCP / Food Safety ✅ COMPLETED

---

## Phase 11 — Quality Checkpoints + Release Logic + HACCP / Food Safety ✅

- [x] `backend/app/models/quality.py` — Extended with 9 new enums + 11 new models:
  - New enums: SamplingMethod, HazardType, RiskLevel, DeviationStatus, CorrectiveActionStatus, ReleaseStatus, QMSAIAgentType, QMSAIRecStatus
  - Extended QCType with RETEST; QCInspection extended with template_id, qc_sub_type, work_order_id, is_mandatory, blocks_progression, release_required, hold_flag
  - QCTemplate + QCTemplateParameter — reusable inspection templates per item/stage/category
  - HazardAnalysis — HACCP hazard records with likelihood × severity risk scoring
  - CriticalControlPoint — CCP definitions with critical limits, monitoring, and corrective action
  - CCPMonitoringLog — real-time monitoring entries with auto-violation detection
  - CorrectiveAction + CorrectiveActionStep — CA workflow with step-by-step tracking
  - QCDeviation — deviation records linked to inspections/lots/products
  - LotQualityStatus — per-lot release gate controlling FEFO eligibility and shipment
  - AllergenValidationRecord — allergen cleaning validation between production runs
  - QMSAIRecommendation — 3 AI agent recommendations with review workflow
- [x] `backend/app/schemas/qms.py` — Pydantic v2 schemas for all QMS models
- [x] `backend/app/services/qms_service.py`:
  - QC Template CRUD
  - Sampling plan calculation (fixed/percentage/frequency/time-based)
  - QC gate check — blocks progression if mandatory QC is pending or failed
  - Lot hold and release with FEFO/shipment eligibility flags
  - Lot quality status sync from inspection decision
  - HACCP hazard analysis creation with risk score calculation
  - CCP creation with auto-number
  - CCP limit checking with violation detection
  - CCP monitoring recording with auto corrective action creation on violation
  - Auto corrective action creation from CCP violations (steps parsed from CA description)
  - Deviation creation and auto-creation from failed inspections
  - Allergen validation creation
  - QMS dashboard aggregation (17 KPIs)
  - AI Agent 1: Quality Risk Predictor — high failure rate lots, open deviations
  - AI Agent 2: Deviation Analyzer — recurring type patterns, repeated CCP violations
  - AI Agent 3: HACCP Assistant — missing CCPs for high-risk hazards, unmonitored CCPs, allergen CCP gaps
- [x] `backend/app/api/v1/endpoints/qms.py` — 40+ routes at /api/v1/qms/:
  - GET /qms/dashboard
  - GET /qms/gate-check — lot progression gate check
  - CRUD /qms/templates + /qms/templates/{id}
  - CRUD /qms/haccp/hazards + /qms/haccp/hazards/{id}
  - CRUD /qms/haccp/ccp + /qms/haccp/ccp/{id}
  - GET /qms/haccp/ccp/{id}/logs, POST /qms/haccp/monitoring
  - GET /qms/haccp/violations
  - CRUD /qms/deviations + /qms/deviations/{id}
  - CRUD /qms/corrective-actions + steps completion + verification
  - GET/POST /qms/lot-status, /qms/lot-status/release, /qms/lot-status/hold
  - CRUD /qms/allergen-validations
  - GET/POST /qms/ai/recommendations + run endpoints (3 agents)
  - Reports: /qms/reports/qc-summary, ccp-violations, deviations, lot-quality
- [x] `backend/app/models/__init__.py` — all new models + enums exported
- [x] `backend/app/api/v1/router.py` — /api/v1/qms wired
- [x] `frontend/src/lib/qms.ts` — types, API client (35+ methods), color maps
- [x] `frontend/src/app/dashboard/qms/page.tsx` — QMS Dashboard (5 KPI sections, quick nav)
- [x] `frontend/src/app/dashboard/qms/inspections/page.tsx` — QC Inspection list with type/status filters
- [x] `frontend/src/app/dashboard/qms/templates/page.tsx` — QC Template editor with parameter viewer
- [x] `frontend/src/app/dashboard/qms/haccp/page.tsx` — HACCP Hazard Analysis with new record form
- [x] `frontend/src/app/dashboard/qms/ccp/page.tsx` — CCP Monitoring Dashboard with live monitoring entry
- [x] `frontend/src/app/dashboard/qms/deviations/page.tsx` — Deviation Management with resolve workflow
- [x] `frontend/src/app/dashboard/qms/corrective-actions/page.tsx` — CA Tracker with step completion and verification
- [x] `frontend/src/app/dashboard/qms/quarantine/page.tsx` — Quarantine/Hold Management with release modal
- [x] `frontend/src/app/dashboard/qms/allergen/page.tsx` — Allergen Validation records
- [x] `frontend/src/app/dashboard/qms/ai/page.tsx` — AI Quality Agents (run, review, accept/reject)
- [x] `frontend/src/app/dashboard/qms/reports/page.tsx` — QMS Reports (4 report panels)
- [x] `frontend/src/components/nav-config.tsx` — "QMS & HACCP" section with 11 nav links

**DB MIGRATION NEEDED:** `alembic revision --autogenerate -m "qms_haccp_system"` then `alembic upgrade head`

## Next Immediate Task: Prompt 12 — GS1 Barcode + Label Printing

## In Progress
- None — Prompt 11 complete

## Blockers
- None

---

## Phase 10 — Full Lot Traceability + Batch Recall Management ✅ COMPLETED

---

## Completed in This Run

### Phase 10 — Lot Traceability + Batch Recall Management ✅
- [x] `backend/app/models/traceability.py` — 9 models, 13 enums:
  - Enums: TraceEventType(13), TraceItemStage(13), GenealogyRelType(10), RecallType(5),
    RecallTrigger(6), RecallSeverity(4), RecallStatus(8), RecallActionType(11),
    RecallActionStatus(5), RecallRiskStatus(4), TRRecAIAgentType(3), TRRecAIRecStatus(4)
  - TraceEvent — immutable event header (receipt/issue/transformation/packaging/shipment/rework/scrap)
  - TraceEventLine — source_lot → child_lot movement per event with stage, quantity, customer/supplier links
  - LotGenealogyLink — directed graph edge (parent_lot → child_lot) with rel_type and quantity
  - RecallHeader — full recall header with time-to-trace, effectiveness, recovery_pct
  - RecallScopeLine — per-lot affected quantities by state (stock/transit/shipped/returned/quarantined/scrapped/reworked)
  - RecallAction — 11 action types with due date, completion, evidence
  - RecallCustomerImpact — per-customer delivery/notification/return tracking
  - RecallReturnRecord — quantity return tracking with discrepancy and follow-up flags
  - TRRecAIRecommendation — 3 AI agents (scope_validator, risk_prioritizer, investigation_assistant)
- [x] `backend/app/schemas/traceability.py` — all Pydantic v2 request/response schemas
- [x] `backend/app/services/traceability_service.py`:
  - Trace event create with auto-genealogy link creation
  - List events by lot or event type
  - Genealogy link CRUD + directional list
  - Forward trace BFS engine (descendant lots → shipments → customers, quantity by state)
  - Backward trace BFS engine (ancestor lots → production orders → suppliers → GRNs)
  - Genealogy tree builder (directed graph nodes + edges, stage summary)
  - Traceability search by lot number / batch / product / material / supplier / customer
- [x] `backend/app/services/recall_service.py`:
  - Recall initiation with auto-generated recall number
  - Recall status update workflow (draft → under_review → active → contained → completed → closed)
  - Scope calculation: forward-traces all source lots, builds per-lot RecallScopeLine records
  - Containment: places is_blocked=True on all affected Stock records, records hold timestamps
  - Recall action CRUD + completion workflow with evidence capture
  - Customer impact building from shipment trace event lines
  - Customer notification tracking
  - Return recording with discrepancy computation and follow-up flags
  - Recovery % auto-update on each return
  - Recall close with effectiveness score
  - Regulatory report generation (narrative summary + lot list + actions + metrics)
  - Recall dashboard KPIs
  - 3 AI agents: ScopeValidator, RiskPrioritizer, InvestigationAssistant
- [x] `backend/app/api/v1/endpoints/traceability.py` — 28 routes at /api/v1/traceability/
- [x] `backend/app/api/v1/router.py` — wired traceability router
- [x] `backend/app/models/__init__.py` — all 9 models + 13 enums exported
- [x] `frontend/src/lib/traceability.ts` — types, API client (32 methods), label/color maps
- [x] `frontend/src/app/dashboard/traceability/page.tsx` — Recall Dashboard (KPIs, recent recalls, quick nav)
- [x] `frontend/src/app/dashboard/traceability/search/page.tsx` — Trace Search Console (multi-field, results with trace links)
- [x] `frontend/src/app/dashboard/traceability/backward/page.tsx` — Backward Trace Viewer (ancestor lots, POs, suppliers, GRNs)
- [x] `frontend/src/app/dashboard/traceability/forward/page.tsx` — Forward Trace Viewer (qty breakdown, descendant lots, shipments)
- [x] `frontend/src/app/dashboard/traceability/genealogy/page.tsx` — Genealogy Graph/Tree (table + node view, stage summary)
- [x] `frontend/src/app/dashboard/traceability/recalls/page.tsx` — Recall List (all recalls, status filters, initiate modal)
- [x] `frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx` — Recall Detail (6-tab: overview/scope/actions/customers/returns/AI)
- [x] `frontend/src/app/dashboard/traceability/mock-recall/page.tsx` — Mock Recall Drill (end-to-end timed drill, effectiveness score)
- [x] `frontend/src/app/dashboard/traceability/regulatory/page.tsx` — Regulatory Report (print-ready, recall summary, actions, metrics)
- [x] `frontend/src/components/nav-config.tsx` — "Traceability & Recall" cluster + 8 nav links

**DB MIGRATION NEEDED:** `alembic revision --autogenerate -m "lot_traceability_recall"` then `alembic upgrade head`

---

## Next Immediate Task: Prompt 11 — Quality Checkpoints + Release Logic + HACCP / Food Safety

## In Progress
- None — Prompt 10 complete

## Blockers
- None — `python -c "from app.main import app; print('OK')"` passes cleanly

---

## Phase 9 — FEFO + Shelf-Life Control ✅ COMPLETED

- [x] 10 models, 15 enums
- [x] FEFO ranking engine, expiry validation, retest, disposition, compliance audit, 3 AI agents
- [x] 39 routes at /api/v1/shelf-life/
- [x] 12 frontend pages

---

## Phase 8 — Machine + Operator Intelligence ✅ COMPLETED
## Phase 7 — Material Flow Engine ✅ COMPLETED
## Phase 6 — Advanced Production Planning Suite ✅ COMPLETED
## Phase 5 — MPS Engine ✅ COMPLETED
## Phase 4 — MRP + Demand Forecasting ✅ COMPLETED
## Phase 3 — AI Production Intelligence ✅ COMPLETED
## Phase 2 — Production Costing Engine ✅ COMPLETED
## Phase 1 — Utility Management ✅ COMPLETED
## Phase 0 — Inventory Bugfixes ✅ COMPLETED

---

## Architecture Notes
- Genealogy is a directed graph: TraceEvent creation auto-creates LotGenealogyLink edges
- Forward/backward trace uses BFS with visited-set to prevent cycles
- Recall scope calculation runs forward_trace from source lot(s) — builds RecallScopeLine per lot
- Containment: sets Stock.is_blocked = True for all stocks associated with scope lot IDs
- RecallCustomerImpact built from TraceEventLine records with event_type=shipment
- TRRecAIRecommendation always requires human review before any action is taken
- Mock recall drill records effectiveness_score from time-to-trace performance
- All monetary values in KES; all quantities in item-native UOM
- DB migration needed: `alembic revision --autogenerate -m "lot_traceability_recall"` before first use
