# TASKS — FMCG ERP (Kenya) · Production Module

## Current Phase
Phase 6 — Advanced Production Planning Suite ✅ COMPLETED

---

## Completed in This Run

### Phase 6 — Advanced Production Planning Suite ✅
- [x] `backend/app/models/planning.py` — PlanningScenario, ResourceCalendar, OperationQueue, CapacityLoadSnapshot, ChangeoverMatrix, PlanningBottleneck, PlanningAIRec, PlanningSimulation (8 models, 8 enums)
- [x] `backend/app/schemas/planning.py` — all Pydantic request/response schemas
- [x] `backend/app/services/planning_scenario_service.py` — CRUD, activate/lock/archive, dashboard aggregation
- [x] `backend/app/services/planning_capacity_service.py` — greedy finite scheduling engine (ATCS rule, working-day calendar, changeover lookup, slot_map → CapacityLoadSnapshot)
- [x] `backend/app/services/planning_bottleneck_service.py` — detect/list/resolve bottlenecks (4 severity levels, recommendation text)
- [x] `backend/app/services/planning_simulation_service.py` — create/compute/publish simulations (in-memory delta)
- [x] `backend/app/services/planning_ai_service.py` — 3 agents: CAPACITY_OPTIMIZER, SEQUENCING_OPTIMIZER, DISRUPTION_PREDICTOR
- [x] `backend/app/api/v1/endpoints/planning.py` — 22 routes at /api/v1/planning/
- [x] `backend/app/api/v1/router.py` — wired planning router
- [x] `backend/app/models/__init__.py` — all 8 planning models exported
- [x] `frontend/src/lib/planning.ts` — types + API client + color/label maps
- [x] `frontend/src/app/dashboard/planning/page.tsx` — Planning Dashboard (KPIs, scenario list, top bottlenecks, AI recs, create modal)
- [x] `frontend/src/app/dashboard/planning/schedule/page.tsx` — Schedule Board (per-WC grouping, Gantt-style table, calculate trigger, op detail modal)
- [x] `frontend/src/app/dashboard/planning/capacity/page.tsx` — Capacity Board (heatmap grid, overload alerts, utilization bars)
- [x] `frontend/src/app/dashboard/planning/bottlenecks/page.tsx` — Bottleneck Explorer (severity cards, AI recs with accept/reject, resolve modal)
- [x] `frontend/src/app/dashboard/planning/simulation/page.tsx` — Simulation Sandbox (op selector, staged changes, impact display, publish flow)
- [x] `frontend/src/app/dashboard/planning/changeover/page.tsx` — Changeover Matrix (grid heatmap + flat list + add modal)
- [x] `frontend/src/components/nav-config.tsx` — "Advanced Planning Suite" section added to Planning & Intelligence cluster

### Phase 4 — MRP Engine + Demand Forecasting ✅
- [x] `backend/app/models/mrp.py` — DemandForecast, DemandForecastLine, MRPRun, MRPResult, MRPSuggestion
- [x] `backend/app/schemas/mrp.py` — all Pydantic schemas
- [x] `backend/app/services/forecast_service.py` — 5 forecast models + MAPE + spike detection
- [x] `backend/app/services/mrp_service.py` — BOM explosion, net requirements, PR/PO creation
- [x] `backend/app/api/v1/endpoints/mrp.py` — 17 routes at /api/v1/mrp/
- [x] `frontend/src/lib/mrp.ts` — types + API client
- [x] `frontend/src/app/dashboard/mrp/` — 4 pages: dashboard, run, suggestions, forecast

### Phase 4b — Backend Startup Bugfixes ✅
- [x] `pydantic-settings` not installed → installed via pip
- [x] `AlarmDetectionType`, `AlarmCategory` missing from utility_management.py → added 5-value enum + AlarmCategory
- [x] `UtilityAlarmRule` missing `alarm_category`, `detection_type` columns → added
- [x] `UtilityAlarmEvent` missing `assigned_to_id`, `assigned_to` → added FK + relationship
- [x] Broken git sync scripts (PS1 `$Args` reserved variable bug) → replaced with clean `sync-to-github.bat` + `setup-autosync.bat`
- [x] router.py wired: `utility_alarm`, `utility_kpi`, `mrp` endpoints
- [x] models/__init__.py wired: MRP + MPS model exports

