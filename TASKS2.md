# TASKS2.md



## Current Phase

Phase 2 — High Importance (Tier 2)



## Current Gap

Gap 20 — Bank API Integration / Open Banking



## In Progress

Not started yet.



## Completed in Last Run

Gap 19 — Electronic Signatures

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

19\. Electronic Signatures



## Remaining Gap Items

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

Implement Gap 20 — Bank API Integration / Open Banking.

Inspect first:
- backend/app/models/finance.py — check BankAccount / bank reconciliation models
- backend/app/models/bank_reconciliation.py — existing reconciliation model
- frontend/src/app/dashboard/ — check for bank-api or open-banking folder
- nav-config.tsx — placement under Finance & Accounting cluster

Expected: CSV import exists; no direct bank API sync. Build bank connection + sync simulation layer.

Build:
1. BankConnection model: connection_no, bank_name, account_name, account_number,
   bank_code, currency, status (ACTIVE/DISCONNECTED), last_synced_at,
   api_type (DIRECT/MOCK), credentials_ref (opaque string)
2. BankTransaction model: connection_id, txn_date, value_date, description,
   amount, direction (DEBIT/CREDIT), reference, balance_after,
   classification (auto-tagged), is_reconciled, matched_record_id, matched_record_type
3. BankSyncLog model: connection_id, synced_at, transactions_fetched, status, message
4. Endpoints:
   - POST /bank-api/connections — create bank connection
   - GET  /bank-api/connections — list connections
   - GET  /bank-api/connections/{id} — detail
   - POST /bank-api/connections/{id}/sync — trigger sync (mock: generate sample txns)
   - GET  /bank-api/transactions — list transactions (filter by connection, date, reconciled)
   - POST /bank-api/transactions/{id}/reconcile — mark reconciled + link to ERP record
   - POST /bank-api/transactions/{id}/classify — set classification
   - GET  /bank-api/dashboard — stats (balance, unreconciled count, last sync)
5. Frontend:
   - /dashboard/bank-api/page.tsx — connections list + sync + transactions table
   - Auto-classify rules: MPESA→payment, salary→payroll, etc.
6. Nav: under Finance & Accounting cluster

Sync approach:
- Real bank API integration requires bank-specific credentials (not available in demo)
- Implement MOCK sync that generates realistic Kenyan bank transactions
- Mock generates 10–20 transactions per sync with realistic descriptions (M-Pesa, salary, supplier, etc.)
- Mark api_type=MOCK for demo connections
- Real API: stub the integration point but don't call external APIs without credentials



## Blockers

App uses create_all — no migration needed.



## Files Changed in Last Run

Gap 19 additions:
backend/app/models/esign.py — NEW: SignatureRequest + SignatureRecord models + enums
backend/app/schemas/esign.py — NEW: full Pydantic schemas incl. ESignDashboard
backend/app/api/v1/endpoints/esign.py — NEW: create/list/pending-for-me/sign/decline/dashboard endpoints
backend/app/api/v1/router.py — registered esign router at /esign
backend/app/models/__init__.py — imported SignatureRequest, SignatureRecord models
frontend/src/lib/esign.ts — NEW: types, esignApi, statusColor helper
frontend/src/app/dashboard/esign/page.tsx — NEW: full page (KPI cards, tabs, requests table, canvas draw pad sign modal, decline modal, create modal with user search)
frontend/src/components/nav-config.tsx — added "E-Signatures" under Admin & System after Documents



## Validation Results

Backend Python compile: PASS (esign.py, schemas/esign.py, endpoints/esign.py)
Backend import chain: PASS (models OK, endpoint OK)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 20: Bank API Integration / Open Banking.

Key design decisions:
- No real bank credentials available — build MOCK sync engine
- Mock generates 10–20 realistic Kenyan bank transactions per sync trigger
- Transaction classification: keyword-based auto-tag (M-Pesa, salary, rent, etc.)
- Reconciliation: link transaction to existing ERP record (invoice, payment, etc.) via matched_record_type + matched_record_id (soft FK)
- BankConnection.credentials_ref: store opaque string (future: encrypt, for now plain)
- Balance tracking: each transaction stores balance_after (simulated running balance)
- Multi-currency: BankConnection has currency field (KES, USD, EUR)
- Sync log: keep history of every sync attempt with count + status

Nav: under Finance & Accounting cluster. Check nav-config.tsx for the exact section and surrounding items.
Finance section ID is likely "finance" — check for existing Bank Reconciliation item for exact placement.
