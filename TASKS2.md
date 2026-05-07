# TASKS2.md



## Current Phase

Phase 2 - High Importance (Tier 2)



## Current Gap

Gap 23 - No-Code / Extensibility Layer



## In Progress

Not started yet.



## Completed in Last Run

Gap 22 - Internal Collaboration Layer Expansion

Gap 21 - CRM Pipeline Depth

Gap 20 - Bank API Integration / Open Banking

Gap 19 - Electronic Signatures

Gap 18 - Retail / Shop POS

Gap 17 - Project Management with Gantt & Dependencies

Gap 16 - Helpdesk / Customer Complaint Ticketing

Gap 15 - Quote / Estimation Module

Gap 14 - WhatsApp Business API Integration

Gap 13 - Multi-Company / Multi-Branch Architecture

Gap 12 - Email Integration Gmail / Outlook Sync

Gap 11 - Real-Time Team Messaging / Collaboration Channels

Gap 10 - Batch Recall Operational Hardening

Gap 9 - Workflow Engine & Approval System

Gap 8 - Inventory Valuation & Costing Engine

Gap 7 - MRP Engine Hardening

Gap 6 - Manufacturing Execution System (MES) Depth

Gap 5 - Serialized Inventory / Serial Number Tracking

Gap 4 - Budget Planning & Variance Analysis

Gap 3 - eTIMS / KRA e-Invoice Integration

Gap 2 - Multi-Currency with Real-Time Exchange Rates

Gap 1 - Full Double-Entry General Ledger



## Implemented Gap Items

1. Full Double-Entry General Ledger

2. Multi-Currency with Real-Time Exchange Rates

3. eTIMS / KRA e-Invoice Integration

4. Budget Planning & Variance Analysis

5. Serialized Inventory / Serial Number Tracking

6. Manufacturing Execution System (MES) Depth

7. MRP Engine Hardening

8. Inventory Valuation & Costing Engine

9. Workflow Engine & Approval System

10. Batch Recall Operational Hardening

11. Real-Time Team Messaging / Collaboration Channels

12. Email Integration Gmail / Outlook Sync

13. Multi-Company / Multi-Branch Architecture

14. WhatsApp Business API Integration

15. Quote / Estimation Module

16. Helpdesk / Customer Complaint Ticketing

17. Project Management with Gantt & Dependencies

18. Retail / Shop POS

19. Electronic Signatures

20. Bank API Integration / Open Banking

21. CRM Pipeline Depth

22. Internal Collaboration Layer Expansion



## Remaining Gap Items

23. No-Code / Extensibility Layer

24. Procurement System Depth

25. Sales Order to Cash Full Lifecycle

26. Warehouse Execution Layer

27. Quality System Completion

28. Knowledge Base / Internal Wiki

29. Employee Survey & Engagement Module

30. VoIP / Call Center Integration

31. Customer Loyalty Program

32. Recurring Billing / Auto-Invoicing

33. Video Meeting Integration

34. Customer / Product NPS Tracking

35. Native Mobile Apps Support Layer

36. API Developer Portal / GraphQL Layer

37. Real-Time Notification Center

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

Implement Gap 23 - No-Code / Extensibility Layer.

Inspect first:
- backend/app/models/custom_fields.py - existing CustomFieldDefinition, CustomFieldOption, CustomFieldValue models
- backend/app/api/v1/endpoints/custom_fields.py - current custom field endpoint coverage
- frontend/src/app/dashboard/custom-fields/ - existing custom fields UI pages
- frontend/src/components/nav-config.tsx - where custom fields/extensibility appears in nav

Expected: Custom fields module exists for adding per-entity fields. What is missing is: visual form builder (drag-drop field arrangement), workflow builder UI (trigger/action rules), dashboard builder (saved widget layouts), and a no-code custom object creation UI. Focus on the most practical slice: form builder + custom field manager with drag-drop arrangement.

Build next coherent slice:
1. Inspect existing custom fields backend/frontend coverage.
2. Add form layout/arrangement metadata to CustomFieldDefinition (display_order, section_label, field_width).
3. Add visual form builder page where users can drag-and-drop custom fields into a form layout.
4. Add custom field preview (what the form would look like with current field arrangement).
5. Add workflow trigger rule stub model (trigger_event + condition_field + action_type) - basic automation rules.
6. Wire nav entry for Form Builder under Administration & System.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: this shell has no python/py launcher on PATH, and backend/venv/Scripts/python.exe points to a missing Python 3.12 install. Backend compile could not be run until the local Python environment is repaired.