### Phase 5 — Master Production Scheduling (MPS) Engine ✅
- [x] `backend/app/models/mps.py`
  - `MPSPlan` — plan header (mode, status, capacity_mode, MRP linkage)
  - `MPSLine` — per-product per-period production lines
  - `MPSCampaign` — SKU campaign groupings (FMCG changeover optimization)
  - `MPSCapacitySlot` — daily capacity utilization per work center
  - `MPSWhatIfScenario` — what-if simulation (changes + computed impact)
  - `MPSAIRecommendation` — AI optimizer + risk predictor outputs
- [x] `backend/app/schemas/mps.py` — all request/response schemas
- [x] `backend/app/services/mps_service.py`
  - `create_mps_plan`, `list_mps_plans`, `get_mps_plan`
  - `generate_mps_from_mrp` — import MRP results as weekly/monthly/daily lines
  - `approve_mps_plan`, `release_mps_plan` — creates ProductionOrders
  - `get_mps_dashboard` — KPI aggregation
- [x] `backend/app/services/mps_capacity_service.py`
  - `run_capacity_scheduling` — finite/infinite mode, distributes hours across working days
  - `get_capacity_heatmap` — per-WC per-day utilization matrix
  - `suggest_reschedule` — finds earliest available window for overloaded line
- [x] `backend/app/services/mps_campaign_service.py`
  - `run_campaign_grouping` — product code prefix clustering
  - Sequence optimization (light→dark by code)
  - Changeover time estimation from WC setup_time_min
- [x] `backend/app/services/mps_whatif_service.py`
  - `create_whatif_scenario` — applies changes to in-memory snapshots
  - Computes service level, delay count, cost delta
- [x] `backend/app/services/mps_ai_service.py`
  - Agent 1 OPTIMIZER: sequence reordering, batch merge, campaign consolidation
  - Agent 2 RISK PREDICTOR: capacity overload, late delivery, material shortage, urgent deadlines
  - `run_all_ai_agents` — orchestrator
  - `review_recommendation` — accept/reject workflow
- [x] `backend/app/api/v1/endpoints/mps.py` — 20 routes at /api/v1/mps/
- [x] `frontend/src/lib/mps.ts` — types, API client, color/label maps
- [x] `frontend/src/app/dashboard/mps/page.tsx` — MPS Dashboard (KPIs, overload alerts, recent plans, quick nav)
- [x] `frontend/src/app/dashboard/mps/planning-board/page.tsx` — Planning Board (lines table, override modal, approve/release)
- [x] `frontend/src/app/dashboard/mps/capacity/page.tsx` — Capacity Heatmap (grid + overload panel + utilization bars)
- [x] `frontend/src/app/dashboard/mps/campaigns/page.tsx` — Campaign View (sequence, SKU lists, efficiency metrics)
- [x] `frontend/src/app/dashboard/mps/whatif/page.tsx` — What-If Simulator (scenario builder, change staging, impact display)
- [x] Nav-config: "Planning & Intelligence" cluster with MRP + MPS sections

---

## Next Immediate Tasks

### Phase 6 — Advanced Production Planning Suite ✅ COMPLETED
(see Completed in This Run above)

### Phase 7 — MPS → Shop Floor Execution Chain
- [ ] Production Order → Work Order auto-creation on planning scenario publish
- [ ] Shop floor execution: start/complete work orders from schedule board
- [ ] Real-time progress tracking per OperationQueue entry

### Phase 7 — Procurement Integration (MRP → PR auto-creation)
1. Material shortage event logging when `_issue_material()` raises INSUFFICIENT_MATERIAL
2. `GET /production/material-shortages` endpoint
3. Frontend alert banner on production order detail page
4. Link MPS → MRP → PR auto-creation workflow

### Phase 8 — Enhanced Reports
1. Daily production summary (line output, efficiency, waste, downtime per shift)
2. Line efficiency report (OEE by machine by shift, period comparison)
3. Cost variance report (actual vs standard by product)
4. MPS vs actual: planned vs delivered per period

## Blockers
- None — `python -c "from app.main import app; print('OK')"` passes cleanly

