# TASKS2.md



## Current Phase

Tier 4 — FMCG-Specific & Regulatory



## Current Gap

Gap 50 - Dynamic / AI Pricing Engine



## In Progress

Not started yet.



## Completed in Last Run

Gap 49 - Regulatory Certificate Tracking

Gap 48 - Consumer Complaint Management Linked to Batch

Gap 47 - Route Optimization for Van Sales



## Implemented Gap Items

1-49 implemented.



## Remaining Gap Items

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

Implement Gap 50 - Dynamic / AI Pricing Engine.

Inspect first:
- Check backend/app/models/pricing.py and pricing.py endpoint — static price lists exist
- Check backend/app/models/price_list.py — enhanced price lists exist (Gap implemented earlier)

Gap 50 missing:
- Competitor price tracking (manual entry or import)
- Demand-based pricing logic (price elasticity model)
- AI price recommendations (margin protection)
- Channel-specific pricing (modern trade / distributor / export)
- Margin protection automation (floor price enforcement)

Build next coherent slice:
1. CompetitorPrice model (product_name, competitor_name, price, channel, recorded_date, source).
2. PriceRecommendation model (product_id, channel, recommended_price, floor_price, current_price, margin_pct, rationale, status PENDING/APPLIED/REJECTED).
3. Endpoints: add competitor price, list competitor prices, generate price recommendation (simple rule: if competitor < our price × 0.9, recommend price cut; if margin < floor, alert), GET /pricing/ai-recommendations.
4. Frontend: AI pricing hub page with competitor tracker and recommendations.
5. Nav under Sales & Distribution.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 49 additions:
backend/app/models/regulatory_certs.py - NEW: RegulatoryCertificate model (cert_ref, authority KEBS/HALAL/ISO/FSCC/etc., entity_type PRODUCT/PLANT/SUPPLIER/COMPANY, entity_id soft link, certificate_number, country, issued_date, expiry_date, status ACTIVE/PENDING_RENEWAL/EXPIRED/SUSPENDED/REVOKED, document_url, alert_sent_30/60/90d flags); CertAuditEntry model (cert_id FK, action, performed_by, notes)
backend/app/api/v1/endpoints/regulatory_certs.py - NEW: POST/GET /regulatory-certs/ (filter by authority/entity_type/status); GET /regulatory-certs/expiring (days param + include_expired); GET /regulatory-certs/stats (by_authority breakdown); GET /regulatory-certs/{id} (with audit_history); PATCH /regulatory-certs/{id} (auto-adds CertAuditEntry)
backend/app/api/v1/router.py - MODIFIED: regulatory_certs import + /regulatory-certs route
frontend/src/app/dashboard/quality/certificates/page.tsx - NEW: Certificate Register — KPI strip (total/expiring_90d/expired/authorities), authority filter chips, status/entity_type filters + expiring-only toggle, certificate table (days_to_expiry color-coded: red<0, amber≤30, orange≤60), add form, document URL link
frontend/src/components/nav-config.tsx - MODIFIED: Reg. Certificates under Quality Control

Gap 48 additions:
backend/app/models/consumer_complaints.py - NEW: ConsumerComplaint model
backend/app/api/v1/endpoints/consumer_complaints.py - NEW: Full CRUD + stats + by-lot endpoints
backend/app/api/v1/router.py - MODIFIED: consumer_complaints route
frontend/src/app/dashboard/quality/consumer-complaints/page.tsx - NEW: Consumer Complaints
frontend/src/components/nav-config.tsx - MODIFIED: Consumer Complaints nav link

Gap 47 additions:
backend/app/models/field_sales.py - MODIFIED: lat_override, lng_override, priority_score on RouteStop
backend/app/api/v1/endpoints/field_sales.py - MODIFIED: Nearest-neighbor + apply + profitability
frontend/src/app/dashboard/van-sales/route-optimizer/page.tsx - NEW: Route Optimizer
frontend/src/components/nav-config.tsx - MODIFIED: Route Optimizer nav link



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 49)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 49 notes:
- RegulatoryCertificate.cert_ref auto-generated CERT-YYYYMM-NNNN.
- expiry endpoint: filters ACTIVE + PENDING_RENEWAL certs with expiry_date ≤ today+days. include_expired=true shows already-expired.
- days_to_expiry computed in Python at query time: (expiry_date - today).days. Negative = expired.
- CertAuditEntry auto-created on POST (action=ISSUED) and PATCH (action=status.value or UPDATED).
- alert_sent_30/60/90d flags: set to True when alert sent (production: cron job calls /regulatory-certs/expiring and sends email/notification, then updates flags).
- stats.by_authority: count per authority type for all active certs.

Gap 50 start:
- pricing.py endpoint already exists at /pricing. Check what models exist before building.
- price_list.py also exists. Avoid duplicating existing price list logic.
- Focus on NEW: competitor price tracking table + AI recommendation engine (rule-based, no ML needed).
