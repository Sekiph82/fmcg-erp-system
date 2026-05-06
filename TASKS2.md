# TASKS2.md



## Current Phase

Phase 1 — Critical ERP Foundation



## Current Gap

Gap 7 — MRP Engine Hardening



## In Progress

Not started yet.



## Completed in Last Run

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



## Remaining Gap Items

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

Implement Gap 7 — MRP Engine Hardening.

Existing MRP endpoint is at /mrp. Need to check what already exists before adding.

Files to inspect first:
- backend/app/api/v1/endpoints/mrp.py — list existing endpoints
- backend/app/models/ — check for MRPRun, MRPLine, MRPException models
- backend/app/services/mrp_service.py (if exists)
- frontend/src/app/dashboard/production/planning/ or /mrp/ pages

Key gaps from spec:
- Exception message system (shortage, delay, risk alerts)
- Lead-time aware planning (supplier lead times)
- Minimum Order Quantity enforcement
- Frozen planning window (freeze horizon)
- Simulation mode (what-if scenarios)
- Planner workbench dashboard
- Demand aggregation (sales orders + forecast + safety stock combined view)

DO NOT re-implement what exists. Inspect first, extend only the gaps.



## Blockers

App uses create_all — no migration cycle needed.



## Files Changed in Last Run

Gap 6 additions:
backend/app/schemas/production_costing.py — Added WIPRow, VarianceDetailRow, WorkCenterUtilRow schemas
backend/app/services/production_cost_service.py — Added get_wip_report(), get_variance_detail(), get_work_center_utilization() service functions
backend/app/api/v1/endpoints/production_costing.py — Added GET /wip, GET /variance-detail, GET /work-center-utilization endpoints
frontend/src/lib/productionCosting.ts — Added WIPRow, VarianceDetailRow, WorkCenterUtilRow types + api methods (wip, varianceDetail, workCenterUtilization)
frontend/src/app/dashboard/production/wip/page.tsx — New WIP valuation dashboard
frontend/src/app/dashboard/production/variance/page.tsx — New variance detail + work center utilization tabbed page
frontend/src/components/nav-config.tsx — Added WIP Valuation and Variance Analysis nav entries



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 7: MRP Engine Hardening.

Existing MRP system likely has: run MRP, get MRP output, procurement suggestions.
Check backend/app/api/v1/endpoints/mrp.py and related service files.

Key true gaps (not yet implemented):
1. Exception messages — when MRP run finds shortage/late delivery/overstock → create MRPException records
   with type (SHORTAGE/LATE_DELIVERY/EXCESS_STOCK), material_id, qty, due_date
2. Frozen planning window — ignore demand within frozen_horizon_days from today; store frozen_horizon in config
3. Simulation mode — run MRP with hypothetical sales orders/demand changes without persisting
4. Planner workbench — dashboard showing: open exceptions, pegged demand, supply/demand timeline per material

Check if MRPException model already exists. If yes, extend. If no, add.