## DB Migrations Needed
- `alembic revision --autogenerate -m "planning_suite"` — creates: planning_scenarios, resource_calendars, operation_queue, capacity_load_snapshots, changeover_matrix, planning_bottlenecks, planning_ai_recs, planning_simulations
- Run after MPS migration: `alembic revision --autogenerate -m "mps_engine"` (if not yet done)

## Architecture Notes
- MPS Plan → MPSLine links to MRPResult (via mrp_result_id)
- MPSLine.work_center_id → WorkCenter (production_advanced)
- Capacity: 8h/day default (Mon–Sat), throughput from WorkCenter.capacity (units/hr)
- Campaign key: first 6 chars of product code → FMCG family grouping
- What-If: in-memory snapshot computation (never touches live plan data)
- AI agents: never auto-apply, always await planner accept/reject
- DB migration needed: `alembic revision --autogenerate -m "mps_engine"` before first use

---

## Previously Completed Phases

---

## Completed in Last Run

### Phase 0 — Inventory Bugfixes (Previous Session)
- [x] Product deletion: structured 409 dependency error, `products.delete` permission
- [x] Inventory page: Adjust + Delete actions with permission guards
- [x] Movements page: Edit + Delete actions with permission guards
- [x] Backend: `adjust_stock_record`, `delete_stock_record`, `delete_movement_record` service methods
- [x] New permissions seeded: `products.delete`, `stock_movement.edit`, `stock_movement.delete`
- [x] Fix: `adjust_stock_record` hardcoded `StockType.PRODUCT`, missed `material_id`; zero-delta now raises 422

### Phase 1 — Utility Management (Previous Sessions)
- [x] Electricity module (backend + frontend)
- [x] Water module (backend + frontend)
- [x] Soft Water module (backend + frontend)
- [x] Steam & Boiler module (backend + frontend)
- [x] Compressor & Compressed Air module (backend + frontend)
- [x] Bulk import adapters for all 5 utility modules
- [x] Nav-config updates for all utility sections

### Phase 2 — Production Costing Engine (This Run)
- [x] Alembic migration `c8d9e0f1a2b3_production_costing.py`
  - Added `total_material_cost`, `total_labor_cost`, `total_machine_cost`, `total_energy_cost`,
    `total_cost`, `cost_per_unit`, `standard_cost_per_unit`, `cost_variance_pct`,
    `costing_finalized_at` to `production_orders`
  - Added `labor_rate_per_hour`, `machine_cost_per_hour` to `work_centers`
- [x] Updated `ProductionOrder` model (production.py) with costing columns
- [x] Updated `WorkCenter` model (production_advanced.py) with rate columns
- [x] `backend/app/services/production_cost_service.py`
  - `compute_order_cost()` — live cost breakdown from DB joins (material × std_cost, labor × rate, machine × duration, energy from utility_tx)
  - `finalize_order_cost()` — persist computed costs to order record (COMPLETED orders only)
  - `get_cost_kpis()` — aggregated dashboard KPIs with anomaly flags
  - `get_cost_report()` — per-product aggregated cost report
  - `get_cost_trend()` — daily stacked cost trend
- [x] `backend/app/schemas/production_costing.py` — `OrderCostBreakdown`, `CostReportRow`, `CostTrendPoint`, `CostKPIs`
- [x] `backend/app/api/v1/endpoints/production_costing.py`
  - `GET  /production-cost/kpis`
  - `GET  /production-cost/report`
  - `GET  /production-cost/trend`
  - `GET  /production-cost/orders/{id}/cost`
  - `POST /production-cost/orders/{id}/finalize`
- [x] Router registered at `/production-cost`
- [x] `frontend/src/lib/productionCosting.ts` — types + API client + `fmtKES`, `fmtVariance`, `buildBreakdownPie`
- [x] `frontend/src/app/dashboard/production/costing/page.tsx`
  - 8 KPI cards (total cost, avg cost/unit, variance %, over-budget count, material/labor/machine/energy split)
  - Stacked AreaChart — daily cost trend (material + labor + machine + energy)
  - PieChart — cost breakdown with % labels
  - Product cost report table (12 columns including variance coloring)
  - Finalize order cost modal
