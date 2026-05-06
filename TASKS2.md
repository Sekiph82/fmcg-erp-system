# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 12 — Email Integration (Gmail / Outlook Sync)



## In Progress

Not started yet.



## Completed in Last Run

Gap 11 — Real-Time Team Messaging / Collaboration Channels

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

11\. Real-Time Team Messaging / Collaboration Channels



## Remaining Gap Items

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

Implement Gap 12 — Email Integration (Gmail / Outlook Sync).

This is a complex external API integration. Inspect existing integrations module first:
- backend/app/api/v1/endpoints/integrations.py — check for any email-related endpoints
- backend/app/models/ — check for EmailMessage, EmailThread, EmailAccount models

Build pragmatic implementation (no live OAuth in this build — use stub/simulation):
1. EmailAccount model — provider (GMAIL/OUTLOOK/SMTP), email, connected status, sync_enabled
2. EmailThread model — external_thread_id, subject, participants, linked_module, linked_object_id
3. EmailMessage model — thread_id, from_email, to_emails, subject, body_text, received_at, is_inbound, is_read
4. EmailTemplate model — name, subject_template, body_template, module
5. Service: simulate_sync() — generate realistic demo email threads linked to customers/suppliers
6. Service: send_from_record() — compose and log outgoing email linked to a record
7. Endpoints: GET /email/accounts, GET /email/threads, GET /email/threads/{id}/messages,
   POST /email/send, GET /email/threads?linked_to={object_id}
8. Frontend: /dashboard/email page with thread list + message view + compose



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 11 additions:
backend/app/models/messaging.py — New file: ChannelType/MemberRole enums + ChatChannel, ChannelMember, ChannelMessage models
backend/app/schemas/messaging.py — New file: ChannelCreate/Read, MessageCreate/Read, MessagePage, DMCreate schemas
backend/app/api/v1/endpoints/messaging.py — New file: 11 endpoints (list/create channels, DM, join, get/post messages, thread, edit, delete, search)
backend/app/api/v1/router.py — Registered messaging router at /messaging
frontend/src/lib/messaging.ts — New file: Channel/Message/MessagePage types + messagingApi + timeAgo utility
frontend/src/app/dashboard/messages/page.tsx — New full-featured chat UI: channel sidebar with unread badges, message thread with hover actions (reply/edit/delete), thread view, search overlay, compose with Enter-to-send, 5s auto-refresh polling
frontend/src/components/nav-config.tsx — Added Team Messages nav entry under Chatter & Timeline



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 12: Email Integration.

Build a practical email management layer — not full OAuth (that needs user credentials).
Instead:
- Store email accounts (connected via config, or demo mode)
- Sync/store email threads linked to ERP records
- Allow composing + logging outbound emails from within ERP records
- Show email history on customer/supplier/order pages

Key design: EmailThread links to any ERP object via (linked_module, linked_object_id) — same
pattern as the approval workflow and messaging link_module approach.

Check integrations.py endpoint first — there may be existing email-related stubs.
