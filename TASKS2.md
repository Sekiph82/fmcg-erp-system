# TASKS2.md



## Current Phase

Phase 3 - Medium Importance (Tier 3)



## Current Gap

Gap 38 - Reporting & BI Layer



## In Progress

Not started yet.



## Completed in Last Run

Gap 37 - Real-Time Notification Center (bell in Sidebar + mobile header)

Gap 36 - API Developer Portal / GraphQL Layer

Gap 35 - Native Mobile Apps Support Layer

Gap 34 - Customer / Product NPS Tracking

Gap 33 - Video Meeting Integration

Gap 32 - Recurring Billing / Auto-Invoicing

Gap 31 - Customer Loyalty Program

Gap 30 - VoIP / Call Center Integration



## Implemented Gap Items

1-37 implemented.



## Remaining Gap Items

38. Reporting & BI Layer

39. Document Management System

40. Customer / Supplier Portal Expansion

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

Implement Gap 38 - Reporting & BI Layer.

Inspect first:
- Check backend/app/api/v1/endpoints/report_builder.py for what already exists
- Check frontend/src/app/dashboard/report-builder/ for existing pages
- The report_builder endpoint already exists in router (prefix: /reports-builder)

Expected: existing report builder has basic structure. Gap 38 = add missing pieces:
1. Scheduled reports model (ReportSchedule: report_id, user_id, cron_expr, last_run, next_run, output_format, email_to).
2. Export stub endpoint (GET /reports-builder/{id}/export?format=excel|pdf — returns mock file or CSV).
3. KPI card builder page (simple drag-drop-style KPI tile configurator).
4. Cross-module analytics summary endpoint (stitches together key counts from multiple modules).
5. Saved views/filters — check if already in report_builder, if not add SavedFilter model + endpoints.
6. Frontend: enhance existing BI hub, add export buttons, add KPI configurator page.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: python not found on PATH.



## Files Changed in Last Run

Gap 37 additions:
frontend/src/components/NotificationBell.tsx - NEW: Real-time notification bell component (polls unread count every 60s, dropdown with 8 most recent unread, mark one/all read, link to notification center, priority color dots, relative timestamps)
frontend/src/components/DashboardShell.tsx - MODIFIED: Added NotificationBell import + bell in mobile top header (between logo and search button)
frontend/src/components/Sidebar.tsx - MODIFIED: Added NotificationBell import + bell in collapsed user footer (between avatar tooltip and sign-out) AND in expanded user footer (between avatar info and sign-out)

Gap 36 additions:
backend/app/models/api_portal.py - NEW: ApiKey model (user_id, key_name, key_prefix, key_hash SHA-256, scopes, rate_limit_per_min, is_active, last_used_at, expires_at); ApiKeyUsageLog model (key_id FK, endpoint, method, status_code, response_ms, ip_address)
backend/app/api/v1/endpoints/api_portal.py - NEW: POST /developer/keys (generate, raw_key shown once), GET /developer/keys (list, include_inactive param), DELETE /developer/keys/{id} (revoke), GET /developer/keys/{id}/usage, GET /developer/dashboard (stats), GET /developer/graphql/schema (stub info), GET /developer/resources (auth/rate limit info)
backend/app/api/v1/router.py - MODIFIED: Added api_portal import + /developer route
frontend/src/lib/api_portal_api.ts - NEW: Typed API client for developer portal
frontend/src/app/dashboard/developer/page.tsx - NEW: Developer Portal Hub — KPI strip, scopes, auth info, navigation links
frontend/src/app/dashboard/developer/keys/page.tsx - NEW: API Keys manager — generate form (name/scopes/rate-limit/description), keys table (prefix shown, revoke button), new-key one-time display with copy button
frontend/src/app/dashboard/developer/graphql/page.tsx - NEW: GraphQL Layer info — stub status, planned types/queries/mutations, integration guide
frontend/src/components/nav-config.tsx - MODIFIED: Added Developer Portal, API Keys, GraphQL Layer under Integrations section

Gap 35 additions:
backend/app/models/mobile.py - NEW: MobilePushToken (user_id, device_id, platform ios/android/web, token, active_flag, app_version, last_seen_at); MobileAppSession (user_id, device_id, platform, os_version, app_version, is_active, last_sync_at)
backend/app/api/v1/endpoints/mobile.py - NEW: POST /mobile/devices, GET /mobile/devices, DELETE /mobile/devices/{id}, POST /mobile/push/send (stub), GET /mobile/approvals (compact), GET /mobile/kpis, GET /mobile/devices/stats
backend/app/api/v1/router.py - MODIFIED: Added mobile route
frontend/src/lib/mobile_api.ts - NEW: Typed mobile API client
frontend/src/app/dashboard/mobile/page.tsx - NEW: Mobile Hub
frontend/src/app/dashboard/mobile/approvals/page.tsx - NEW: Mobile Approvals Inbox
frontend/src/app/dashboard/mobile/devices/page.tsx - NEW: Device Manager + test push form
frontend/src/components/nav-config.tsx - MODIFIED: Added Mobile Apps, Mobile Approvals, Device Manager under Admin & System



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors — verified after all 3 gaps)

Backend Python compile: BLOCKED (python not found)



## Notes for Next Claude Run

Gap 37 notes:
- NotificationBell polls GET /api/v1/notifications/unread-count?user_id=... every 60s.
- unread-count and mark-all-read endpoints take user_id as query param (not from auth token) — this is how the existing endpoint is designed.
- useAuth() hook returns user object; bell accesses user.id or user.user_id.
- Bell dropdown shows max 8 unread. Full list at /dashboard/notification-center/list.
- compact=true → smaller icon (14px), dropdown opens above (bottom-full) for sidebar collapsed use. 
- compact=false → larger icon (17px), dropdown opens below (top-full) for mobile header use.

Gap 36 notes:
- API keys store only SHA-256 hash + first 12 chars as prefix. Raw key shown once only.
- ApiKeyUsageLog exists but is not auto-populated yet — requires middleware integration in production.
- GraphQL stub at GET /developer/graphql/schema returns planned types/queries for documentation.

Gap 38 start:
- Check backend/app/api/v1/endpoints/report_builder.py and frontend/src/app/dashboard/report-builder/ before building.
- report_builder endpoint is already in router at prefix /reports-builder.
- Focus on: scheduled reports model + endpoint, export stub, cross-module analytics summary.