- [x] Nav-config expanded Production section: Work Centers, Scheduling, OEE Records, Waste & Yield, Batch/Lots, Costing

---

### Phase 3 — AI Production Intelligence (This Run) ✅
- [x] `alembic/versions/d9e0f1a2b3c4_production_ai.py`
  - `ai_predictions` — Agent 1 output per order (risk_level, delay_risk_pct, efficiency_forecast_pct, confidence, explanation)
  - `ai_anomalies` — Agent 2 detections (type, severity, deviation_pct, is_resolved)
  - `ai_suggestions` — Agent 3/4/5/6 output (status: pending/accepted/rejected/applied)
  - `ai_model_metrics` — per-agent accuracy tracking
- [x] `backend/app/models/production_ai.py` — ProductionPrediction, ProductionAnomaly, ProductionSuggestion, ProductionAIMetrics
- [x] `backend/app/models/__init__.py` — registered all new models + production_advanced models
- [x] `backend/app/services/production_ai_service.py` — 6 agents:
  - Agent 1: PREDICTION — linear extrapolation from historical duration/qty ratios, delay_rate_pct from past orders
  - Agent 2: ANOMALY — material Z-score vs BOM standard, OEE rolling average drop, downtime spike vs MTBF, waste Z-score, QC fail rate spike
  - Agent 3: OPTIMIZATION — batch size efficiency analysis, work center utilization balancing
  - Agent 4: RECIPE — QC fail rate per recipe (90-day), top-cost ingredient identification
  - Agent 5: COST — cost-per-unit trend comparison (recent 30d vs prior 30d)
  - Agent 6: MAINTENANCE — MTBF calculation from downtime event intervals, failure prediction
  - `run_all_agents()` orchestrator, `get_ai_dashboard()`, resolve/action helpers
- [x] `backend/app/schemas/production_ai.py` — all output schemas with confidence_score + explanation
- [x] `backend/app/api/v1/endpoints/production_ai.py` — 14 routes
- [x] Router registered at `/production-ai`
- [x] `frontend/src/lib/productionAi.ts` — types + API client + label/color maps
- [x] `frontend/src/app/dashboard/production/ai/page.tsx`
  - 5 tabs: Overview · Anomalies · Suggestions · Predictions · Maintenance
  - Overview: KPI cards, critical alert panel, pending suggestions quick-action
  - Anomalies: severity badges, deviation display, resolve modal
  - Suggestions: accept/reject with actioned_by tracking, confidence bars, impact metrics
  - Predictions: table with risk level badge, delay%, efficiency%, error% tracking
  - Maintenance: MTBF display, predicted failure time, accept/dismiss
- [x] Nav-config: "AI Intelligence" added to Production section

---

## Next Immediate Tasks

### Phase 4 — Procurement Integration

### Phase 4 — Procurement Integration
1. Material shortage event logging when `_issue_material()` raises INSUFFICIENT_MATERIAL
2. `GET /production/material-shortages` endpoint — orders with materials below reorder
3. Frontend alert banner on production order detail page
4. Link to procurement module: auto-suggest PR creation for short materials

### Phase 5 — Enhanced Reports
1. Daily production summary (line output, efficiency, waste, downtime per shift)
2. Line efficiency report (OEE by machine by shift, period comparison)
3. Cost variance report (actual vs standard by product, trend vs budget)
4. Waste analysis (type, category, material, abnormal event list)

### Phase 6 — Role-based Access
1. Production Manager — full CRUD + costing finalization
2. Operator — start/complete work orders, log time, update quantities
3. QC Inspector — create/update QC inspections + results
4. Accounting — read-only costing reports

---

## Architecture Notes
- Costing uses `Material.standard_cost` as raw material unit price
- Labor rate: `WorkCenter.labor_rate_per_hour` (KES/hr)
- Machine rate: `WorkCenter.machine_cost_per_hour` (KES/hr)
- Energy cost linked via `UtilityTransaction.batch_id = ProductionOrder.batch_no`
- Cost finalization is idempotent — re-running updates stored values
- All monetary values in KES (Kenyan Shillings)
- Migration chain: … → b7c8d9e0f1a2 (compressor) → c8d9e0f1a2b3 (costing)

## Blockers
- None
