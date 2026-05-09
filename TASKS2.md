# TASKS2.md



## Current Phase

Tier 5 — Advanced / Future Roadmap



## Current Gap

Gap 65 - AI-Powered Receipt OCR



## In Progress

Not started yet.



## Completed in Last Run

Gap 64 - Carbon Footprint Per Product

Gap 63 - Blockchain-Based Traceability

Gap 62 - ML-Based Demand Forecasting Engine

Gap 61 - IoT / Real-Time Machine Data Streaming



## Implemented Gap Items

1-64 implemented.



## Remaining Gap Items

65. AI-Powered Receipt OCR

66. Natural Language ERP Control

67. AI Agent Governance Framework

68. Predictive Maintenance

69. ESG Intelligence & Sustainability Optimization

70. Plugin / App Marketplace Architecture



## Next Immediate Task

Implement Gap 65 - AI-Powered Receipt OCR.

Inspect first: backend/app/models/expenses.py — does expense claim model exist?

Build plan:
1. ReceiptOCRRecord model (image_url, file_name, extracted_date, extracted_vendor, extracted_amount, extracted_category, raw_extracted_text, confidence_score, processing_status, duplicate_hash, is_duplicate, duplicate_of_id, linked_expense_id).
2. POST /ai/receipt-ocr (submit image URL → stub extraction simulates OCR → returns structured data, checks for duplicates).
3. GET /ai/receipt-ocr (list past OCR results).
4. Frontend: receipt scanner page in expenses/HR section.
5. Nav under HR & Workforce > Expenses.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 64 additions:
backend/app/models/esg.py - MODIFIED: ProductCarbonFootprint model (scope1/2/3 auto-computed, co2e_per_unit)
backend/app/api/v1/endpoints/esg.py - MODIFIED: POST/GET /esg/carbon-footprints + summary
frontend/src/app/dashboard/esg/carbon/page.tsx - NEW: 3-tab Carbon Footprint page
frontend/src/components/nav-config.tsx - MODIFIED: Carbon Per Product ESG nav link

Gap 63 additions:
backend/app/models/traceability.py - MODIFIED: BlockchainAnchor model (STUB/ETH/POLYGON/Hyperledger, SHA-256 payload hash, public QR token)
backend/app/api/v1/endpoints/traceability.py - MODIFIED: POST anchor, GET anchors, GET public/{token} (no auth)

Gap 62 additions:
backend/app/models/mrp.py - MODIFIED: rmse on DemandForecast; squared_error + override audit on DemandForecastLine; ForecastOverrideLog model
backend/app/services/forecast_service.py - MODIFIED: RMSE computation, promotion uplift check, cross-SKU Pearson correlation
backend/app/api/v1/endpoints/mrp.py - MODIFIED: Override log, cross-SKU correlation, promotion uplift endpoints
frontend/src/app/dashboard/mrp/forecast/accuracy/page.tsx - NEW
frontend/src/app/dashboard/mrp/forecast/correlation/page.tsx - NEW
frontend/src/components/nav-config.tsx - MODIFIED: Forecast Accuracy + Correlation nav links



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 64)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 64 notes:
- Kenya electricity grid factor: 0.4971 kg CO2e/kWh. Diesel: 2.68 kg CO2e/litre (GHG Protocol).
- Company-level ESG confirmed existing (esg/page.tsx has full scope 1/2/3 dashboard). Not re-implemented.

Gap 63 notes:
- STUB tx_hash = sha256(payload_hash + timestamp). Public QR needs no auth.
- Production: wire web3.py / fabric-sdk-py / polygon SDK.

Gap 62 notes:
- RMSE computed during backfill_actuals (squared_error per line, then sqrt(mean)).
- cross_sku_correlation uses Python statistics.correlation() — requires Python 3.10+.
- ForecastOverrideLog: logged on every adjusted_qty PATCH.

Gap 65 start: check expenses.py model. Add ReceiptOCRRecord to new or existing model. Stub OCR: regex-like extraction patterns from image URL name, simulate confidence score. Duplicate: sha256(vendor+amount+date). Frontend: receipt scan page in expenses section.
