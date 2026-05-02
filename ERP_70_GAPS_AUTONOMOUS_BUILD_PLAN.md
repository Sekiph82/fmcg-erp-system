# ERP 70 Gaps Autonomous Build Plan

You are working inside the FMCG ERP repository.

Repository goal:
Turn this FMCG ERP into a production-grade vertical FMCG operating system by closing the 70 identified competitive gaps.

Core operating rule:
Do not wait for the user to write detailed prompts for each gap. For every gap item, generate your own internal implementation prompt, plan the work, implement it, test it, update TASKS2.md, then continue if there is enough context and usage budget.

Do not implement shallow placeholders.
Do not create fake frontend-only pages.
Do not mark a gap complete unless the feature has real usable behavior.

---

# GLOBAL EXECUTION CYCLE

For every run, follow this exact cycle:

1. Read ERP_70_GAPS_AUTONOMOUS_BUILD_PLAN.md.
2. Read TASKS2.md.
3. Determine the current phase and current gap.
4. Take the next incomplete gap.
5. Generate an internal detailed prompt for that gap.
6. Inspect existing code before editing.
7. Create an implementation plan.
8. Implement backend, frontend, permissions, navigation, audit, and tests where applicable.
9. Run available checks.
10. Update TASKS2.md.
11. If context/usage is low, stop safely.
12. If enough context/usage remains, start the next gap by reading TASKS2.md again and repeating the cycle.

---

# LIMIT / CONTEXT RULE

If context, token budget, or usage limit is close:
- Stop coding.
- Update TASKS2.md first.
- Clearly record:
  - what was completed
  - what is in progress
  - exact next file/task
  - blockers
- Do not continue half-blind.

When a new session starts, continue from TASKS2.md.

---

# REQUIRED TRACKING FILE

Always create or update TASKS2.md with this exact structure:

## Current Phase

## Current Gap

## In Progress

## Completed in Last Run

## Implemented Gap Items

## Remaining Gap Items

## Next Immediate Task

## Blockers

## Files Changed in Last Run

## Validation Results

## Notes for Next Claude Run

TASKS2.md is the memory bridge between sessions. Treat it as the source of truth.

---

# SELF-PROMPTING ENGINE

For every gap item, before coding, generate an internal execution prompt using this structure:

## Internal Gap Prompt

Gap number:
Gap name:
Business problem:
Current system assumption:
Files/modules to inspect:
Backend requirements:
Frontend requirements:
Database/model requirements:
Permission requirements:
Audit/logging requirements:
Integration requirements:
Testing requirements:
Definition of done:

After generating this internal prompt, execute it.

Do not ask the user to provide this prompt.
You must create it yourself from the gap description and existing code.

---

# PLANNING TEMPLATE

For every gap, create a short implementation plan before coding:

1. Existing System Analysis
2. Data Model Changes
3. Backend/API Changes
4. Frontend/UI Changes
5. Permission & Security Changes
6. Audit/Logging Changes
7. Navigation Placement
8. Tests / Validation
9. Risks
10. Definition of Done

---

# QUALITY CONTROL LOOP

After implementing each gap, re-check:

- Does the backend compile?
- Does the frontend compile?
- Are permissions respected?
- Is data persisted?
- Is the workflow usable by a real user?
- Are routes linked in navigation/search where needed?
- Are there no duplicate modules?
- Are there no broken imports?
- Are there no placeholder-only features?
- Is TASKS2.md updated?

If any answer is no, fix before marking complete.

---

# SIDEBAR / NAVIGATION RULE

The sidebar is rendered from:
- frontend/src/components/Sidebar.tsx
- frontend/src/components/nav-config.tsx

Keep the existing 14-domain sidebar structure.
Do not create more main sidebar titles unless absolutely necessary.
Maximum allowed main clusters: 16.

Preferred main clusters:

1. Dashboard
2. Master Data
3. Planning
4. Production / MES
5. Inventory & Warehouse
6. Quality & Compliance
7. Sales & Distribution
8. Procurement & Suppliers
9. Finance & Accounting
10. HR & Workforce
11. Logistics & Field Operations
12. Utilities & Sustainability
13. AI, Analytics & Intelligence
14. Administration & System

Optional only if truly needed:
15. Collaboration & Documents
16. Extensions & Integrations

Do not scatter new modules randomly.
Place every new page into the correct existing cluster.

---

# GENERAL BUILD RULES

For every feature:

1. Inspect existing related files first.
2. Reuse existing architecture.
3. Extend existing models/services/routes where possible.
4. Do not duplicate modules.
5. Add database models only when required.
6. Add schemas.
7. Add services/business logic.
8. Add API endpoints.
9. Add frontend pages/components.
10. Add permissions.
11. Add audit events where relevant.
12. Add tests if a test framework exists.
13. Update navigation only if the route should be user-facing.
14. Update TASKS2.md.
15. Run available validation commands.

