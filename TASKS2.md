# TASKS2.md



## Current Phase

Tier 5 — Advanced / Future Roadmap



## Current Gap

Gap 61 - IoT / Real-Time Machine Data Streaming



## In Progress

Not started yet.



## Completed in Last Run

Gap 60 - Kenya Localization Expansion

Gap 59 - Secondary Sales / Distributor Sell-Through Expansion

Gap 58 - Trade Promotion Management Expansion

Gap 57 - Shelf-Life / FEFO Control Expansion

Gap 56 - GS1 Barcode & Labeling Advanced

Gap 55 - Allergen & Nutrition Management

Gap 54 - HACCP System Expansion



## Implemented Gap Items

1-60 implemented.



## Remaining Gap Items

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

Implement Gap 61 - IoT / Real-Time Machine Data Streaming.

Inspect first:
- Check backend/app/models/integrations.py for existing IoT models (MachineEvent exists)
- Check backend/app/api/v1/endpoints/integrations.py for IoT endpoints
- utilities module (electricity, steam, etc.) may have sensor data ingestion

Gap 61 missing:
- MQTT broker integration for live sensor data
- OPC-UA connector for PLC/SCADA
- Real-time streaming dashboards (WebSocket-based)
- Sensor data normalization layer
- Threshold-based auto-alert system
- Machine state detection (running/idle/down)
- Event-based triggers (not polling)

Build next coherent slice:
1. Check existing MachineEvent model — likely exists from integrations module.
2. Add SensorDataPoint model (sensor_id, machine_id, metric_name, value, unit, timestamp, quality_flag).
3. Add MachineStateEvent model (machine_id, state: RUNNING/IDLE/DOWN/FAULT, previous_state, changed_at, trigger_value).
4. Add IoT alert threshold model (machine_id, metric_name, min_threshold, max_threshold, alert_severity).
5. Endpoints: ingest sensor data, list machine states, set thresholds, get alert history.
6. Frontend: IoT dashboard page with machine state tiles + sensor trend sparklines.
7. Nav under Utilities or AI section.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 60 additions:
backend/app/models/payroll_ke.py - MODIFIED: Added SHIFTier model (Kenya SHIF 2.75% rate replacing NHIF, effective Oct 2023); Added eTIMSInvoiceRecord model (KRA e-invoicing stub: invoice_id, customer_pin, supplier_pin, VAT amounts, status PENDING/SUBMITTED/ACCEPTED/REJECTED/FAILED, etims_ref, QR code)
backend/app/api/v1/endpoints/payroll_ke.py - MODIFIED: Added POST/GET /payroll-ke/etims/submit|records (eTIMS stub endpoints); POST/GET /payroll-ke/shif-tiers; POST /payroll-ke/shif-tiers/seed-defaults (seeds 2.75% standard rate)

Gap 59 additions:
backend/app/api/v1/endpoints/secondary_sales.py - MODIFIED: Added GET /secondary-sales/analytics/distributor-aging (days since last upload per distributor → aging buckets 0-30/31-60/61-90/91+d); GET /secondary-sales/analytics/sku-velocity (top SKUs by units/day over N days)

Gap 58 additions:
backend/app/models/tpm.py - MODIFIED: Added DateTime import; DistributorRebateAccrual model (distributor_id, promotion_id, period_month, rebate_rate_pct OR rebate_amount_flat, total_sales_value, accrued_amount, outstanding_amount, status OPEN/SETTLED/CANCELLED)
backend/app/api/v1/endpoints/tpm.py - MODIFIED: Added POST/GET /tpm/rebate-accruals (auto-compute accrued_amount from rate×sales or flat×units); POST /tpm/rebate-accruals/{id}/settle (mark settled, link claim_ref)

Gap 57 additions:
backend/app/models/shelf_life.py - MODIFIED: Added ShelfLifeExtension model (lot_id, original/proposed_expiry, extension_days auto-calc, justification, risk_assessment, status PENDING/APPROVED/REJECTED)
backend/app/api/v1/endpoints/shelf_life.py - MODIFIED: Added POST/GET /shelf-life/extensions; POST /shelf-life/extensions/{id}/approve|reject

Gap 56 additions:
backend/app/api/v1/endpoints/gs1.py - MODIFIED: Added POST /gs1/scan/dispatch-validate (decode barcode, lookup GTIN, check expected GTINs, expiry date warning); GET /gs1/gtin/lookup (find product by GTIN)

Gap 55 additions:
backend/app/models/allergen.py - MODIFIED: CleaningValidationLog model
backend/app/api/v1/endpoints/allergen.py - MODIFIED: POST/GET /allergen/cleaning-validations
frontend/src/app/dashboard/allergen/cleaning/page.tsx - NEW: Cleaning Validation Log page
frontend/src/components/nav-config.tsx - MODIFIED: Cleaning Validation nav link

Gap 54 additions:
backend/app/models/quality.py - MODIFIED: QualityAuditChecklist + SupplierFoodSafetyApproval models
backend/app/api/v1/endpoints/qms.py - MODIFIED: Audit checklist + supplier food safety endpoints
frontend/src/app/dashboard/qms/audit-checklists/page.tsx - NEW: Audit runner
frontend/src/app/dashboard/qms/supplier-safety/page.tsx - NEW: Supplier food safety tracker



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after all gaps this run)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 60 notes:
- eTIMS stub: stores invoice locally, returns PENDING status. To go live: POST to https://etims.kra.go.ke/api/... with OAuth2 token. Response sets etims_ref + QR code.
- SHIF: 2.75% of gross salary (min KES 300/month). Replaced NHIF flat rate Oct 2023. seed-defaults endpoint creates one "SHIF Standard Rate" entry.
- KeComponentType enum in payroll_ke.py still has NHIF — should be updated to SHIF in production payroll runs.

Gap 59 notes:
- distributor-aging: groups by distributor_id, gets max(upload_date), computes days since. Sorted by most stale first.
- sku-velocity: joins SecondarySalesLine → SecondarySalesHeader, groups by product_sku, returns units/day = total_units / days param.

Gap 58 notes:
- RebateAccrual.accrued_amount = total_sales × rate/100 OR total_units × flat_amount (whichever is set).
- Settle endpoint: sets settled_amount = accrued_amount, outstanding = 0, links claim_ref.

Gap 61 start:
- Check integrations.py for existing MachineEvent model (IoT placeholder was there originally).
- New models needed: SensorDataPoint, MachineStateEvent, IoTAlertThreshold.
- WebSocket endpoint NOT feasible without FastAPI WebSocket setup — use SSE (Server-Sent Events) or polling instead.
- Frontend: IoT dashboard with machine state cards + threshold alert list.
