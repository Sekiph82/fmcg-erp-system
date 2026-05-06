# TASKS2.md



## Current Phase

Phase 1 — Critical ERP Foundation



## Current Gap

Gap 5 — Serialized Inventory / Serial Number Tracking



## In Progress

Not started yet.



## Completed in Last Run

Gap 4 — Budget Planning & Variance Analysis

Gap 3 — eTIMS / KRA e-Invoice Integration

Gap 2 — Multi-Currency with Real-Time Exchange Rates

Gap 1 — Full Double-Entry General Ledger



## Implemented Gap Items

1\. Full Double-Entry General Ledger

2\. Multi-Currency with Real-Time Exchange Rates

3\. eTIMS / KRA e-Invoice Integration

4\. Budget Planning & Variance Analysis



## Remaining Gap Items

5\. Serialized Inventory / Serial Number Tracking

6\. Manufacturing Execution System Depth

7\. MRP Engine Hardening

8\. Inventory Valuation & Costing Engine

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

Implement Gap 5 — Serialized Inventory / Serial Number Tracking.

Existing system has batch/lot tracking in inventory. Need per-unit serial number tracking.

Focus on:
- SerialNumber model: serial_no, product_id, status (IN_STOCK/SOLD/SCRAPPED/IN_REPAIR),
  current_location (warehouse_id), batch_id (optional link), warranty_expiry
- SerialMovement model: serial_id, from_location, to_location, moved_at, reference_type, reference_id
- API: assign serial numbers, lookup history, dispatch validation (block if not IN_STOCK),
  warranty status endpoint
- Frontend: serial number lookup page, movement history, serial assignment on goods receipt



## Blockers

App uses create_all — no migration cycle needed.



## Files Changed in Last Run

Gap 4 additions:
backend/app/models/finance.py — Added BudgetType enum, version + budget_type columns to Budget; updated UniqueConstraint
backend/app/schemas/finance.py — Added BudgetType import, budget_type/version to BudgetCreate/BudgetRead, BudgetAlertRow schema, utilization_pct to BudgetVsActualRow
backend/app/services/finance_service.py — Fixed budget_vs_actual() to use posted GL data, added _get_gl_actual() helper, added budget_alerts() service
backend/app/api/v1/endpoints/finance.py — Added lock/revise budget endpoints, budget-alerts report endpoint, BudgetType/BudgetAlertRow imports
frontend/src/lib/finance.ts — Added BudgetType, updated Budget interface, added BudgetAlertRow, added lockBudget/reviseBudget/budgetAlerts API methods
frontend/src/app/dashboard/finance/budget/page.tsx — Added KPI cards, alert section, utilization bar, budget_type/version display, lock/revise buttons



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 5: Serialized Inventory / Serial Number Tracking.

1. Create SerialNumber model in backend/app/models/inventory.py (or new file):
   - Fields: id, serial_no (unique), product_id, batch_id (nullable),
     status (IN_STOCK/SOLD/SCRAPPED/IN_REPAIR/RETURNED), warehouse_id (nullable),
     warranty_expiry (Date, nullable), notes
   - Check if inventory.py exists and what models are there

2. Create SerialMovement model for history tracking:
   - Fields: id, serial_id, from_status, to_status, from_warehouse_id, to_warehouse_id,
     reference_type (GRN/DISPATCH/ADJUSTMENT), reference_id, moved_at, moved_by_id

3. Backend: schemas + CRUD + service + endpoints in appropriate file
   - GET /inventory/serials/ — list with filters (product, status, warehouse)
   - POST /inventory/serials/ — create/assign (bulk or single)
   - GET /inventory/serials/{serial_no} — lookup by serial number
   - GET /inventory/serials/{id}/history — movement history
   - POST /inventory/serials/{id}/transfer — change status/location

4. Frontend: new page at /dashboard/inventory/serials/page.tsx
   - Search by serial number
   - List with product, status, location, warranty columns
   - Movement history drawer/modal

5. Check existing inventory module file paths first — do not duplicate models.

Key files to inspect:
- backend/app/models/ (find inventory-related models)
- backend/app/api/v1/endpoints/ (find inventory endpoints)
- frontend/src/components/nav-config.tsx (to add nav entry)
