# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 15 — Quote / Estimation Module



## In Progress

Not started yet.



## Completed in Last Run

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



## Remaining Gap Items

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

Implement Gap 15 — Quote / Estimation Module.

Check existing sales models first:
- backend/app/models/sales.py — check if Quotation or Quote model exists
- backend/app/api/v1/endpoints/sales.py — check for quote endpoints
- frontend/src/app/dashboard/sales/ — check for quote pages

Expected: No quote model exists (system goes straight from CRM to Sales Order).

Build:
1. Quotation model — quote_no (unique), customer_id, status (DRAFT/SENT/ACCEPTED/REJECTED/EXPIRED),
   valid_until (date), version (int), discount_pct, currency, total_amount
2. QuotationLine model — product_id, description, qty, unit_price, discount_pct, line_total
3. Service: create_quote(), convert_to_so() — creates SalesOrder from accepted quote
4. Endpoints: full CRUD + POST /quotes/{id}/send + POST /quotes/{id}/accept +
   POST /quotes/{id}/reject + POST /quotes/{id}/convert-to-so + POST /quotes/{id}/revise (new version)
5. Frontend: /dashboard/sales/quotes page — quote list, create/edit form, convert-to-SO button
6. Win/loss tracking: status history, won/lost counts in dashboard



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 14 additions:
backend/app/models/whatsapp.py — New file: WAMessageDirection/Type/Status enums + WhatsAppConfig, WhatsAppMessage, WhatsAppTemplate models
backend/app/schemas/whatsapp.py — New file: full schemas for config, send text, send template, message read, template CRUD, simulate inbound
backend/app/api/v1/endpoints/whatsapp.py — New file: config CRUD, send text/template (demo mode → auto DELIVERED), Meta webhook handler (verification + message/status processing), message log, simulate-inbound, template CRUD, seed 5 FMCG demo templates
backend/app/api/v1/router.py — Registered whatsapp router at /whatsapp
frontend/src/lib/whatsapp.ts — New file: WAConfig/Message/Template types + waApi + STATUS_COLOR + STATUS_ICON maps
frontend/src/app/dashboard/whatsapp/page.tsx — Full WhatsApp client: account selector, KPI cards, Conversations tab (contact list + message bubbles inbound/outbound), Templates tab (display + seed demo), Config tab (account table), send modal (text or template with variable fields)
frontend/src/components/nav-config.tsx — Added WhatsApp nav entry under Integrations



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 15: Quote / Estimation Module.

Check backend/app/models/sales.py first — especially:
- SalesOrder model fields (to ensure quote→SO conversion matches)
- SOStatus enum values
- SalesOrderLine fields

Build quotation as pre-cursor to Sales Order:
Quote → DRAFT → SENT (to customer) → ACCEPTED/REJECTED/EXPIRED → convert to SO

Version bumping: when user revises a quote, old version stays, new DRAFT created with version+1.
Only one ACTIVE version per customer per quote (same quote_no, different version).
