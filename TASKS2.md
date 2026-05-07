# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 16 — Helpdesk / Customer Complaint Ticketing



## In Progress

Not started yet.



## Completed in Last Run

Gap 15 — Quote / Estimation Module

Gap 14 — WhatsApp Business API Integration

Gap 13 — Multi-Company / Multi-Branch Architecture

Gap 12 — Email Integration Gmail / Outlook Sync

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

12\. Email Integration Gmail / Outlook Sync

13\. Multi-Company / Multi-Branch Architecture

14\. WhatsApp Business API Integration

15\. Quote / Estimation Module



## Remaining Gap Items

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

Implement Gap 16 — Helpdesk / Customer Complaint Ticketing.

Inspect first:
- backend/app/models/ — check for any existing helpdesk/ticket/complaint model
- frontend/src/app/dashboard/ — check for any helpdesk folder
- nav-config.tsx — check if helpdesk section exists

Expected: No model exists. Build from scratch.

Build:
1. TicketStatus enum: OPEN / IN_PROGRESS / ESCALATED / RESOLVED / CLOSED
2. TicketCategory enum: QUALITY / DELIVERY / BILLING / PRODUCT / OTHER
3. TicketPriority enum: LOW / MEDIUM / HIGH / CRITICAL
4. Ticket model: ticket_no, customer_id, category, priority, status,
   subject, description, lot_id (nullable FK → lots), sla_hours,
   first_response_at, resolved_at, customer_satisfaction (1-5),
   assigned_to_id, created_by_id
5. TicketComment model: ticket_id, body, is_internal, created_by_id
6. Service + endpoints:
   - CRUD tickets + GET /dashboard
   - POST /tickets/{id}/assign, /escalate, /resolve, /close
   - POST /tickets/{id}/comments
   - SLA breach tracking (resolved_at vs created_at + sla_hours)
7. Frontend: /dashboard/helpdesk/page.tsx
8. Nav: add under "Quality & Compliance" cluster (tickets are quality/service items)
   OR add a small section in Sales & Distribution — choose Quality & Compliance.



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 15 additions:
backend/app/models/quotation.py — NEW: QuoteStatus, Quotation, QuotationLine models
backend/app/schemas/quotation.py — NEW: full Pydantic schemas
backend/app/api/v1/endpoints/quotation.py — NEW: full CRUD + send/accept/reject/expire/revise/convert endpoints
backend/app/api/v1/router.py — registered quotation router at /quotes
backend/app/models/__init__.py — imported QuoteStatus, Quotation, QuotationLine
frontend/src/lib/quotations.ts — NEW: types, quoteApi, STATUS_COLORS, fmtCcy, fmtDate
frontend/src/app/dashboard/sales/quotes/page.tsx — NEW: full page with KPI cards, filter, table, create modal, reject modal, row actions
frontend/src/components/nav-config.tsx — added Quotations link to Sales & Distribution section



## Validation Results

Backend Python compile: PASS (all 5 files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 16: Helpdesk / Complaint Ticketing.

Key design decisions:
- lot_id link enables batch-level complaint tracking (ties into Gap 10 recall system)
- SLA hours configurable per category (QUALITY=4h, CRITICAL=1h, others=24h)
- customer_satisfaction score (1-5) captured on close
- TicketComment supports internal notes vs external replies
- Consider linking to Customer (sales.py) and Lot (inventory.py)

Check if Lot model has the right FK target name:
  grep "class Lot" backend/app/models/inventory.py
  — should be "lots" table

Nav placement: Under Quality & Compliance cluster (alongside qms, allergen, gs1).
OR under new "Customer Service" sub-cluster inside Sales & Distribution.
Prefer Quality & Compliance for FMCG context (complaint = quality event).
