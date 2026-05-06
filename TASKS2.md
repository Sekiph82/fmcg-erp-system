# TASKS2.md



## Current Phase

Phase 1 — Critical ERP Foundation



## Current Gap

Gap 10 — Batch Recall Operational Hardening



## In Progress

Not started yet.



## Completed in Last Run

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



## Remaining Gap Items

10\. Batch Recall Operational Hardening

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

Implement Gap 10 — Batch Recall Operational Hardening.

Existing system has recall logic (traceability module). Need enterprise-grade hardening.

Files to inspect first:
- backend/app/models/traceability.py — list existing recall models
- backend/app/api/v1/endpoints/traceability.py — list existing endpoints
- frontend/src/app/dashboard/ — find recall/traceability pages

Key items to add (only what's missing):
- Recall drill/test simulation mode (RecallDrill model)
- Predefined communication templates (RecallTemplate model)
- Effectiveness validation (closure checklist per recall)
- Immutable audit trail (every status change logged)
- Risk-based dashboard with SLA tracking
- Evidence/document attachment system

DO NOT re-implement what exists. Inspect first.



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 9 additions:
backend/app/models/workflow.py — New file: ApprovalModule/ApprovalStatus enums + ApprovalRule/ApprovalRequest/ApprovalStep models
backend/app/schemas/workflow.py — New file: ApprovalRuleCreate/Read/Update, ApprovalStepRead, ApprovalRequestRead, ApprovalSubmit, ApprovalAction, ApprovalReject schemas
backend/app/services/approval_service.py — New file: submit_for_approval(), approve_request(), reject_request(), cancel_request(), escalate_overdue(), get_pending_for_user()
backend/app/api/v1/endpoints/approvals.py — New file: GET / (inbox), GET /all, GET /{id}, POST /submit, POST /{id}/approve, POST /{id}/reject, POST /{id}/cancel, POST /admin/escalate-overdue, GET /rules/, POST /rules/, PATCH /rules/{id}, DELETE /rules/{id}
backend/app/api/v1/router.py — Registered approvals router at /approvals
frontend/src/lib/approvals.ts — New file: ApprovalModule/Status/Step/Request/Rule types + approvalsApi + STATUS_COLOR map
frontend/src/app/dashboard/approvals/page.tsx — New approval inbox page: My Inbox tab, All Requests tab, Rules admin tab, detail panel with step timeline, approve/reject actions, new rule modal
frontend/src/components/nav-config.tsx — Added Approval Inbox nav entry under Admin & System



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 10: Batch Recall Operational Hardening.

Inspect backend/app/models/traceability.py and backend/app/api/v1/endpoints/traceability.py
BEFORE adding anything. The system has recall logic already.

Expected true gaps:
1. RecallDrill model — simulate recall without actually stopping production
2. RecallCommunication templates — predefined messages per audience (retailer/consumer/regulator)
3. RecallEffectiveness — closure report: % units recovered, time to complete, SLA compliance
4. Immutable audit steps on recall (every status change: who/when/what)
5. Risk-based dashboard: severity × affected units × days open = risk score
6. Evidence attachments (FK to documents module)
