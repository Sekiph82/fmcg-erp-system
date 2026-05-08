# TASKS2.md



## Current Phase

Phase 2 - High Importance (Tier 2)



## Current Gap

Gap 25 - Sales Order to Cash Full Lifecycle



## In Progress

Gap 25 - Sales Order to Cash Full Lifecycle (inspection started, no files changed yet)



## Completed in Last Run

Gap 24 - Procurement System Depth

Gap 23 - No-Code / Extensibility Layer

Gap 22 - Internal Collaboration Layer Expansion

Gap 21 - CRM Pipeline Depth

Gap 20 - Bank API Integration / Open Banking

Gap 19 - Electronic Signatures

Gap 18 - Retail / Shop POS

Gap 17 - Project Management with Gantt & Dependencies

Gap 16 - Helpdesk / Customer Complaint Ticketing

Gap 15 - Quote / Estimation Module

Gap 14 - WhatsApp Business API Integration

Gap 13 - Multi-Company / Multi-Branch Architecture

Gap 12 - Email Integration Gmail / Outlook Sync

Gap 11 - Real-Time Team Messaging / Collaboration Channels

Gap 10 - Batch Recall Operational Hardening

Gap 9 - Workflow Engine & Approval System

Gap 8 - Inventory Valuation & Costing Engine

Gap 7 - MRP Engine Hardening

Gap 6 - Manufacturing Execution System (MES) Depth

Gap 5 - Serialized Inventory / Serial Number Tracking

Gap 4 - Budget Planning & Variance Analysis

Gap 3 - eTIMS / KRA e-Invoice Integration

Gap 2 - Multi-Currency with Real-Time Exchange Rates

Gap 1 - Full Double-Entry General Ledger



## Implemented Gap Items

1. Full Double-Entry General Ledger

2. Multi-Currency with Real-Time Exchange Rates

3. eTIMS / KRA e-Invoice Integration

4. Budget Planning & Variance Analysis

5. Serialized Inventory / Serial Number Tracking

6. Manufacturing Execution System (MES) Depth

7. MRP Engine Hardening

8. Inventory Valuation & Costing Engine

9. Workflow Engine & Approval System

10. Batch Recall Operational Hardening

11. Real-Time Team Messaging / Collaboration Channels

12. Email Integration Gmail / Outlook Sync

13. Multi-Company / Multi-Branch Architecture

14. WhatsApp Business API Integration

15. Quote / Estimation Module

16. Helpdesk / Customer Complaint Ticketing

17. Project Management with Gantt & Dependencies

18. Retail / Shop POS

19. Electronic Signatures

20. Bank API Integration / Open Banking

21. CRM Pipeline Depth

22. Internal Collaboration Layer Expansion

23. No-Code / Extensibility Layer

24. Procurement System Depth



## Remaining Gap Items

25. Sales Order to Cash Full Lifecycle

26. Warehouse Execution Layer

27. Quality System Completion

28. Knowledge Base / Internal Wiki

29. Employee Survey & Engagement Module

30. VoIP / Call Center Integration

31. Customer Loyalty Program

32. Recurring Billing / Auto-Invoicing

33. Video Meeting Integration

34. Customer / Product NPS Tracking

35. Native Mobile Apps Support Layer

36. API Developer Portal / GraphQL Layer

37. Real-Time Notification Center

38. Reporting & BI Layer

39. Document Management System

40. Customer / Supplier Portal Expansion

41. Audit Logs & Compliance Trail

42. Mobile-First Field Sales Expansion

43. Resource & Calendar Scheduling System

44. Integration Marketplace / Connector Hub

45. Returnable Packaging / Container Management

46. New Product Development Workflow

47. Route Optimization for Van Sales

48. Consumer Complaint Management Linked to Batch

49. Regulatory Certificate Tracking

50. Dynamic / AI Pricing Engine

51. Brand Asset / Label Design Management

52. Market Intelligence / Competitor Tracking

53. Co-Packing / Toll Manufacturing

54. HACCP System Expansion

55. Allergen & Nutrition Management