---

# VALIDATION COMMANDS

Run what exists in the project:

Frontend:
- npm run lint
- npm run build
- npm run typecheck, if available

Backend:
- pytest, if available
- python -m compileall app, if applicable
- alembic check/migration commands, if configured

If dependencies are missing:
- Do not install random packages without need.
- Document the issue in TASKS2.md.
- Continue with static validation where possible.

---

## ## TIER 1 — Critical Gaps

Missing entirely or structurally incomplete. High legal/business impact.

## 1. Full Double-Entry General Ledger

Missing in: Our ERP — Has partial finance module (cashbook, receivables, budgets, landed cost, bank reconciliation) but no true double-entry accounting.

Every financial transaction in a compliant business must generate a balanced debit and credit entry, traceable to a structured Chart of Accounts. Without this, your system is a tracking tool, not a legally compliant accounting system.

What’s missing:

• Chart of Accounts (CoA) with hierarchy (Assets, Liabilities, Equity, Revenue, Expenses)
• Manual Journal Entries (adjustments, accruals, corrections)
• Automatic Journal Entries from transactions (PO, invoice, payroll, inventory)
• Trial Balance generation
• Profit & Loss Statement (real-time)
• Balance Sheet (real-time)
• General Ledger (per account drill-down)
• Period closing (monthly/year-end lock)
• Opening balance migration
• Tax posting rules (VAT, WHT, etc.)
• Multi-entity financial consolidation capability
• Audit-safe transaction immutability

Impact:

Without this:
• You cannot pass audits
• You cannot generate statutory reports
• You cannot comply with Kenya Companies Act
• Investors will not trust your financials

## 2. Multi-Currency with Real-Time Exchange Rates

Missing in: Entire system operates in KES only

An FMCG manufacturer imports raw materials globally. Forcing everything into KES breaks costing, payments, and financial accuracy.

What’s missing:

• Multi-currency purchase orders (USD, EUR, GBP, CNY)
• Multi-currency sales invoices (exports)
• Exchange rate table (manual + auto-fetch from CBK / ECB APIs)
• Currency gain/loss calculation at payment time
• Dual reporting (transaction currency + base currency KES)
• Foreign currency bank accounts
• Forex revaluation at period end
• Multi-currency GL posting
• Currency-aware costing (landed cost accuracy)

Impact:

• Landed cost becomes inaccurate
• Supplier payments miscalculated
• Export invoicing incorrect
• Financial reports unreliable

## 3. eTIMS / e-Invoice Integration (KRA — Kenya)

Missing in: Entire system

Kenya Revenue Authority mandates Electronic Tax Invoice Management System (eTIMS) for all VAT-registered companies.

What’s missing:

• eTIMS API integration for invoice signing
• TIMS device/API-based digital receipt generation
• Real-time invoice transmission to KRA
• VAT 3 return auto-generation from invoices
• Input/output VAT reconciliation
• KRA PIN validation for customers/suppliers
• Withholding Tax tracking
• Digital tax certificate generation

Impact:

• Legal non-compliance
• Heavy penalties and fines
• Possible business shutdown risk
• Cannot operate legally in Kenya

## 4. Budget Planning & Variance Analysis

Status: Partial — fields exist, no real system

Currently budgets are passive fields, not enforced financial controls.

What’s missing:

• Annual budget creation per department/cost center
• Monthly/quarterly budget allocation
• Budget vs actual real-time reporting
• Budget enforcement on Purchase Orders
• Payroll budget tracking
• CapEx planning and tracking
• Budget revision workflow with approval
• Forecast vs budget vs actual comparison
• Alerts when spending exceeds thresholds

Impact:

• No cost control
• Overspending only discovered late
• No financial discipline
• Management decisions based on incomplete data

## 5. Serialized Inventory / Serial Number Tracking

Missing in: Inventory system (only batch/lot exists)

Batch tracking ≠ serial tracking.
You cannot track individual high-value assets.

What’s missing:

• Serial number assignment per unit
• Serial-level movement tracking
• Ownership history
• Warranty tracking
• Repair/service history
• Serial-based dispatch validation
• Integration with asset management

Impact:

• No control over capital equipment
• No warranty/service tracking
• Compliance issues in exports
• Asset loss risk

## 6. Manufacturing Execution System (MES) Depth

Status: Strong foundation, but incomplete

You have production modules — but not full execution-level control.

What’s missing:

• Work center capacity planning
• Routing definition (multi-step production)
• Labor tracking per operation
• Machine setup/changeover tracking
• Scrap and yield variance tracking
• WIP (Work-in-Progress) valuation
• Production variance accounting
• Shop-floor tablet interface (operator UI)
• Real-time production monitoring
• Batch closing with cost locking

