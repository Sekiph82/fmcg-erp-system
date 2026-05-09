# TASKS2.md



## Current Phase

Tier 4 — FMCG-Specific & Regulatory



## Current Gap

Gap 56 - GS1 Barcode & Labeling Advanced



## In Progress

Not started yet.



## Completed in Last Run

Gap 55 - Allergen & Nutrition Management

Gap 54 - HACCP System Expansion

Gap 53 - Co-Packing / Toll Manufacturing



## Implemented Gap Items

1-55 implemented.



## Remaining Gap Items

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

Implement Gap 56 - GS1 Barcode & Labeling Advanced.

Inspect first:
- Check backend/app/models/gs1.py — what GS1 models exist
- Check backend/app/api/v1/endpoints/gs1.py — what endpoints exist
- Check frontend/src/app/dashboard/gs1/ — what pages exist

Gap 56 missing (from ERP_70_GAPS plan):
- GS1-128 barcode generation (enhanced)
- GTIN master data
- Expiry/lot encoded labels
- Pallet SSCC labeling
- Label template designer
- Printer integration stub
- Scan validation during dispatch

Build next coherent slice:
1. Check existing GS1 models before building.
2. Add GTIN model if not present (gtin, product_id, gtin_type GS1-8/13/14, status).
3. Add SSCC model (sscc_number, pallet_id, created_by, products JSONB).
4. Add label template model (template_name, template_type, zpl_template or html_template, fields JSONB).
5. Add endpoints: GTIN CRUD, SSCC generation, scan validation (GET /gs1/scan/{barcode}), label templates.
6. Frontend: GS1 hub with GTIN manager + SSCC generator.
7. Nav.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 55 additions:
backend/app/models/allergen.py - MODIFIED: Added CleaningValidationResult enum + CleaningValidationLog model (validation_ref, line_id/name, previous_product, previous_allergens JSON list, next_product, cleaning_method/agent, cleaned_by, validated_by, swab_test_result, swab_threshold, result PASS/FAIL/CONDITIONAL/PENDING, corrective_action)
backend/app/api/v1/endpoints/allergen.py - MODIFIED: Added imports (datetime, BaseModel, select, desc); Added POST/GET /allergen/cleaning-validations (no auth — consistent with existing allergen endpoints)
frontend/src/app/dashboard/allergen/cleaning/page.tsx - NEW: Cleaning Validation Log — KPI strip (total/pass/fail), log form (line/products/allergens/method/swab result/result), validation list with allergen badges and result colors, cross-contamination info box
frontend/src/components/nav-config.tsx - MODIFIED: Cleaning Validation under Allergen & Nutrition

Gap 54 additions:
backend/app/models/quality.py - MODIFIED: Added AuditStandard/AuditType/AuditResult enums; QualityAuditChecklist model (audit_ref, standard, audit_type, items JSON, total/passed items, score_pct, result, certificate_issued); SupplierFoodSafetyStatus enum; SupplierFoodSafetyApproval model (supplier, approval_type, status, audit_score, expiry_date, certificate, findings count)
backend/app/api/v1/endpoints/qms.py - MODIFIED: Added audit checklist imports; POST/GET /qms/audit-checklists (pre-populates BRC/FSSC/HALAL/HACCP_CODEX items); PATCH /qms/audit-checklists/{id}/items (marks pass/fail/na, recomputes score, auto-sets result); POST /qms/audit-checklists/{id}/close; GET /qms/audit-checklists/stats; POST/GET/PATCH /qms/supplier-food-safety
frontend/src/app/dashboard/qms/audit-checklists/page.tsx - NEW: Audit Checklists — split view (list left, checklist runner right), pass/fail/na buttons per item, score progress bar, result badge
frontend/src/app/dashboard/qms/supplier-safety/page.tsx - NEW: Supplier Food Safety — status filter, expiring toggle, critical/major/minor findings column (red/orange highlight)
frontend/src/components/nav-config.tsx - MODIFIED: Audit Checklists + Supplier Food Safety under QMS & HACCP

Gap 53 additions:
backend/app/models/copacking.py - NEW: CoPackingContract, CoPackingRun, CustomerTool models
backend/app/api/v1/endpoints/copacking.py - NEW: Full CRUD + tool usage logging
frontend/src/app/dashboard/copacking/page.tsx - NEW: 5-tab Co-Packing hub
frontend/src/components/nav-config.tsx - MODIFIED: Co-Packing nav link



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 55)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 55 notes:
- Allergen endpoints do NOT use get_current_user (existing pattern). New cleaning validation endpoints follow same pattern.
- CleaningValidationLog.previous_allergens = JSON list (array of strings). Frontend sends comma-separated input, splits to array on POST.
- Result scoring: PASS ≥95%, CONDITIONAL_PASS ≥75%, FAIL otherwise.

Gap 54 notes:
- AuditChecklist items pre-seeded per standard on create. _STANDARD_ITEMS dict has BRC (7), FSSC_22000 (7), HALAL (6), HACCP_CODEX (12) items.
- Score computation: passed/total_scored (excludes 'na' from denominator).
- SupplierFoodSafetyApproval: days_to_expiry computed in Python at read time.

Gap 56 start:
- Check backend/app/models/gs1.py and frontend/src/app/dashboard/gs1/ — GS1 module already exists.
- GS1 module has barcode generation (CODE128, EAN13, QR_CODE, GS1_128, DATAMATRIX formats).
- Focus on what's MISSING: GTIN master data model, SSCC pallet labeling, label template designer, scan validation endpoint.