## Files Changed in Last Run

Gap 22 additions:
backend/app/models/chatter.py - MODIFIED: Extended ReferenceType enum (added crm_record, ticket, project, production, document, batch, batch_recall); changed Activity columns from SAEnum to String(50) to avoid PostgreSQL enum constraint on new values; added sla_due_at (DateTime nullable) and sla_breached (Boolean) columns to Activity; changed ChatterAIRecommendation columns from SAEnum to String
backend/app/schemas/chatter.py - MODIFIED: Changed ActivityOut fields from enum types to str for reference_type/activity_type/visibility; added sla_due_at/sla_breached to ActivityOut; changed ActivityCreate to use str types + added sla_due_at; changed CTAIRecOut/CTAIRecAck to use str for agent_type/status
backend/app/services/chatter_service.py - MODIFIED: Added sla_due_at support in create_activity; added get_timeline service (cross-module, paginated, with module_breakdown + sla_breached_count); added get_sla_breached service; added create_activity_with_sla stub
backend/app/api/v1/endpoints/chatter.py - MODIFIED: Added GET /chatter/timeline endpoint (cross-module filtered timeline); added GET /chatter/sla/breached endpoint
frontend/src/lib/chatter.ts - MODIFIED: Extended ReferenceType type union (crm_record, ticket, project, production, document, batch, batch_recall); changed ActivityOut types to string; added sla_due_at/sla_breached to ActivityOut; added TimelineResponse interface; added getTimeline + getSLABreached API methods; changed TYPE_ICON/TYPE_COLOR/TYPE_BADGE maps to Record<string, string>; added new REF_LABEL entries
frontend/src/app/dashboard/chatter/threads/page.tsx - NEW: Cross-module activity timeline browser with SLA overdue alert section, module breakdown filter chips, reference type dropdown, search, SLA-only filter, pagination
frontend/src/components/nav-config.tsx - MODIFIED: Added "Module Threads" nav entry under Chatter & Timeline



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors)

Backend Python compile: BLOCKED (python and py not found; backend venv python points to missing C:\Users\sekip\AppData\Local\Programs\Python\Python312\python.exe)

Backend import chain: NOT RUN due local Python environment blocker above



## Notes for Next Claude Run

Gap 22 implementation notes:
- Activity.reference_type, activity_type, visibility columns changed from SAEnum to String. This avoids PostgreSQL ENUM constraint issues when adding new reference type values. For fresh installs (create_all), the table will be created with String columns. For existing installs, the column type change won't happen automatically.
- SLA timer fields: sla_due_at (DateTime, nullable) + sla_breached (Boolean, default False) added to Activity.
- Cross-module timeline GET /chatter/timeline: filters by reference_types (comma-separated), created_by, search, sla_overdue_only, page/per_page. Returns items + module_breakdown (count per reference type) + sla_breached_count.
- SLA breached queue: GET /chatter/sla/breached returns activities where sla_due_at < now, ordered by sla_due_at ascending (oldest overdue first).
- New module threads page: shows SLA alert strip at top, module breakdown filter chips, timeline items with ref type + activity type badges, pagination.
- ChatterTimeline.tsx component already uses the TYPE_BADGE/TYPE_ICON maps - changed maps to Record<string, string> to allow any string key (TypeScript fix).

Gap 21 implementation notes:
- CRMTerritory is a new table (create_all will create it). territory_id column added to crm_records as nullable FK.
- Territory management page shows per-territory pipeline/win-rate cards and a list with edit capability.
- Customer 360 view (/crm/records/{id}/360) aggregates: activity health score (0-100), communication risk (LOW/MEDIUM/HIGH based on days since last completed activity), deal risk flag (close date overdue), overdue activity count, interest product count, weighted deal value, pipeline age, summary_flags list.
- 360 tab added to record detail page with health score gauge, communication risk badge, activity metrics, deal intelligence grid, and action flags chips.
- credit_signal is returned as "UNKNOWN" — full credit scoring requires linking to sales invoice/payment history which is deferred to Gap 25.

Exact next task:
Start Gap 23 by inspecting existing custom_fields backend/frontend before coding.
Look at: backend/app/models/custom_fields.py, backend/app/api/v1/endpoints/custom_fields.py, frontend/src/app/dashboard/custom-fields/.
Focus on: form layout metadata (display_order, section_label), visual form builder page, custom field arrangement UI.
Do not create a parallel extensibility module. Extend existing custom_fields module.