Impact:

• No real production efficiency tracking
• Costing inaccuracies
• No visibility into factory performance
• Weak operational control

## 7. MRP Engine Hardening (Critical Upgrade Needed)

Status: Exists but not production-grade

You already built MRP — good. But it lacks planning intelligence and automation depth.

What’s missing:

• Scheduled automatic MRP runs (daily/weekly)
• Exception message system (shortage, delay, risk alerts)
• Lead-time aware planning
• Minimum Order Quantity optimization
• Multi-level BOM explosion validation
• Demand aggregation (sales orders + forecast + safety stock)
• Frozen planning window
• Simulation mode (what-if scenarios)
• Planner workbench dashboard
• Constraint-based planning (capacity + material)

Impact:

• Planning errors
• Stockouts or overstock
• Inefficient procurement
• Manual intervention required

## 8. Inventory Valuation & Costing Engine

Status: Partial

Inventory exists, but financial integration is weak.

What’s missing:

• FIFO / Weighted Average / Standard Cost methods
• Cost layer tracking
• Real-time COGS posting
• Production cost roll-up (BOM-based costing)
• Landed cost allocation into inventory value
• Inventory revaluation tools
• Inventory aging valuation reports
• Integration with GL for every movement

Impact:

• Incorrect financial statements
• Wrong product margins
• Poor pricing decisions
• Audit failure risk

## 9. Workflow Engine & Approval System

Status: Basic roles exist, no real workflow engine

Modern ERP = workflow-driven system.

What’s missing:

• Visual workflow builder
• Approval matrix (by amount, role, department)
• Multi-step approvals
• Delegation rules
• Escalation rules
• SLA-based approvals
• Approval audit timeline
• Workflow simulation/testing

Impact:

• Manual approvals outside system
• Lack of control
• No accountability
• High fraud risk

## 10. Batch Recall System — Operational Hardening

Status: Exists (good), but not enterprise-grade

You already built recall logic — this is a big advantage.
But it still lacks regulatory and operational depth.

What’s missing:

• Role-based recall approval workflow
• Recall drill/test simulations
• Predefined communication templates
• Regulatory report formats per authority
• Recall effectiveness validation
• Evidence/document attachment system
• Immutable audit trail
• Risk-based recall dashboard
• SLA tracking (time to recall completion)

Impact:

• Weak regulatory compliance
• Inefficient recall execution
• Legal exposure in product safety incidents

## ## TIER 2 — High Importance

Missing or severely limited. Significant operational impact.

## 11. Real-Time Team Messaging / Collaboration Channels

Missing in: Entire system (only record-level chatter exists)

Your ERP has contextual comments, but not real-time communication.
Teams are forced to use WhatsApp → data fragmentation.

What’s missing:

• Channel-based messaging (Production, Sales, Finance, Ops)
• Direct messages between users
• @mentions with notifications
• Threaded conversations
• File/image sharing inside chat
• Message search
• Cross-module linking (message → order → batch → issue)
• Integration with Slack / Teams

Impact:

• Critical communication happens outside ERP
• No audit trail of decisions
• Slower reaction time in operations
• Knowledge scattered across WhatsApp groups

## 12. Email Integration (Two-Way Gmail / Outlook Sync)

Missing in: Entire system

Your ERP does not “see” email — which means it is blind to real customer communication.

What’s missing:

• Gmail / Outlook connection
• Incoming email auto-link to:

CRM lead
Customer
Supplier
Sales order / PO
• Send emails directly from ERP records
• Full email thread history inside records
• Email templates with merge fields
• Auto-create leads/tickets from inbound emails
Impact:

• CRM is incomplete
• Sales reps work outside system
• Lost communication history
• No single source of truth

## 13. Multi-Company / Multi-Branch Architecture

Missing in: Entire system

Right now:
👉 New company = new system
👉 That kills scalability immediately

What’s missing:

• Multiple legal entities in one system
• Separate books per company
• Inter-company transactions
• Consolidated financial reporting
• Company-specific Chart of Accounts
• User access by company

Impact:

• Impossible to scale group structure
• No centralized control
• Financial consolidation becomes manual nightmare

## 14. WhatsApp Business API Integration

Missing in: Entire system

In Kenya / Africa:
👉 WhatsApp = primary business interface

What’s missing:

• WhatsApp Business API integration (Twilio / Africa’s Talking / Infobip)
• Order confirmations via WhatsApp
• Invoice delivery via WhatsApp
• Payment reminders via WhatsApp
• Customer complaint intake via WhatsApp
• Van sales updates via WhatsApp bot
• Chat → ERP record linking

Impact:

