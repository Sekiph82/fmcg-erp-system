# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 11 — Real-Time Team Messaging / Collaboration Channels



## In Progress

Not started yet.



## Completed in Last Run

Gap 10 — Batch Recall Operational Hardening

Gap 9 — Workflow Engine & Approval System

Gap 8 — Inventory Valuation & Costing Engine

Gap 7 — MRP Engine Hardening

Gap 6 — Manufacturing Execution System (MES) Depth

Gap 5 — Serialized Inventory / Serial Number Tracking

Gap 4 — Budget Planning & Variance Analysis

Gap 3 — eTIMS / KRA e-Invoice Integration

Gap 2 — Multi-Currency with Real-Time Exchange Rates

Gap 1 — Full Double-Entry General Ledger



## Implemented Gap Items

1\. Full Double-Entry General Ledger

2\. Multi-Currency with Real-Time Exchange Rates

3\. eTIMS / KRA e-Invoice Integration

4\. Budget Planning & Variance Analysis

5\. Serialized Inventory / Serial Number Tracking

6\. Manufacturing Execution System (MES) Depth

7\. MRP Engine Hardening

8\. Inventory Valuation & Costing Engine

9\. Workflow Engine & Approval System

10\. Batch Recall Operational Hardening



## Remaining Gap Items

11\. Real-Time Team Messaging / Collaboration Channels

12\. Email Integration Gmail / Outlook Sync

13\. Multi-Company / Multi-Branch Architecture

14\. WhatsApp Business API Integration

15\. Quote / Estimation Module

16\. Helpdesk / Customer Complaint Ticketing

17\. Project Management with Gantt & Dependencies

18\. Retail / Shop POS

19\. Electronic Signatures

20\. Bank API Integration / Open Banking

21\. CRM Pipeline Depth

22\. Internal Collaboration Layer Expansion

23\. No-Code / Extensibility Layer

24\. Procurement System Depth

25\. Sales Order to Cash Full Lifecycle

26\. Warehouse Execution Layer

27\. Quality System Completion

28\. Knowledge Base / Internal Wiki

29\. Employee Survey & Engagement Module

30\. VoIP / Call Center Integration

31\. Customer Loyalty Program

32\. Recurring Billing / Auto-Invoicing

33\. Video Meeting Integration

34\. Customer / Product NPS Tracking

35\. Native Mobile Apps Support Layer

36\. API Developer Portal / GraphQL Layer

37\. Real-Time Notification Center

38\. Reporting & BI Layer

39\. Document Management System

40\. Customer / Supplier Portal Expansion

41\. Audit Logs & Compliance Trail

42\. Mobile-First Field Sales Expansion

43\. Resource & Calendar Scheduling System

44\. Integration Marketplace / Connector Hub

45\. Returnable Packaging / Container Management

46\. New Product Development Workflow

47\. Route Optimization for Van Sales

48\. Consumer Complaint Management Linked to Batch

49\. Regulatory Certificate Tracking

50\. Dynamic / AI Pricing Engine

51\. Brand Asset / Label Design Management

52\. Market Intelligence / Competitor Tracking

53\. Co-Packing / Toll Manufacturing

54\. HACCP System Expansion

55\. Allergen & Nutrition Management

56\. GS1 Barcode & Labeling Advanced

57\. Shelf-Life / FEFO Control Expansion

58\. Trade Promotion Management Expansion

59\. Secondary Sales / Distributor Sell-Through Expansion

60\. Kenya Localization Expansion

61\. IoT / Real-Time Machine Data Streaming

62\. ML-Based Demand Forecasting Engine

63\. Blockchain-Based Traceability

64\. Carbon Footprint Per Product

65\. AI-Powered Receipt OCR

66\. Natural Language ERP Control

67\. AI Agent Governance Framework

68\. Predictive Maintenance

69\. ESG Intelligence & Sustainability Optimization

70\. Plugin / App Marketplace Architecture



## Next Immediate Task

Implement Gap 11 — Real-Time Team Messaging / Collaboration Channels.

Check if any existing chat/messaging model exists first:
- backend/app/models/chatter.py (investigator found this — check contents)
- backend/app/api/v1/endpoints/chatter.py
- frontend/src/lib/chatter.ts
- frontend/src/app/dashboard/ — any messaging/chat pages

Spec requires:
- Channel-based messaging (Production, Sales, Finance, Ops)
- Direct messages between users
- @mentions with notifications
- Threaded conversations
- Message search
- Cross-module linking (message → order → batch → issue)

If chatter exists but is only record-level comments, need to add:
- ChatChannel model (team channels, not per-record)
- ChannelMessage model (with thread support)
- DirectMessage model
- WebSocket or polling endpoints for real-time feel
- Frontend: chat/messaging page with channel list + message thread



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 10 additions:
backend/app/models/traceability.py — Added sla_target_hours to RecallHeader; added RecallAudience enum + RecallCommunicationTemplate model; added RecallStatusLog model (immutable); added RecallEvidence model
backend/app/schemas/traceability.py — Added RecallAudience import; added RecallTemplateCreate/Update/Out, RecallStatusLogOut, RecallEvidenceCreate/Out schemas
backend/app/services/recall_service.py — Added _log_status_change() helper; hooked into update_recall_status(); added list_templates(), create_template(), update_template(), list_status_logs(), add_evidence(), list_evidence() service functions
backend/app/api/v1/endpoints/traceability.py — Added GET/POST/PATCH /recall-templates, GET /recalls/{id}/audit-log, GET/POST /recalls/{id}/evidence endpoints
frontend/src/lib/traceability.ts — Added RecallAudience/RecallTemplate/RecallStatusLog/RecallEvidence types; added listTemplates, createTemplate, updateTemplate, getAuditLog, listEvidence, addEvidence API methods
frontend/src/app/dashboard/traceability/templates/page.tsx — New comm. templates management page with audience filter cards, template table, active toggle, create/edit modal with placeholder docs
frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx — Added Audit Trail tab (immutable status log) + Evidence tab (attach/view documents); added audit/evidence state + fetch on tab switch
frontend/src/components/nav-config.tsx — Added Comm. Templates nav entry



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 11: Real-Time Team Messaging / Collaboration Channels.

Inspect backend/app/models/chatter.py first — it likely has record-level chatter (comments on POs/records).
Gap 11 requires TRUE team channels (not per-record), similar to Slack channels.

If chatter.py has per-record comments only, need to add:
1. ChatChannel model — id, name, channel_type (TEAM/DIRECT), module_link (nullable), members
2. ChatMessage model — channel_id, sender_id, body, parent_id (thread), mentions (JSON array of user IDs)
3. ChannelMember model — channel_id, user_id, last_read_at
4. Service: create_channel, post_message, get_messages (with pagination), mark_read, search_messages
5. Endpoints: GET /channels/, POST /channels/, POST /channels/{id}/messages, GET /channels/{id}/messages
6. Frontend: /dashboard/messages/ with channel list sidebar + message thread + @mention support

WebSocket is complex — use polling (GET with ?since=timestamp) for simplicity. Real-time feel via 5s refetch.