56. GS1 Barcode & Labeling Advanced

57. Shelf-Life / FEFO Control Expansion

58. Trade Promotion Management Expansion

59. Secondary Sales / Distributor Sell-Through Expansion

60. Kenya Localization Expansion

61. IoT / Real-Time Machine Data Streaming

62. ML-Based Demand Forecasting Engine

63. Blockchain-Based Traceability

64. Carbon Footprint Per Product

65. AI-Powered Receipt OCR

66. Natural Language ERP Control

67. AI Agent Governance Framework

68. Predictive Maintenance

69. ESG Intelligence & Sustainability Optimization

70. Plugin / App Marketplace Architecture



## Next Immediate Task

Implement Gap 25 - Sales Order to Cash Full Lifecycle.

Inspect first:
- backend/app/models/sales.py - existing SalesOrder, SalesOrderLine models
- backend/app/api/v1/endpoints/sales.py - current sales endpoints
- frontend/src/app/dashboard/sales/ - existing sales pages
- frontend/src/lib/sales.ts - existing sales lib

Expected: Basic sales order exists. Missing: credit limit check on SO creation, Return Management (RMA) workflow, payment allocation to invoices, customer statements (aged balance), overdue collection workflow, margin tracking per order.

Build next coherent slice:
1. Inspect existing sales backend/frontend.
2. Add ReturnMerchandiseAuthorization (RMA) model + return lines.
3. Add credit limit enforcement: check customer credit limit before confirming SO.
4. Add customer statement endpoint (outstanding invoices + payments + aged balance).
5. Add margin tracking: extend SO/SOLine with cost_price + gross_margin computed field.
6. Add RMA frontend page.
7. Add customer statement page.
8. Update nav under Sales & Distribution.



## Blockers

No schema migration blocker: app uses create_all.

Validation environment blocker: this shell has no python/py launcher on PATH, and backend/venv/Scripts/python.exe points to a missing Python 3.12 install. Backend compile could not be run until the local Python environment is repaired.



## Files Changed in Last Run

Gap 24 additions:
backend/app/models/procurement.py - MODIFIED: Added RFQStatus, RFQResponseStatus, BPAStatus enums; added RFQRequest model (rfq_no, title, material_id, product_id, quantity, unit, required_by, response_deadline, status, awarded_supplier_id, notes, created_by_id); added RFQResponse model (rfq_id, supplier_id, quoted_unit_price, quoted_currency, lead_time_days, valid_until, payment_terms, notes, status, score); added BlanketPurchaseAgreement model (bpa_no, supplier_id, material_id, product_id, agreed_unit_price, currency, agreed_quantity, consumed_quantity, unit, valid_from, valid_to, payment_terms, status); added AutoReorderPolicy model (material_id, product_id, warehouse_id, reorder_point, reorder_quantity, max_stock_level, lead_time_days, preferred_supplier_id, auto_create_pr, active_flag)
backend/app/schemas/procurement.py - MODIFIED: Added RFQStatus/RFQResponseStatus/BPAStatus imports; added RFQResponseCreate, RFQResponseRead, RFQCreate, RFQUpdate, RFQRead, RFQDetailRead, BlanketAgreementCreate, BlanketAgreementUpdate, BlanketAgreementRead (with remaining_quantity + is_expired computed fields), AutoReorderPolicyCreate, AutoReorderPolicyUpdate, AutoReorderPolicyRead schemas
backend/app/api/v1/endpoints/procurement.py - MODIFIED: Added RFQRequest/RFQResponse/BlanketPurchaseAgreement/AutoReorderPolicy model imports; added all new schema imports; added GET/POST /rfq/ + GET/PATCH /rfq/{id} + POST /rfq/{id}/responses endpoints; added GET/POST /bpa/ + PATCH /bpa/{id} endpoints; added GET/POST /reorder-policies/ + PATCH/DELETE /reorder-policies/{id} endpoints; added _build_rfq_detail() helper
frontend/src/lib/procurement.ts - MODIFIED: Added RFQStatus, RFQResponseStatus, BPAStatus types; added RFQResponseRead, RFQRead, RFQDetail, BlanketAgreement, AutoReorderPolicy interfaces; added listRFQs/createRFQ/getRFQ/updateRFQ/addRFQResponse, listBPAs/createBPA/updateBPA, listReorderPolicies/createReorderPolicy/updateReorderPolicy/deleteReorderPolicy API methods
frontend/src/app/dashboard/procurement/rfq/page.tsx - NEW: RFQ management page - list table with status filter, detail panel showing supplier responses with award button, create modal, add-response modal
frontend/src/app/dashboard/procurement/blanket-agreements/page.tsx - NEW: Blanket agreements page - list with KPI cards (active/expired/total value), create/edit modal, expiring-soon highlight, cancel action
frontend/src/app/dashboard/procurement/reorder-policies/page.tsx - NEW: Reorder policies page - list with auto_create_pr status, create/edit modal with material/product ID, reorder point/qty, lead time, preferred supplier, active toggle
frontend/src/components/nav-config.tsx - MODIFIED: Added RFQ, Blanket Agreements, Reorder Policies nav entries under Procurement section