• Massive adoption friction
• Distributors won’t use portal
• Lost communication tracking
• Missed automation opportunity

## 15. Quote / Estimation Module

Missing in: Entire system

Currently:
👉 Users jump straight to Sales Orders
👉 No commercial pipeline discipline

What’s missing:

• Quotation creation
• Expiry dates
• Versioning (v1, v2, v3)
• Convert quote → sales order
• Quote PDF generation
• Customer approval / e-sign
• Win/loss tracking
• Quote pipeline reporting

Impact:

• No traceability of negotiations
• Weak sales analytics
• Revenue forecasting unreliable

## 16. Helpdesk / Customer Complaint Ticketing

Missing in: Entire system

Critical for FMCG quality + distributor relations.

What’s missing:

• Ticket intake (phone, email, portal, WhatsApp)
• Ticket categorization (quality / delivery / billing)
• SLA tracking (response/resolution time)
• Batch/lot linking for quality issues
• Escalation rules
• Customer satisfaction tracking
• Ticket → CAPA integration

Impact:

• Complaints lost in inboxes
• No trend analysis
• No accountability
• Regulatory risk for quality complaints

## 17. Project Management (Gantt + Dependencies)

Status: Partial (Kanban only)

What’s missing:

• Project phases & milestones
• Task dependencies
• Gantt chart visualization
• Resource allocation (overload detection)
• Project P&L tracking
• Critical path analysis
• Timesheet integration

Impact:

• Projects managed in Excel
• Poor planning
• Delays and cost overruns

## 18. Retail / Shop POS (Traditional POS)

Status: Only Van Sales exists

What’s missing:

• Touchscreen POS interface
• Barcode scanner support
• Cash drawer integration
• Receipt printer integration
• End-of-day reconciliation
• Offline POS mode
• Loyalty integration

Impact:

• Cannot operate retail stores
• No trade fair / outlet sales capability

## 19. Electronic Signatures

Missing in: Entire system

What’s missing:

• Signature request workflow
• Secure signing links
• Digital signature capture
• Document auto-archiving
• Signature audit trail (IP, time, user)

Impact:

• Slow contract execution
• Paper-based processes
• Legal inefficiencies

## 20. Bank API Integration (Open Banking)

Status: Partial (CSV import only)

What’s missing:

• Direct bank API integration (Kenya banks)
• Daily auto transaction sync
• Transaction classification rules
• Auto reconciliation
• Real-time bank balance

Impact:

• Manual work
• Errors in reconciliation
• Delayed financial visibility

## 21. CRM Pipeline Depth (Advanced CRM Layer)

Status: Exists but shallow

What’s missing:

• Lead scoring
• Activity sequencing
• Customer 360 view
• Visit history tracking
• Territory management
• Sales funnel forecasting
• Credit risk scoring
• Communication integration (email/WhatsApp/VoIP)

Impact:

• Weak sales intelligence
• No predictive sales
• Inefficient sales team performance

## 22. Internal Collaboration Layer Expansion

Status: Partial

What’s missing:

• Internal threads linked to records
• Mentions across modules
• Document comments
• Cross-module activity timeline
• SLA timers

Impact:

• Teams disconnected
• Context switching between tools
• Slower execution

## 23. No-Code / Extensibility Layer

Missing in: Entire system

What’s missing:

• Visual form builder
• Custom object creation
• Workflow builder UI
• Dashboard builder
• Plugin/module generator
• Safe schema migration UI

Impact:

• Every change requires developers
• Slow iteration
• Poor scalability

## 24. Procurement System Depth

Status: Strong base, missing advanced logic

What’s missing:

• RFQ workflow
• Supplier quotation comparison
• Supplier scorecards
• Contract pricing enforcement
• Blanket purchase agreements
• Supplier delivery performance tracking
• Quality rejection analytics
• Auto reorder policies

Impact:

• Suboptimal purchasing decisions
• Higher costs
• Supplier risk unmanaged

## 25. Sales Order → Cash (Full Lifecycle)

Status: Partial

What’s missing:

• Full lifecycle automation:
Quote → SO → Delivery → Invoice → Payment
• Credit limit checks
• Return management (RMA)
• Payment allocation
• Customer statements
• Overdue collection workflow
• Margin tracking per order

Impact:

• Revenue leakage
• Weak financial control
• Poor customer management

## 26. Warehouse Execution (WMS Layer)

Status: Exists but not execution-grade

What’s missing:

• Scanner-first operations
• Putaway rules engine
• Pick/pack/ship workflow
• FEFO picking
• Pallet/license plate tracking
• Bin replenishment
• Mobile warehouse interface
• Label printing (Zebra/Honeywell)

Impact:

• Warehouse inefficiency
• Picking errors
• Inventory mismatch

## 27. Quality System Completion

Status: Strong but incomplete

