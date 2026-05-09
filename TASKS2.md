# TASKS2.md



## Current Phase

Phase 3 - Medium Importance (Tier 3) → Tier 4 (FMCG-Specific)



## Current Gap

Gap 44 - Integration Marketplace / Connector Hub



## In Progress

Not started yet.



## Completed in Last Run

Gap 43 - Resource & Calendar Scheduling System

Gap 42 - Mobile-First Field Sales Expansion

Gap 41 - Audit Logs & Compliance Trail



## Implemented Gap Items

1-43 implemented.



## Remaining Gap Items

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

Implement Gap 44 - Integration Marketplace / Connector Hub.

Inspect first:
- Check backend/app/api/v1/endpoints/integrations.py — what exists
- Check frontend/src/app/dashboard/integrations/ — what pages exist
- Check if connector registry model exists

Gap 44 missing (from ERP_70_GAPS plan):
- Connector registry (list all available integrations)
- Prebuilt integrations (M-Pesa, email, WhatsApp, webhooks)
- API key management (already done in Gap 36 /developer)
- Webhook retry system (check webhooks module)
- Integration logs (check existing /integrations/logs)
- External system connectors (accounting, M-Pesa, EDI, WhatsApp)

Build next coherent slice:
1. Check what integrations.py endpoint already has.
2. Add ConnectorRegistry model (connector_code, name, category, status: ACTIVE/COMING_SOON, icon_url, description, auth_type, config_schema JSONB).
3. Add endpoints: GET /integrations/connectors (list), POST /integrations/connectors/{code}/test (stub test), GET /integrations/connectors/{code}/logs.
4. Frontend: Integration Marketplace hub page with connector cards (status badges, categories).
5. Wire nav.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 43 additions:
backend/app/models/calendar.py - MODIFIED: Added ShiftType enum (morning/afternoon/night/custom); Added ShiftSchedule model (user_id, user_name, department, shift_date ISO string, shift_type, shift_start/end HH:MM, location, approved_flag, approved_by, notes)
backend/app/api/v1/endpoints/calendar.py - MODIFIED: Added imports (select, desc, and_, Query, pydantic BaseModel); Added POST/GET /calendar/shifts (create + list with dept/date/user filters); PATCH /calendar/shifts/{id}/approve; DELETE /calendar/shifts/{id}
frontend/src/app/dashboard/calendar/shifts/page.tsx - NEW: Shift Scheduling — add shift form (user/dept/date/type/time), shift type presets (morning/afternoon/night/custom), grouped by date view with approve/delete buttons
frontend/src/components/nav-config.tsx - MODIFIED: Added Shift Schedule under Calendar & Scheduling

Gap 42 additions:
backend/app/models/van_sales.py - MODIFIED: outlet_photo_url on VanVisit; VanRepDayLog model
backend/app/api/v1/endpoints/van_sales.py - MODIFIED: Photo capture + rep day log endpoints
frontend/src/app/dashboard/van-sales/field-rep/page.tsx - NEW: Field Rep Day Log
frontend/src/components/nav-config.tsx - MODIFIED: Field Rep Log nav link

Gap 41 additions:
backend/app/models/audit_log.py - MODIFIED: Extended AuditLog + AuditRetentionPolicy
backend/app/api/v1/endpoints/audit.py - MODIFIED: Stats + export + integrity check + retention endpoints
frontend/src/app/dashboard/logs/compliance/page.tsx - NEW: Compliance Audit Trail
frontend/src/app/dashboard/logs/retention/page.tsx - NEW: Retention Policies
frontend/src/components/nav-config.tsx - MODIFIED: Compliance + Retention nav links



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after Gap 43)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 43 notes:
- ShiftSchedule.shift_date stored as String(10) — ISO date "YYYY-MM-DD". Easier to filter than DateTime.
- Shift type presets auto-fill start/end times when selected in UI. Custom type leaves times editable.
- Approve endpoint: PATCH /calendar/shifts/{id}/approve?approved_by=Manager. Simple flag flip.
- Calendar module already had: ResourceBooking, CalendarResource (incl. MACHINE type), availability check, conflict resolver AI, events/participants — all complete.

Gap 44 start:
- Check integrations.py endpoint and integrations frontend pages.
- Likely has basic integration list. Need: ConnectorRegistry model, marketplace hub page.
- The api_portal keys (Gap 36) handle API key management — don't duplicate.
- Focus: connector catalog with status badges (ACTIVE/BETA/COMING_SOON), test endpoint, usage logs.
