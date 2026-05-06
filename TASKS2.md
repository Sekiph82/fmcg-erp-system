# TASKS2.md



## Current Phase

Phase 1 — Critical ERP Foundation



## Current Gap

Gap 8 — Inventory Valuation & Costing Engine



## In Progress

Not started yet.



## Completed in Last Run

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



## Remaining Gap Items

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

Implement Gap 8 — Inventory Valuation & Costing Engine.

Existing system has:
- Stock model (quantity_on_hand per warehouse/lot/product)
- MaterialConsumption (actual qty used in production)
- ProductionOrder (with total_material_cost finalized)
- StockMovement (every qty change)
- ProductCost / ProductionCostEntry in finance.py

Key gaps to fill:
- FIFO / Weighted Average / Standard Cost valuation methods
- Cost layer tracking (FIFO requires ordered layers: date, qty, unit_cost)
- Real-time COGS posting when stock is issued/sold
- Inventory valuation report (total inventory value by method)
- Inventory aging valuation (how long stock has been held)
- GL integration for every stock movement

Files to inspect first:
- backend/app/models/inventory.py (existing Stock, StockMovement models)
- backend/app/models/finance.py (existing GL/Journal models)
- backend/app/services/inventory_service.py (if exists)
- frontend/src/app/dashboard/inventory/ (existing pages)

DO NOT re-implement what exists. Inspect existing stock movement and costing models.
Add only the FIFO layer tracking and valuation reports.



## Blockers

App uses create_all — no migration needed.

GitHub push was blocked by 840MB PDF in history. Fixed: rewrote 12 commits with
git filter-branch, added KenyaFactoryAI/imports/**/*.pdf to .gitignore, pushed
successfully (commit a2e38a6).



## Files Changed in Last Run

Gap 7 additions:
backend/app/models/master.py — Added minimum_order_qty field to Material model
backend/app/models/mrp.py — Added frozen_horizon_days to MRPRun; added MRPExceptionType, MRPExceptionSeverity enums; added MRPException model
backend/app/schemas/mrp.py — Added frozen_horizon_days to MRPRunCreate/MRPRunOut; added MRPExceptionOut schema
backend/app/services/mrp_service.py — Fixed MOQ to use Material.minimum_order_qty with ceiling rounding; added frozen window filter to _build_so_demand; added exception generation (SHORTAGE/EXCESS_STOCK/LATE_ORDER) at end of _do_mrp; added frozen_horizon_days to create_mrp_run
backend/app/api/v1/endpoints/mrp.py — Added MRPException/MRPExceptionOut imports; pass frozen_horizon_days in trigger; added GET /exceptions and PATCH /exceptions/{id}/acknowledge endpoints
frontend/src/lib/mrp.ts — Added frozen_horizon_days to MRPRun/MRPRunCreate; added MRPException type; added getExceptions/acknowledgeException API methods
frontend/src/app/dashboard/mrp/workbench/page.tsx — New planner workbench page: exceptions tab (with acknowledge), supply/demand tab, draft suggestions tab (quick approve/reject)
frontend/src/components/nav-config.tsx — Added Planner Workbench nav entry



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 8: Inventory Valuation & Costing Engine.

Inspect these files first:
- backend/app/models/inventory.py — Stock, Lot, StockMovement models
- backend/app/models/finance.py — JournalEntry/JournalLine for GL posting
- backend/app/services/inventory_service.py (may not exist — check)

Key additions needed:
1. CostLayer model — FIFO layers: product_id/material_id, lot_id, receipt_date, qty, unit_cost, qty_remaining
2. InventoryValuationMethod enum (FIFO, WEIGHTED_AVG, STANDARD)
3. Service: compute_fifo_cost() — consumes layers in FIFO order
4. Service: weighted_avg_cost() — total_value / total_qty
5. Service: inventory_valuation_report() — total inventory value by method
6. Service: inventory_aging() — days held × qty × unit_cost per lot
7. GL posting on stock issue — debit COGS, credit Inventory Asset
8. Endpoint: GET /inventory/valuation — summary by method
9. Frontend: valuation dashboard page at /dashboard/inventory/valuation