What’s missing:

• Sampling plans (AQL)
• Certificate of Analysis generation
• Instrument calibration tracking
• Non-conformance workflow
• CAPA root cause analysis
• Batch release approval workflow
• Supplier quality scorecards

Impact:

• Weak quality control
• Compliance risk
• No continuous improvement loop

## ## TIER 3 — Medium Importance

Improves UX, reporting, visibility, and team productivity.

## 28. Knowledge Base / Internal Wiki

Missing in: Entire system

Right now, your company knowledge is floating in PDFs, emails, and people’s heads.

What’s missing:

• Wiki-style content editor (rich text)
• Hierarchical structure (Categories → Articles → Sections)
• Full-text search across all knowledge
• Linking knowledge to modules (e.g., SOP → Production Order)
• Version control for documents
• Access control per department
• Embedded media (images, videos, diagrams)

Impact:

• SOPs lost or outdated
• Training inefficiency
• Repeated mistakes
• Knowledge dependency on individuals

## 29. Employee Survey & Engagement Module

Missing in: Entire system

What’s missing:

• Pulse surveys (weekly/monthly)
• Anonymous employee feedback
• Annual engagement surveys
• Results dashboard (trend tracking)
• Action plan tracking based on results
• Exit interview surveys

Impact:

• No visibility into employee morale
• Retention issues invisible
• Management decisions blind to culture

## 30. VoIP / Call Center Integration

Missing in: Entire system

What’s missing:

• Click-to-call from CRM
• Incoming call pop-up with customer data
• Call recording and storage
• Call logs linked to CRM/customer
• Call duration + outcome tracking
• Call analytics (rep performance)

Impact:

• Sales calls not tracked
• No call history
• Weak sales performance analysis

## 31. Customer Loyalty Program

Missing in: Entire system

What’s missing:

• Points accumulation per purchase
• Tier-based loyalty (Silver/Gold/Platinum)
• Redemption system (discounts/free goods)
• Loyalty visibility in customer portal
• Loyalty campaign management

Impact:

• No retention strategy
• Lost repeat business
• Competitors win loyal distributors

## 32. Recurring Billing / Auto-Invoicing

Status: Partial (orders exist, invoices not automated)

What’s missing:

• Scheduled invoice generation
• Auto-email with payment link
• Payment tracking (paid vs ignored)
• Subscription-like billing logic
• Auto-renew contracts

Impact:

• Manual billing work
• Revenue leakage
• Missed invoices

## 33. Video Meeting Integration

Missing in: Entire system

What’s missing:

• Schedule meeting (Zoom/Teams/Google Meet) from ERP
• Auto-send meeting links
• Calendar sync
• Meeting notes linked to CRM/project
• Recording storage

Impact:

• Meetings disconnected from ERP
• No record of discussions
• Poor collaboration continuity

## 34. Customer / Product NPS Tracking

Missing in: Entire system

What’s missing:

• NPS surveys after delivery or visit
• Score tracking per customer
• Trend analysis over time
• Driver analysis (why score changed)
• Alerts for low scores

Impact:

• No customer satisfaction visibility
• Problems discovered too late
• Weak brand perception tracking

## 35. Native Mobile Apps (iOS / Android)

Missing in: Entire system (except Van Sales UI)

What’s missing:

• Native mobile app (not just web UI)
• Push notifications
• Approval workflows on mobile
• ESS (leave, payslip, expenses)
• Dashboard monitoring on phone
• Offline sync capability

Impact:

• Managers disconnected from system
• Slow approvals
• Poor adoption

## 36. API Developer Portal / GraphQL Layer

Status: Partial (REST exists)

What’s missing:

• GraphQL endpoint
• API key management
• Developer dashboard
• Rate limiting
• SDKs (JS, Python)
• Webhook subscription UI
• Postman collections

Impact:

• Hard to integrate externally
• Slower ecosystem growth
• Developers struggle to use system

## 37. Real-Time Notification Center

Status: Basic notifications exist

What’s missing:

• Notification bell UI
• Unread count
• Categorized alerts (finance, QC, stock, approvals)
• Priority levels (critical vs info)
• Email digest (daily/weekly)
• SMS / WhatsApp alerts for critical events
• Bulk mark-as-read

Impact:

• Important events missed
• Slow reaction to issues
• Users ignore system alerts

## 38. Reporting & BI Layer (Advanced Analytics)

Status: Exists but basic

What’s missing:

• Drag-and-drop report builder
• Saved filters/views
• Scheduled reports
• Export (Excel/PDF)
• Drill-down dashboards
• KPI cards
• Cross-module analytics
• Row-level security in reports

Impact:

• Decisions made outside ERP
• Excel dependency
• No real-time business visibility

## 39. Document Management System (DMS)

