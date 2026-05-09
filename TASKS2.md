# TASKS2.md



## Current Phase

Tier 4 — FMCG-Specific & Regulatory



## Current Gap

Gap 47 - Route Optimization for Van Sales



## In Progress

Not started yet.



## Completed in Last Run

Gap 46 - New Product Development Workflow

Gap 45 - Returnable Packaging / Container Management

Gap 44 - Integration Marketplace / Connector Hub



## Implemented Gap Items

1-46 implemented.



## Remaining Gap Items

47. Route Optimization for Van Sales

48. Consumer Complaint Management Linked to Batch

49. Regulatory Certificate Tracking

50. Dynamic / AI Pricing Engine

51. Brand Asset / Label Design Management

52. Market Intelligence / Competitor Tracking

53. Co-Packing / Toll Manufacturing

54. HACCP System Expansion

55. Allergen & Nutrition Management

56. GS1 Barcode & Labeling Advanced

57. Shelf-Life / FEFO Control Expansion

58. Trade Promotion Management Expansion

59. Secondary Sales / Distributor Sell-Through Expansion

60. Kenya Localization Expansion

61. IoT / Real-Time Machine Data Streaming

62. ML-Based Demand Forecasting Engine

63. Blockchain-Based Traceability

64. Carbon Footprint Per Product

65. AI-Powered Receipt OCR

66. Natural Language ERP Control

67. AI Agent Governance Framework

68. Predictive Maintenance

69. ESG Intelligence & Sustainability Optimization

70. Plugin / App Marketplace Architecture



## Next Immediate Task

Implement Gap 47 - Route Optimization for Van Sales.

Inspect first:
- Van sales already has route model (SalesRoute, RouteStop in field_sales.py)
- Check backend/app/api/v1/endpoints/field_sales.py and van_sales.py for existing route endpoints
- Check frontend/src/app/dashboard/van-sales/route/ for existing route UI

Gap 47 missing:
- Route optimization algorithm (nearest-neighbor / Clarke-Wright)
- Traffic-aware routing (Google Maps link generation)
- Visit prioritization (revenue-based ranking of stops)
- Route profitability analytics
- Dynamic re-routing (mark customer unavailable, skip)

Build next coherent slice:
1. Add GET /van-sales/routes/{route_id}/optimize endpoint — runs nearest-neighbor algorithm on existing route stops, returns reordered stop sequence.
2. Add POST /van-sales/routes/{route_id}/apply-optimization — persists reordered sequence_no to RouteStop records.
3. Add GET /van-sales/routes/profitability — revenue per route, cost estimate (km × fuel rate).
4. Frontend: route optimizer page — show current vs optimized sequence, apply button, Google Maps link.
5. Wire nav.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 46 additions:
backend/app/models/npd.py - NEW: NPDProject (project_code, name, category, stage IDEA/CONCEPT/DEVELOPMENT/PILOT/LAUNCH/LAUNCHED/CANCELLED, target_launch_date, estimated_cogs/selling_price, bom_recipe_id, regulatory_checklist JSONB, launch_readiness_checklist JSONB); NPDStageGate (project_id, stage, department, approved_flag, approved_by, approved_at); NPDPilotBatch (project_id, batch_ref, batch_no, qty_produced, uom, actual_cogs, outcome PASS/FAIL/CONDITIONAL/IN_PROGRESS)
backend/app/api/v1/endpoints/npd_workflow.py - NEW: POST/GET /npd-workflow/projects; GET /npd-workflow/projects/{id} (with stage_gates + pilot_batches); PATCH /npd-workflow/projects/{id}; POST /npd-workflow/projects/{id}/advance-stage (checks all current gates approved); POST /npd-workflow/projects/{id}/gates/{gate_id}/approve; PATCH /npd-workflow/projects/{id}/checklist; POST /npd-workflow/projects/{id}/pilot-batches; GET /npd-workflow/dashboard
backend/app/api/v1/router.py - MODIFIED: npd_workflow import + /npd-workflow route
frontend/src/app/dashboard/npd/page.tsx - NEW: NPD hub — KPI strip, stage filter bar, project cards (stage badge, COGS, launch date), new project form
frontend/src/app/dashboard/npd/[id]/page.tsx - NEW: NPD project detail — stage advance button (blocked until all gates approved), gate approval list with approver input, regulatory + launch checklists (checkbox toggle), pilot batches list + add form
frontend/src/components/nav-config.tsx - MODIFIED: Added New Product Development section under Planning cluster

Gap 45 additions:
backend/app/models/containers.py - NEW: ContainerType, ContainerIssuance, ContainerReturn
backend/app/api/v1/endpoints/containers.py - NEW: Full container CRUD + issue/return/write-off/stats
backend/app/api/v1/router.py - MODIFIED: containers route
frontend/src/app/dashboard/containers/page.tsx - NEW: Container hub
frontend/src/app/dashboard/containers/outstanding/page.tsx - NEW: Outstanding tracker
frontend/src/components/nav-config.tsx - MODIFIED: Container nav links

Gap 44 additions:
backend/app/models/integrations.py - MODIFIED: ConnectorRegistry model
backend/app/api/v1/endpoints/integrations.py - MODIFIED: Marketplace endpoints
frontend/src/app/dashboard/integrations/marketplace/page.tsx - NEW
frontend/src/components/nav-config.tsx - MODIFIED: Marketplace nav link



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 46)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 46 notes:
- NPDProject.project_code auto-generated as NPD-YYYYMM-XXXX (random 4 digits).
- Stage advancement blocked if any gate in current stage is unapproved. Gate seeding: 5 departments auto-created per stage on project create (IDEA) and on each advance.
- regulatory_checklist default keys: allergen_review, label_approved, kebs_check, haccp_review, nutritional_calc.
- launch_readiness_checklist default keys: bom_approved, label_signed_off, production_plan, sales_plan, regulatory_clearance, pricing_approved.
- Checklist PATCH toggles individual keys; JSONB field updated in-place.

Gap 47 start:
- field_sales.py has SalesRoute (route_id, name, rep_id, status) and RouteStop (route_id, stop_sequence, customer_id, lat, lon, estimated_arrival).
- Check what lat/lon fields exist on RouteStop — needed for nearest-neighbor distance calc.
- Nearest-neighbor algorithm: start from first stop, greedily pick closest unvisited stop using Haversine distance.
- Avoid installing scipy/numpy — implement Haversine in pure Python.
