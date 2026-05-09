# TASKS2.md



## Current Phase

Tier 4 — FMCG-Specific & Regulatory



## Current Gap

Gap 54 - HACCP System Expansion



## In Progress

Not started yet.



## Completed in Last Run

Gap 53 - Co-Packing / Toll Manufacturing

Gap 52 - Market Intelligence / Competitor Tracking



## Implemented Gap Items

1-53 implemented.



## Remaining Gap Items

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

Implement Gap 54 - HACCP System Expansion.

Inspect first:
- Check backend/app/models/quality.py + qms.py for existing HACCP models
- Check frontend/src/app/dashboard/qms/ for existing QMS pages

Gap 54 missing (from ERP_70_GAPS plan):
- HACCP plan PDF generation (stub)
- CCP trend analytics
- BRC / FSSC 22000 audit checklist
- HALAL / KOSHER compliance tracking
- Mock audit workflows
- Supplier food safety approval tracking

Build next coherent slice:
1. Inspect qms.py models — likely has CCP, HACCP plan, deviations.
2. Add AuditChecklist model (checklist_type: BRC/FSSC/HALAL/KOSHER/ISO22000, items JSONB, score, status, conducted_by, audit_date).
3. Add SupplierFoodSafetyApproval model (supplier_id/name, approval_type, status, expiry_date, auditor, score, notes).
4. Endpoints: audit checklists CRUD, stats, supplier food safety CRUD.
5. Frontend: HACCP expansion page with audit checklist runner + supplier approval tracker.
6. Nav under QMS & HACCP.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 53 additions:
backend/app/models/copacking.py - NEW: CoPackingContract (contract_ref, customer_name, contract_type COPACKING/TOLL_MFG/PRIVATE_LABEL, brand_name, start/end_date, MOQ, processing_fee_per_unit, status DRAFT/ACTIVE/SUSPENDED/EXPIRED/TERMINATED); CoPackingRun (run_ref, contract_id FK, run_date, qty_planned/produced, processing_fee_total auto-calc from contract rate); CustomerTool (tool_ref, customer_name, tool_name, tool_type, serial_number, units_produced, max_units_life, life_used_pct, depreciation_per_unit, status ACTIVE/IN_REPAIR/RETIRED/RETURNED)
backend/app/api/v1/endpoints/copacking.py - NEW: Contracts CRUD + status patch; Runs list/create (auto-calc fee from contract rate); Tools register/list; POST /tools/{id}/log-usage (increments units_produced, auto-RETIRED at max); GET /stats
backend/app/api/v1/router.py - MODIFIED: copacking route
frontend/src/app/dashboard/copacking/page.tsx - NEW: 5-tab page (Contracts/Tools/Runs/+Contract/+Tool). Contracts list with status badge. Tools table with life-used % bar (red ≥90%). Runs list with QC pass/fail badge.
frontend/src/components/nav-config.tsx - MODIFIED: Co-Packing / Toll under Subcontracting section

Gap 52 additions:
backend/app/models/market_intelligence.py - NEW: MarketObservation (obs_ref, outlet_name/type, location, category, our_facings/total_facings → auto shelf_share_pct, our_promo_active, competitor_promo_active, our_oos_flag); MarketShareEstimate (category, period_month YYYY-MM, our_share_pct, competitor_shares JSONB, total_market_value_kes, source)
backend/app/api/v1/endpoints/market_intelligence.py - NEW: POST/GET /market-intel/observations; GET /market-intel/shelf-share/summary (avg/OOS rate/comp_promo rate per category); GET /market-intel/dashboard; POST/GET /market-intel/market-share
backend/app/api/v1/router.py - MODIFIED: market_intelligence route
frontend/src/app/dashboard/market-intelligence/page.tsx - NEW: 5-tab page (Shelf Share Analytics/Field Observations/Market Share/Log Observation/Log Market Share). Shelf share table with color-coded bars. Market share table with competitor shares.
frontend/src/components/nav-config.tsx - MODIFIED: Market Intelligence under Analytics / BI



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 53)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 53 notes:
- CoPackingRun.processing_fee_total auto-calculated: contract.processing_fee_per_unit × qty_produced.
- CustomerTool.life_used_pct = units_produced / max_units_life × 100. Tool auto-RETIRED when units_produced ≥ max_units_life on log-usage call.
- stats.tools_near_end_of_life: active tools with units_produced ≥ 90% of max_units_life.

Gap 52 notes:
- shelf_share_pct auto-computed on create: our_facings / total_facings × 100.
- shelf-share summary groups by category, returns avg_shelf_share, OOS rate, competitor_promo rate per category.
- MarketShareEstimate.competitor_shares is JSONB: {brand: share_pct} dict.

Gap 54 start:
- Check backend/app/models/quality.py and qms.py — QMS has HACCP plans, CCPs, deviations.
- Don't duplicate existing QMS. Add what's MISSING: audit checklists (BRC/FSSC/HALAL/KOSHER) + supplier food safety approvals.
- AuditChecklist: predefined item sets per standard. Score = passed_items/total × 100.