Status: Partial

What’s missing:

• Document version control
• Approval workflows
• Expiry tracking
• Tagging system
• Supplier compliance docs
• Product spec sheets
• Audit-ready document storage

Impact:

• Document chaos
• Compliance risk
• Manual tracking

## 40. Customer / Supplier Portal Expansion

Status: Exists but limited

What’s missing:

• Customer order tracking
• Distributor sell-through upload
• Supplier ASN (Advance Shipping Notice)
• Supplier invoice upload
• Quality certificate upload
• Self-service account statements
• Portal-level permissions

Impact:

• Low portal adoption
• Manual communication
• Supplier inefficiency

## 41. Audit Logs & Compliance Trail

Status: Basic logs exist

What’s missing:

• Immutable logs
• Before/after value tracking
• User/session/IP tracking
• Exportable audit reports
• Retention policies
• Tamper detection
• Searchable audit UI

Impact:

• Compliance risk
• Weak traceability
• Audit failure risk

## 42. Mobile-First Field Sales Expansion

Status: Good base (van sales), not complete

What’s missing:

• Offline mode
• GPS check-in/out
• Route planning UI
• Van inventory reconciliation
• M-Pesa payment confirmation
• Retail outlet photo capture
• Fraud detection enhancement
• End-of-day reconciliation

Impact:

• Field inefficiency
• Data gaps
• Fraud risk

## 43. Resource & Calendar Scheduling System

Status: Basic calendar exists

What’s missing:

• Machine scheduling
• Maintenance scheduling
• Production calendar
• Delivery planning
• Staff shift scheduling
• Drag-drop rescheduling
• Conflict detection

Impact:

• Scheduling conflicts
• Inefficient resource use
• Delays

## 44. Integration Marketplace / Connector Hub

Status: Basic integrations exist

What’s missing:

• Connector registry
• Prebuilt integrations
• API key management
• Webhook retry system
• Integration logs
• External system connectors (accounting, M-Pesa, EDI, WhatsApp)

Impact:

• Hard integrations
• Slow expansion
• Weak ecosystem

## ## TIER 4 — FMCG-Specific & Regulatory

Not in most general ERPs. Critical for FMCG manufacturing reality.

## 45. Returnable Packaging / Container Management

Missing in: Entire system

In FMCG, you don’t just ship products…
👉 You ship assets (crates, bottles, drums, pallets)

What’s missing:

• Returnable container register per customer
• Issue containers on delivery
• Track returns on next delivery
• Deposit management (charge/refund)
• Overdue return alerts
• Container reconciliation per distributor
• Write-off workflow (lost/damaged containers)
• Container lifecycle tracking

Impact:

• Hidden financial losses
• Inventory distortion
• Disputes with distributors
• Asset leakage

## 46. New Product Development (NPD) Workflow

Missing in: Entire system (AI formulation exists but isolated)

You already have something powerful:
👉 AI Formulation Engine

But you don’t have the business workflow around it

What’s missing:

• Idea → Concept → Development → Pilot → Launch pipeline
• Stage-gate approvals (R&D → Marketing → Ops → Finance)
• Cost model per stage (estimated COGS)
• Regulatory checklist (allergen, label, compliance)
• BOM / recipe linkage
• Pilot batch tracking
• Launch readiness checklist
• First production order trigger

Impact:

• Product development chaos
• No traceability of decisions
• Slower innovation
• High risk of failed launches

## 47. Route Optimization for Van Sales (AI-Based)

Status: Partial (routes exist, no optimization engine)

Van sales is one of your strongest differentiators — but currently inefficient.

What’s missing:

• Route optimization algorithm (Clarke-Wright / nearest neighbor)
• Traffic-aware routing (Google Maps / HERE API)
• Dynamic re-routing (customer unavailable)
• Visit prioritization (revenue-based ranking)
• Minimum call-time enforcement
• Route profitability analytics

Impact:

• Lost sales opportunities
• Higher fuel costs
• Inefficient field operations
• Poor coverage of high-value customers

## 48. Consumer Complaint Management (Batch-Linked)

Missing in: Entire system

This is different from distributor complaints.
This is end-consumer safety level.

What’s missing:

• Consumer complaint intake (phone/email/social media)
• Complaint linked to product batch (via lot number)
• Severity classification:

Safety
Quality
Label issue
• Auto-trigger recall if severity HIGH
• Investigation workflow
• Regulatory reporting
• Response tracking (acknowledged → resolved → compensated)
Impact:

• Safety risks unmanaged
• No recall triggers
• Regulatory violations
• Brand damage

## 49. Regulatory Certificate Tracking (Kenya + Export)

Missing in: Entire system

FMCG is heavily regulated.
Products can’t exist without valid certifications.

What’s missing:

