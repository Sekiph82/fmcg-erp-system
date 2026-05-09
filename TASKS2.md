# TASKS2.md



## Current Phase

Phase 3 - Medium Importance (Tier 3)



## Current Gap

Gap 41 - Audit Logs & Compliance Trail



## In Progress

Not started yet.



## Completed in Last Run

Gap 40 - Customer / Supplier Portal Expansion

Gap 39 - Document Management System

Gap 38 - Reporting & BI Layer

Gap 37 - Real-Time Notification Center

Gap 36 - API Developer Portal / GraphQL Layer

Gap 35 - Native Mobile Apps Support Layer



## Implemented Gap Items

1-40 implemented.



## Remaining Gap Items

41. Audit Logs & Compliance Trail

42. Mobile-First Field Sales Expansion

43. Resource & Calendar Scheduling System

44. Integration Marketplace / Connector Hub

45. Returnable Packaging / Container Management

46. New Product Development Workflow

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

Implement Gap 41 - Audit Logs & Compliance Trail.

Inspect first:
- Check backend/app/models/audit_log.py — what model exists
- Check backend/app/api/v1/endpoints/audit.py — what endpoints exist
- Check frontend/src/app/dashboard/logs/ for existing audit log pages

Gap 41 missing (from ERP_70_GAPS plan):
- Immutable logs (append-only)
- Before/after value tracking
- User/session/IP tracking
- Exportable audit reports
- Retention policies
- Tamper detection
- Searchable audit UI

Build next coherent slice:
1. Check if existing audit_log model has before_value/after_value fields.
2. If not: add these fields to the audit model (alter table not needed — create_all will add).
3. Add export endpoint (GET /audit/export?format=csv) — stream CSV of filtered audit events.
4. Add retention policy model + endpoint (configurable per module: retain_days).
5. Add tamper detection: each log row has a hash of (event_type + entity + timestamp + before + after); an audit integrity check endpoint verifies hashes.
6. Frontend: enhanced audit log page with before/after diff view, export button, retention settings.
7. Wire nav.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 40 additions:
backend/app/models/portal.py - MODIFIED: Added PortalSellThroughUpload model (portal_account_id FK, period_start, period_end, total_units_sold, total_value, notes, upload_reference, review_status, reviewed_by, reviewed_at)
backend/app/api/v1/endpoints/portal.py - MODIFIED: Added GET /portal/accounts/{id}/sales-orders (ERP SalesOrder tracking by linked_customer_id); Added POST /portal/sell-through-upload (PortalSellThroughUpload submission); Added SellThroughUploadIn pydantic schema
frontend/src/app/dashboard/portal/order-tracking/page.tsx - NEW: Order Tracking — account selector, ERP sales orders table (order_no, dates, status badge, payment status, amount), linked via linked_customer_id
frontend/src/app/dashboard/portal/sell-through/page.tsx - NEW: Sell-Through Upload — portal account selector, period start/end, units sold, total value, reference, notes; POST to /portal/sell-through-upload; success banner with upload_id
frontend/src/components/nav-config.tsx - MODIFIED: Added Order Tracking + Sell-Through Upload to Customer/Distributor Portal section

Gap 39 additions:
backend/app/models/documents.py - MODIFIED: DocumentTag model + tags relationship
backend/app/api/v1/endpoints/documents.py - MODIFIED: Expiry list endpoint + tagging CRUD endpoints
frontend/src/app/dashboard/documents/expiring/page.tsx - NEW: Expiry Tracker
frontend/src/app/dashboard/documents/compliance/page.tsx - NEW: Compliance Docs viewer
frontend/src/components/nav-config.tsx - MODIFIED: Expiry Tracker + Compliance Docs nav links

Gap 38 additions:
backend/app/models/report_builder.py - MODIFIED: RLSPolicy model
backend/app/api/v1/endpoints/report_builder.py - MODIFIED: executive-summary + RLS CRUD endpoints
frontend/src/app/dashboard/report-builder/executive/page.tsx - NEW: Executive KPI Dashboard
frontend/src/app/dashboard/report-builder/rls/page.tsx - NEW: RLS management
frontend/src/components/nav-config.tsx - MODIFIED: Executive KPIs + RLS nav links



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after all gaps this run)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 40 notes:
- Portal statement endpoint already existed (GET /portal/accounts/{id}/statement via portal_service.get_portal_statement) — NOT re-implemented.
- Order tracking endpoint (GET /portal/accounts/{id}/sales-orders) queries SalesOrder by linked_customer_id cast to string — may need adjustment if linked_customer_id stores UUID format differently vs SalesOrder.customer_id.
- PortalSellThroughUpload is stored in portal_sell_through_uploads table. Separate from SecondarySalesHeader — portal submissions need manual review before posting to secondary_sales.
- Sell-through upload returns PENDING status — no auto-integration with secondary_sales. Next step: add a "review and post" endpoint that creates a SecondarySalesHeader from a PortalSellThroughUpload.

Gap 39 notes:
- DocumentTag table: id, document_id (FK cascade), tag (lowercase), created_by, created_at.
- Expiry list endpoint: GET /documents/expiring/list?days=30&include_expired=true. Must be before /{doc_id} route in file (static vs dynamic path conflict).
- Tag search: GET /documents/tags/search?tag=xxx — also must be before /{doc_id} in routing.

Gap 38 notes:
- RLS not yet enforced in report runner (report_builder_service.run_report). Next: inject active RLS policies as WHERE clauses in run_report().
- Executive summary cross-module endpoint at GET /reports-builder/executive-summary.

Gap 41 start:
- Check audit_log.py model and audit.py endpoint first.
- audit module is already imported in router at prefix /audit.
- Focus on: before/after value columns (if missing), export CSV endpoint, tamper hash verification.
- System audit logs exist at /dashboard/logs in nav — may be separate from the compliance audit trail.
