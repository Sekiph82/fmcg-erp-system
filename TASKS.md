# TASKS — FMCG ERP (Kenya) · Production Module

## Current Phase
Phase 3 — AI Production Intelligence Layer ✅ COMPLETED

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