• Certificate register (KEBS, KEPHIS, PPB, NEMA)
• Expiry tracking per product and plant
• Renewal workflow (alerts 30/60/90 days before expiry)
• Supplier certifications:

FSCC
HALAL
KOSHER
ISO
• Audit history per certificate
• Document storage + version control
• Export compliance tracking per country
Impact:

• Product recall risk
• Legal penalties
• Export rejection
• Production stoppage

## 50. Dynamic / AI Pricing Engine

Status: Partial (static price lists exist)

You already control:
👉 Costs
👉 Promotions
👉 Sales

Now you need intelligence

What’s missing:

• Competitor price tracking
• Demand-based pricing logic
• Price elasticity modeling
• AI price recommendations
• Channel-specific pricing (modern trade / distributor / export)
• Margin protection automation

Impact:

• Underpricing or overpricing
• Lost margin
• Weak competitiveness
• Manual pricing decisions

## 51. Brand Asset / Label Design Management (DAM)

Missing in: Entire system

In FMCG:
👉 Label = legal document

What’s missing:

• Digital Asset Management system
• Label/artwork version control
• Approval workflow:
R&D → Regulatory → Marketing → Print
• Link label version to BOM version
• Alert if BOM changes require label update
• Label compliance checklist

Impact:

• Wrong labels printed
• Regulatory risk
• Expensive reprints
• Brand inconsistency

## 52. Market Intelligence / Competitor Tracking

Status: Partial (internal secondary sales exists)

What’s missing:

• Competitor price monitoring
• Market share tracking
• Shelf share tracking (field data)
• Promotion effectiveness vs market
• External data integration (Nielsen/IRI)

Impact:

• Blind pricing decisions
• No market positioning insight
• Weak strategy

## 53. Co-Packing / Toll Manufacturing (Advanced)

Status: Partial (basic subcontracting exists)

What’s missing:

• Tool/mould register (customer-owned assets)
• Tool depreciation tracking
• Production limits per tool
• Tool lifecycle tracking
• Cost amortization per unit
• Multi-party manufacturing contracts

Impact:

• Asset ownership disputes
• Cost misallocation
• Lack of control over subcontractors

## 54. HACCP System Expansion

Status: Strong foundation already exists

This is one of your biggest strengths already.

What’s missing:

• HACCP plan PDF generation
• CCP trend analytics
• BRC / FSSC 22000 audit checklist
• HALAL / KOSHER compliance tracking
• Mock audit workflows
• Supplier food safety approval tracking

Impact:

• Missed certification opportunities
• Audit inefficiency
• Incomplete compliance

## 55. Allergen & Nutrition Management

Status: Partial

What’s missing:

• Allergen matrix (cross-product mapping)
• Cross-contamination risk rules
• Cleaning validation logs
• Nutrition facts calculation
• Ingredient declaration automation
• Label compliance validation

Impact:

• Allergen risk
• Regulatory violations
• Consumer safety issues

## 56. GS1 Barcode & Labeling System (Advanced)

Status: Exists but basic

What’s missing:

• GS1-128 barcode generation
• GTIN master data
• Expiry/lot encoded labels
• Pallet SSCC labeling
• Label template designer
• Printer integration
• Scan validation during dispatch

Impact:

• Weak traceability
• Distribution inefficiency
• Retail integration problems

## 57. Shelf-Life / FEFO Control Expansion

Status: Exists but not complete

What’s missing:

• FEFO reservation system
• Near-expiry alerts
• Shelf-life rules per customer
• Expiry quarantine
• Shelf-life extension approval
• Write-off workflow

Impact:

• Expired goods shipped
• Losses
• Customer complaints

## 58. Trade Promotion Management (TPM) Expansion

Status: Strong base exists

What’s missing:

• Buy X get Y
• Discount slabs
• Free goods logic
• Distributor rebate accruals
• Promotion budget control
• Promotion ROI tracking
• Claim settlement automation

Impact:

• Promotion inefficiency
• Budget overspend
• No ROI visibility

## 59. Secondary Sales / Distributor Sell-Through Expansion

Status: Exists but incomplete

What’s missing:

• Distributor stock uploads
• Retail-level sales tracking
• Territory performance analytics
• Distributor aging analysis
• SKU velocity heatmaps
• Scheme effectiveness tracking

Impact:

• No visibility beyond distributor
• Weak demand forecasting
• Poor channel control

## 60. Kenya Localization (Advanced Layer)

Status: Strong base exists (payroll, M-Pesa)

What’s missing:

• Full eTIMS integration
• VAT automation
• Withholding tax logic
• SHIF/NHIF/NSSF full compliance
• M-Pesa reconciliation automation
• Regional route/territory mapping

Impact:

• Partial localization
• Compliance gaps
• Operational inefficiency

