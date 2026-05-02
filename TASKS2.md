# TASKS2.md



## Current Phase

Phase 1 — Critical ERP Foundation



## Current Gap

Gap 4 — Budget Planning & Variance Analysis



## In Progress

Not started yet.



## Completed in Last Run

Gap 1 — Full Double-Entry General Ledger

Gap 2 — Multi-Currency with Real-Time Exchange Rates

Gap 3 — eTIMS / KRA e-Invoice Integration



## Implemented Gap Items

1\. Full Double-Entry General Ledger

2\. Multi-Currency with Real-Time Exchange Rates

3\. eTIMS / KRA e-Invoice Integration



## Remaining Gap Items

4\. Budget Planning \& Variance Analysis

5\. Serialized Inventory / Serial Number Tracking

6\. Manufacturing Execution System Depth

7\. MRP Engine Hardening

8\. Inventory Valuation \& Costing Engine

9\. Workflow Engine \& Approval System

10\. Batch Recall Operational Hardening

11\. Real-Time Team Messaging / Collaboration Channels

12\. Email Integration Gmail / Outlook Sync

13\. Multi-Company / Multi-Branch Architecture

14\. WhatsApp Business API Integration

15\. Quote / Estimation Module

16\. Helpdesk / Customer Complaint Ticketing

17\. Project Management with Gantt \& Dependencies

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

29\. Employee Survey \& Engagement Module

30\. VoIP / Call Center Integration

31\. Customer Loyalty Program

32\. Recurring Billing / Auto-Invoicing

33\. Video Meeting Integration

34\. Customer / Product NPS Tracking

35\. Native Mobile Apps Support Layer

36\. API Developer Portal / GraphQL Layer

37\. Real-Time Notification Center

38\. Reporting \& BI Layer

39\. Document Management System

40\. Customer / Supplier Portal Expansion

41\. Audit Logs \& Compliance Trail

42\. Mobile-First Field Sales Expansion

43\. Resource \& Calendar Scheduling System

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

55\. Allergen \& Nutrition Management

56\. GS1 Barcode \& Labeling Advanced

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

69\. ESG Intelligence \& Sustainability Optimization

70\. Plugin / App Marketplace Architecture



## Next Immediate Task

Implement Gap 4 — Budget Planning & Variance Analysis.

Existing system has Budget/BudgetLine models and basic endpoints (backend/app/models/finance.py).
Budget approval exists. BUT: missing real actuals linking, monthly allocation enforcement,
CapEx tracking, spending alerts, budget revision workflow.

Focus on:
- Budget vs Actual: link budget lines to GL journal entries (not just cash transactions)
  Fix the budget_vs_actual service to use posted GL instead of returning zeros
- Budget approval workflow: notification on approve
- Add budget_revision (version bumping) — new BudgetRevision model or just version field
- Add CapEx budget type
- Threshold alerts: if actual > % of budget → generate alert
- Frontend: budget dashboard with real variance charts, drill-down page



## Blockers

Alembic migration cycle — app uses create_all, no blocking issue.



## Files Changed in Last Run

Gap 3 additions:
backend/app/models/tax_regulatory.py — Added ETimsSubmission, VATReturn, WithholdingTaxRecord models
backend/app/schemas/tax_regulatory.py — Added ETimsSubmissionRead, VATReturnCreate/Read, WithholdingTaxCreate/Read
backend/app/api/v1/endpoints/tax_regulatory.py — Added /etims/submit, /vat-returns/generate, /withholding-tax endpoints
frontend/src/app/dashboard/finance/etims/page.tsx — eTIMS submission dashboard
frontend/src/app/dashboard/finance/vat-returns/page.tsx — VAT3 return generation and filing
frontend/src/components/nav-config.tsx — Added eTIMS, VAT Returns to Tax & Regulatory nav

Gap 2 additions:
backend/app/models/finance.py — Added ExchangeRate model, RateSource enum
backend/app/schemas/finance.py — Added ExchangeRateCreate, ExchangeRateRead, FXConvertResult schemas
backend/app/services/finance_service.py — Added get_rate(), convert_to_kes()
backend/app/api/v1/endpoints/finance.py — Added /exchange-rates/ CRUD and convert endpoint
frontend/src/lib/finance.ts — Added ExchangeRate, FXConvertResult types and API methods
frontend/src/app/dashboard/finance/exchange-rates/page.tsx

Gap 1 additions:
backend/app/models/finance.py — Added AccountingPeriod model
backend/app/schemas/finance.py — Added GL report schemas
backend/app/services/finance_service.py — Added GL service functions
backend/app/api/v1/endpoints/finance.py — Added GL report + period endpoints
frontend/src/lib/finance.ts — Added GL report types
frontend/src/app/dashboard/finance/accounting/trial-balance/page.tsx
frontend/src/app/dashboard/finance/accounting/profit-loss/page.tsx
frontend/src/app/dashboard/finance/accounting/balance-sheet/page.tsx
frontend/src/app/dashboard/finance/accounting/general-ledger/page.tsx
frontend/src/app/dashboard/finance/accounting/chart-of-accounts/page.tsx
frontend/src/app/dashboard/finance/accounting/period-closing/page.tsx
frontend/src/app/dashboard/finance/accounting/journal/page.tsx
frontend/src/components/nav-config.tsx



## Validation Results

Backend Python compile: PASS (all modified files)
Frontend TypeScript: PASS (tsc --noEmit, 0 errors)



## Notes for Next Claude Run

Gap 4: Budget Planning & Variance Analysis.

1. Fix budget_vs_actual() in finance_service.py: currently returns zeros for actual.
   Use posted JournalLine data where account maps to budget category, OR use Invoice/Payment data.
   Simplest: use InvoiceStatus != DRAFT/CANCELLED sales + PurchaseInvoice data grouped by month.

2. Add BudgetVersion field to Budget model (Integer, default=1) for revision tracking.

3. Add budget threshold alert: when actual/budgeted > 0.9 (90%), create alert record.

4. Improve frontend budget/page.tsx to show real variance with color coding.
   Currently at: frontend/src/app/dashboard/finance/budget/page.tsx

5. Add "New Budget" form to budget page if not already there.

Context note: Budget model already has year, department, status (DRAFT/APPROVED/LOCKED), lines (category, month, budgeted_amount).
The service file ends with the budget_vs_actual function returning placeholder zeros.
