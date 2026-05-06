# TASKS2.md



## Current Phase

Phase 1 — Critical ERP Foundation



## Current Gap

Gap 9 — Workflow Engine & Approval System



## In Progress

Not started yet.



## Completed in Last Run

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



## Remaining Gap Items

9\. Workflow Engine & Approval System

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

Implement Gap 9 — Workflow Engine & Approval System.

Existing system has basic roles + approve endpoints on individual modules (budget, MRP, shop floor).
No generic approval engine.

Files to inspect first:
- backend/app/models/ — check if any file has "Workflow", "ApprovalMatrix", "Approval" models
- backend/app/api/v1/endpoints/ — check for any workflow endpoint
- frontend/src/app/dashboard/ — check for any approval or workflow pages

Key items to build:
1. ApprovalRule model: module (PR/PO/Budget/Production), amount_threshold, role_required, level (1/2/3)
2. ApprovalRequest model: object_type, object_id, status (PENDING/APPROVED/REJECTED/ESCALATED),
   requested_by, current_level, steps (JSON audit trail)
3. Service: submit_for_approval(db, object_type, object_id, amount, requester_id)
4. Service: approve(db, request_id, approver_id, notes)
5. Service: reject(db, request_id, approver_id, reason)
6. Service: escalate_overdue(db) — find requests > SLA hours, escalate
7. Endpoints: GET /approvals/ (my pending), POST /approvals/{id}/approve, POST /approvals/{id}/reject
8. Frontend: approval inbox page (/dashboard/approvals)



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 8 additions:
backend/app/models/inventory.py — Added InventoryValuationMethod enum + CostLayer model
backend/app/schemas/inventory.py — Added ValuationRow, ValuationSummary, AgingRow schemas
backend/app/services/inventory_service.py — Added create_cost_layer(), consume_fifo_layers(), inventory_valuation_report(), inventory_aging_report() service functions
backend/app/api/v1/endpoints/inventory.py — Added GET /inventory/valuation and GET /inventory/aging endpoints
frontend/src/lib/inventory.ts — Added ValuationRow, ValuationSummary, AgingRow types + inventoryApi.valuation() + inventoryApi.aging()
frontend/src/app/dashboard/inventory/valuation/page.tsx — New valuation dashboard: KPI cards, Valuation Report tab (FIFO/WAC/Std side-by-side), Aging tab (bucket summary + layer detail)
frontend/src/components/nav-config.tsx — Added Valuation nav entry under Warehouse & Inventory



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 9: Workflow Engine & Approval System.

Inspect backend/app/models/ for any existing Workflow/Approval models before adding new ones.
Also check if notifications.py service can be used for approval notifications.

The approval engine should be GENERIC — not tied to one module. Any module (PO, PR, Budget,
Production Order, Invoice) can submit an approval request. The ApprovalRule table maps
(module, amount_threshold) → (required_role, level).

Multi-level approvals: Level 1 (supervisor) → Level 2 (manager) → Level 3 (director).
Amount thresholds trigger different levels.

Delegation: if approver is out, requests auto-route to delegate (delegate_id on User or separate table).

SLA: each rule has sla_hours. If request sits > sla_hours, auto-escalate to next level.