## ## TIER 5 — Advanced / Future Roadmap

Cutting-edge capabilities. Build after operational stability (Tier 1–3) is solid.

## 61. IoT / Real-Time Machine Data Streaming

Status: Partial foundation (utilities exist: electricity, steam, water, etc.)

Right now you collect data… but not in real-time intelligence form.

What’s missing:

• MQTT broker integration for live sensor data
• OPC-UA connector for PLC/SCADA systems
• Real-time streaming dashboards (WebSocket-based)
• Sensor data normalization layer
• Threshold-based auto-alert system
• Machine state detection (running / idle / down)
• Event-based triggers (not polling)

Impact:

• Delayed reaction to issues
• Hidden machine inefficiencies
• No real-time factory visibility

## 62. ML-Based Demand Forecasting Engine

Status: Basic (moving average only)

What’s missing:

• Time-series ML models (ARIMA / Prophet / LSTM)
• Seasonality detection
• Promotion uplift modeling
• Cross-SKU demand correlation
• Forecast accuracy tracking (MAPE, RMSE)
• Continuous model retraining
• Forecast override with audit trail

Impact:

• Poor planning accuracy
• Overstock / stockouts
• Weak supply chain optimization

## 63. Blockchain-Based Traceability (Export-Grade)

Missing in: Entire system

What’s missing:

• Immutable lot traceability ledger
• QR code per product → public trace view
• Supplier → factory → distributor chain visibility
• Third-party verification access
• Smart contract-based traceability attestations

Impact:

• Limited export trust
• Cannot enter premium regulated markets
• No differentiation for high-value products

## 64. Carbon Footprint Per Product (Granular ESG)

Status: Partial (company-level ESG exists)

What’s missing:

• Scope 3 emissions (raw materials)
• Energy usage per production batch
• Water consumption per SKU
• Packaging carbon impact
• Carbon per finished product unit
• Carbon labeling on product spec sheets

Impact:

• Weak ESG positioning
• Missed export opportunities
• No sustainability differentiation

## 65. AI-Powered Receipt OCR (Expenses Automation)

Missing in: Entire system

What’s missing:

• Mobile receipt scanning
• AI extraction:

Date
Amount
Vendor
Category
• Confidence scoring
• Auto-fill expense claims
• Duplicate detection
• Receipt storage linked to expense
Impact:

• Manual data entry
• Errors in expenses
• Slow reimbursement process

## 66. Natural Language ERP Control (AI Actions)

Status: Basic AI chat exists

This is where your ERP becomes a command center.

What’s missing:

• Action-based AI commands:

“Approve all POs under 50K”
“Run MRP for next 30 days”
“Send dunning emails to overdue customers”
• Confirmation layer before execution
• Permission-aware AI actions
• Audit logs of AI actions
• Multi-step workflow automation via natural language
Impact:

• Slower operations
• Underutilized AI
• Missed productivity leap

## 67. AI Agent Governance Framework

Missing in: Entire system

You already have AI modules…
But not AI discipline

What’s missing:

• Prompt template registry
• Tool access control per AI agent
• Human-in-the-loop approval system
• AI decision audit logs
• Evaluation/testing framework
• Hallucination guardrails
• RAG (retrieval from internal data)
• Cost tracking per AI action

Impact:

• Uncontrolled AI behavior
• Security risks
• Inconsistent outputs
• Lack of trust in AI

## 68. Predictive Maintenance (ML + IoT Fusion)

Status: Maintenance exists, but reactive

What’s missing:

• Vibration anomaly detection
• Temperature trend analysis
• Failure probability prediction
• Remaining useful life (RUL) estimation
• Spare parts prediction
• Maintenance optimization (cost vs risk)
• Auto-trigger maintenance orders

Impact:

• Unexpected breakdowns
• Higher maintenance costs
• Production downtime

## 69. ESG Intelligence & Sustainability Optimization

Status: ESG tracking exists

What’s missing:

• Carbon factor database
• Energy per SKU analytics
• Water usage per batch
• Wastewater compliance tracking
• Solar offset calculation
• ESG audit reporting
• Supplier sustainability scoring

Impact:

• Weak ESG reporting
• No sustainability optimization
• Missed funding / partnership opportunities

## 70. Plugin / App Marketplace Architecture

Missing in: Entire system

What’s missing:

• Modular plugin system
• Install/uninstall modules
• Dependency management
• Version control per module
• Marketplace infrastructure
• Tenant-specific module configs

Impact:

• System not extensible
• Slow innovation
• Developer bottleneck
---

# STARTING INSTRUCTION

When beginning from scratch:
Start with Phase 1, Gap 1: Full Double-Entry General Ledger.

When continuing:
Read TASKS2.md and continue from the next incomplete gap.