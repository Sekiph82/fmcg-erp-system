# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 19 — Electronic Signatures



## In Progress

Not started yet.



## Completed in Last Run

Gap 18 — Retail / Shop POS

Gap 17 — Project Management with Gantt & Dependencies

Gap 16 — Helpdesk / Customer Complaint Ticketing

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

16\. Helpdesk / Customer Complaint Ticketing

17\. Project Management with Gantt & Dependencies

18\. Retail / Shop POS



## Remaining Gap Items

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

Implement Gap 19 — Electronic Signatures.

Inspect first:
- backend/app/models/ — check for any existing signature/esign model
- backend/app/models/documents.py — check Document model for attachment hooks
- frontend/src/app/dashboard/ — check for esign folder
- nav-config.tsx — best placement (Administration & System or Sales & Distribution)

Expected: No signature model exists. Build from scratch.

Build:
1. SignatureRequest model: request_no, document_id (nullable), document_type (e.g. "contract", "quotation"),
   document_ref (str, the doc name), requester_id, signer_ids (junction), status (PENDING/SIGNED/DECLINED/EXPIRED),
   subject, message, expires_at, signed_count, required_count
2. SignatureRecord model: request_id, signer_id, signed_at, ip_address, user_agent,
   signature_data (base64 PNG or SVG path), status (PENDING/SIGNED/DECLINED)
3. Endpoints:
   - POST /esign/requests — create signature request
   - GET /esign/requests — list requests
   - GET /esign/requests/{id} — detail
   - POST /esign/requests/{id}/sign — signer submits signature
   - POST /esign/requests/{id}/decline — signer declines
   - GET /esign/requests/pending-for-me — my pending requests
   - GET /esign/dashboard — stats
4. Frontend:
   - /dashboard/esign/page.tsx — request list + create modal
   - Signature capture: HTML canvas draw pad (no external library)
5. Nav: under "Administration & System" cluster (documents-adjacent)

Signature capture approach:
- Canvas-based draw pad in frontend
- On sign, save canvas.toDataURL() as base64 PNG in signature_data field
- No external library (react-signature-canvas) — use plain canvas API



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 18 additions:
backend/app/models/pos.py — NEW: POSSessionStatus/PaymentMethod/SaleStatus enums + POSSession + POSSale + POSSaleLine models
backend/app/schemas/pos.py — NEW: full Pydantic schemas incl. POSDashboard
backend/app/api/v1/endpoints/pos.py — NEW: sessions (open/close/current/list) + sales (create/get/void) + dashboard endpoints
backend/app/api/v1/router.py — registered pos router at /pos
backend/app/models/__init__.py — imported POS models
frontend/src/lib/pos.ts — NEW: types, posApi, fmtKES
frontend/src/app/dashboard/pos/page.tsx — NEW: full touchscreen POS terminal (product grid, cart, payment modal, session controls)
frontend/src/components/nav-config.tsx — added "Point of Sale" section under Sales & Distribution

Gap 17 additions:
backend/app/models/project.py — NEW
backend/app/schemas/project.py — NEW
backend/app/api/v1/endpoints/project.py — NEW
frontend/src/lib/projects.ts — NEW
frontend/src/app/dashboard/projects/page.tsx — NEW
frontend/src/app/dashboard/projects/[id]/page.tsx — NEW (with Gantt chart)
frontend/src/components/nav-config.tsx — added Project Management under Planning cluster

Gap 16 additions:
backend/app/models/helpdesk.py — NEW
backend/app/schemas/helpdesk.py — NEW
backend/app/api/v1/endpoints/helpdesk.py — NEW
frontend/src/lib/helpdesk.ts — NEW
frontend/src/app/dashboard/helpdesk/page.tsx — NEW
frontend/src/components/nav-config.tsx — added Helpdesk under Quality & Compliance



## Validation Results

Backend Python compile: PASS (all files in this run)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 19: Electronic Signatures.

Key design decisions:
- No external e-sign service required (internal self-hosted implementation)
- Canvas-based signature pad in frontend (plain HTML canvas API, no library)
- SignatureRecord.signature_data stores base64 PNG string (may be large, use Text column)
- For multi-signer: all must sign for status → SIGNED; any decline → DECLINED
- IP address capture: FastAPI request.client.host in sign endpoint
- Audit immutability: once signed, SignatureRecord cannot be modified
- document_type is a free string (contract, quote, delivery_note, etc.)
- document_ref is a human-readable label (e.g. "Contract CT-2024-0001")
- The sign/decline endpoints should NOT require the user to own the request —
  only the signer_id in the request should be able to sign their record

Nav: under "Administration & System" cluster, after "Documents" item.
Check nav-config.tsx for the exact section ID and surrounding items.