Gap 23 additions:
backend/app/models/custom_fields.py - MODIFIED: Added FieldWidth, WFTriggerEvent, WFActionType enums; added field_width column; added WorkflowTriggerRule model
backend/app/schemas/custom_fields.py - MODIFIED: Added field_width to schemas; added FormLayoutItem/FormLayoutReorder/WorkflowRuleOut/WorkflowRuleCreate/WorkflowRuleUpdate schemas
backend/app/services/custom_fields_service.py - MODIFIED: Added get_form_layout/reorder_form_layout/list_workflow_rules/create_workflow_rule/update_workflow_rule/delete_workflow_rule services
backend/app/api/v1/endpoints/custom_fields.py - MODIFIED: Added form layout and workflow rules endpoints
frontend/src/lib/custom_fields.ts - MODIFIED: Added new types, interfaces, API methods, and constants
frontend/src/app/dashboard/custom-fields/form-builder/page.tsx - NEW: Visual form builder with HTML5 drag-and-drop
frontend/src/app/dashboard/custom-fields/workflow-rules/page.tsx - NEW: Workflow rules CRUD page
frontend/src/app/dashboard/custom-fields/page.tsx - MODIFIED: Extended quick links
frontend/src/components/nav-config.tsx - MODIFIED: Added Form Builder + Workflow Rules entries



## Validation Results

Frontend TypeScript: PASS (npm.cmd run type-check, 0 errors)

Backend Python compile: BLOCKED (python and py not found; backend venv python points to missing C:\Users\sekip\AppData\Local\Programs\Python\Python312\python.exe)

Backend import chain: NOT RUN due local Python environment blocker above



## Notes for Next Claude Run

Gap 24 implementation notes:
- RFQRequest.status transitions: DRAFT → SENT (via update endpoint) → RESPONSES_RECEIVED (auto-set when first response submitted) → AWARDED (via update with awarded_supplier_id).
- RFQResponse: one row per RFQ+supplier. On re-submit, updates existing row. Status auto-set to SUBMITTED on addRFQResponse.
- BlanketPurchaseAgreement: consumed_quantity starts at 0. Future enhancement: auto-increment on PO line creation linked to BPA. BlanketAgreementRead has computed remaining_quantity and is_expired.
- AutoReorderPolicy: checked by MRP engine (future). auto_create_pr=true means MRP will generate PRs automatically when stock falls below reorder_point.
- Frontend RFQ page shows split view: list left, detail panel right. Supplier IDs shown as UUID prefix until supplier lookup implemented (needs supplier search endpoint integration in future enhancement).
- Expiring soon alert: agreements valid_to within 30 days highlighted in amber.

Gap 25 start: Inspect backend/app/models/sales.py and backend/app/api/v1/endpoints/sales.py before coding. Check if RMA model exists. Look at existing invoice/payment models to understand credit limit and payment allocation context.
