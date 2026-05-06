# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 13 — Multi-Company / Multi-Branch Architecture



## In Progress

Not started yet.



## Completed in Last Run

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



## Remaining Gap Items

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

Implement Gap 13 — Multi-Company / Multi-Branch Architecture.

This is a STRUCTURAL gap. Inspect existing system first:
- backend/app/models/user.py — does User have company_id?
- backend/app/models/master.py — does Product/Material have company_id?
- backend/app/models/ — check if Company or Branch model exists

Key decisions:
- Pragmatic approach: add Company model (not full multi-tenant DB isolation)
- Add company_id + branch_id to key models (Product, Warehouse, Customer, Supplier, Budget, PO, SO)
- Add Company CRUD + Branch CRUD endpoints
- Add company context to user sessions (current_company_id in JWT or header)
- Consolidated reporting: GET /companies/{id}/summary — cross-entity financial summary
- Frontend: company switcher in header, company admin page

DO NOT attempt full database-level tenancy isolation (too complex for this build).
Use application-level filtering: each query adds .where(model.company_id == current_company_id).

Scope: add Company + Branch models, user-company assignment, basic CRUD,
company switcher UI. Do NOT rewrite existing queries to add company filtering
(that is a separate migration effort).



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 12 additions:
backend/app/models/email_integration.py — New file: EmailProvider enum + EmailAccount, EmailThread, EmailMessage, EmailTemplate models
backend/app/schemas/email_integration.py — New file: full CRUD schemas for accounts, threads, messages, send request, templates
backend/app/api/v1/endpoints/email_integration.py — New file: account CRUD, thread list/detail/link, send email, simulate sync (5 realistic demo emails), template CRUD
backend/app/api/v1/router.py — Registered email_integration router at /email
frontend/src/lib/email.ts — New file: EmailAccount/Thread/Message/Template types + emailApi + PROVIDER_COLOR + fmtEmailDate
frontend/src/app/dashboard/email/page.tsx — Full email client UI: account switcher, thread list with unread badges, message view with inbound/outbound bubbles, compose modal, sync button, link-to-record display
frontend/src/components/nav-config.tsx — Added Email Inbox nav entry under Integrations



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 13: Multi-Company / Multi-Branch Architecture.

Pragmatic approach — do NOT add company_id to every existing model (too risky).
Instead:
1. Company model — id, name, registration_no, country, base_currency, is_active
2. Branch model — id, company_id, name, branch_code, address, is_active
3. UserCompanyAccess — user_id, company_id, role (ADMIN/USER/VIEWER), is_default
4. CompanySummary service — aggregate KPIs per company (revenue, expenses, employees, products)
5. Endpoints: GET/POST/PATCH /companies, GET/POST /companies/{id}/branches, 
   POST /companies/{id}/users (grant access), GET /companies/{id}/summary
6. Frontend: /dashboard/companies page (admin), company switcher component in header

The company switcher should store selected company_id in localStorage and pass it as
X-Company-ID header on requests. Existing data is treated as belonging to the default company.
