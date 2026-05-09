# TASKS2.md



## Current Phase

Tier 5 — Advanced / Future Roadmap



## Current Gap

Gap 67 - AI Agent Governance Framework



## Implemented Gap Items

1-66 implemented. Gap 66 backend done, frontend NL console page missing — build next run.



## Remaining Gap Items

67. AI Agent Governance Framework

68. Predictive Maintenance

69. ESG Intelligence & Sustainability Optimization

70. Plugin / App Marketplace Architecture



## Next Immediate Task

1. First: create /dashboard/ai/nl-command page (Gap 66 frontend completion).
2. Then: implement Gaps 67-70 in order.

Gap 66 frontend: POST /api/v1/ai/nl-command, show parsed_intent + risk_level + confirmation, GET /api/v1/ai/nl-command/history.

Gap 67: AIAgentPolicy model + AIAgentRun log. Endpoints: CRUD policies, log runs. Frontend: governance console at /dashboard/ai/governance.

Gap 68: Check maintenance.py. Add MaintenancePrediction model (machine_id, predicted_failure_date, confidence, failure_mode, recommended_action). Rule-based from IoT sensor trends. Frontend page.

Gap 69: ESG Intelligence expansion — SupplierSustainabilityScore model, energy intensity per SKU from IoT + production data, wastewater compliance tracking. Frontend.

Gap 70: Plugin model (code, name, category, version, status, installed). Endpoints: list, install stub. Frontend marketplace.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 66 (backend only):
backend/app/models/ai.py - MODIFIED: NLCommandStatus enum + NLCommandLog model
backend/app/api/v1/endpoints/ai.py - MODIFIED: _parse_intent() rule-based (7 intents); POST/GET nl-command endpoints
FRONTEND PAGE MISSING: /dashboard/ai/nl-command

Gap 65:
backend/app/models/receipt_ocr.py - NEW: ReceiptOCRRecord (stub OCR, duplicate detection)
backend/app/api/v1/endpoints/receipt_ocr.py - NEW: Full OCR endpoints
backend/app/api/v1/router.py - MODIFIED: receipt_ocr route
frontend/src/app/dashboard/expenses/receipt-ocr/page.tsx - NEW
frontend/src/components/nav-config.tsx - MODIFIED: Receipt OCR nav



## Validation Results

Frontend TypeScript: PASS (verified before stopping)

Backend Python compile: BLOCKED (python not found)



## Notes

Gap 66 _parse_intent keywords: approve+po→APPROVE_PO, run+mrp→RUN_MRP, dunning+overdue→SEND_DUNNING, reorder+low stock→TRIGGER_REORDER, recall+batch→INITIATE_RECALL, payroll→RUN_PAYROLL, report+generate→GENERATE_REPORT.

HIGH risk (requires_confirmation=True): TRIGGER_REORDER, INITIATE_RECALL, RUN_PAYROLL.

execute endpoint is STUB — does not actually call target_endpoint. Wire httpx.AsyncClient for real execution.
