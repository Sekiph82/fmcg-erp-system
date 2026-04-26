# TASKS — FMCG ERP (Kenya) · Production Module

## Current Phase
Phase 33 — Moto Sales Extension ✅ COMPLETED

---

## Phase 33 — Moto Sales / Van Sales Extension (M-Pesa + Fraud + Performance) ✅

Built as an extension to Phase 29 Van Sales module.

- [x] Extended `backend/app/models/van_sales.py` with 3 new model classes:
  - `VanMpesaPayment` — STK Push lifecycle (merchant_request_id, checkout_request_id, receipt, status, callback time, raw_callback)
  - `VanFraudAlert` — fraud type, risk_score (0–100), severity, status, reviewed_by, resolution
  - `VanRiderPerformance` — daily score per driver: visits, completion%, collection%, cash variance, fraud flags, composite score (0–100)
- [x] `backend/app/services/moto_sales_service.py`:
  - `initiate_stk_push()` — creates PENDING record (production: calls Daraja API)
  - `handle_stk_callback()` — updates status, auto-creates van_payment on SUCCESS, updates txn payment_status
  - `run_fraud_scan()` — 3 detectors: abnormal discounts (>20% avg), repeated returns (>3 in 7d), payment mismatch (unpaid >72h)
  - `_severity_from_score()` — risk score → LOW/MEDIUM/HIGH/CRITICAL
  - `review_fraud_alert()` — set status + resolution + reviewer
  - `compute_rider_performance()` — upserts daily record with composite score (route 30%, collection 25%, cash accuracy 15%, sales volume 20%, fraud-free 10%)
  - `leaderboard()` — 7-day aggregation ranked by avg score
- [x] `backend/app/api/v1/endpoints/moto_sales.py` — 10 routes at /api/v1/moto-sales/
- [x] `backend/alembic/versions/b8c9d0e1f2a3_moto_sales_extension.py` — migration (down_revision: a6b7c8d9e0f1), 3 new tables
- [x] `frontend/src/lib/moto_sales.ts` — types, API client, color helpers, scoreColor()
- [x] Frontend pages (3 new screens under /dashboard/van-sales/):
  - Fraud Alerts — scan button, KPI strip, severity+status filters, inline review panel (Dismiss/Confirm/Escalate)
  - Rider Performance — leaderboard tab (podium + full table), daily records tab, compute form
  - M-Pesa Payments — STK Push initiation form, status filter, payment table with receipt tracking
- [x] Nav: "Van Sales" section extended with 3 new links (Fraud Alerts, Rider Performance, M-Pesa Payments)

## Next: Prompt 31 — Sales Commission Tracking

---

## Phase 30 — Contract Management ✅ COMPLETED

---

## Phase 30 — Contract Management ✅

- [x] `backend/app/models/contracts.py` — 12 enums + 7 models (UUID PKs): Contract, ContractTerm, ContractRebate, ContractPerformance, ContractVersion, ContractApproval, CTAIRecommendation
- [x] `backend/app/schemas/contracts.py` — Pydantic v2 schemas (header CRUD, terms, rebates, performance upsert, approval, version, AI rec)
- [x] `backend/app/services/contracts_service.py`:
  - Full lifecycle: DRAFT → UNDER_REVIEW → APPROVED → ACTIVE → EXPIRED/TERMINATED/ARCHIVED
  - Submit/approve/reject/activate/terminate/archive transitions
  - Terms and rebate CRUD
  - Performance upsert with auto achievement_pct and rebate_earned calculation from rebate tiers
  - Version snapshot on every meaningful change
  - Approval log for full audit trail
  - Contract lookup by party (for order integration)
  - Reports: summary KPIs, expiring contracts, performance aggregation
  - 3 AI agents: RISK_MONITOR (underperforming <60%), RENEWAL_ADVISOR (expiring in 45d), COMPLIANCE_MONITOR (large unsettled rebates)
- [x] `backend/app/api/v1/endpoints/contracts.py` — 22 routes at /api/v1/contracts/
- [x] `backend/alembic/versions/a6b7c8d9e0f1_contracts.py` — migration (down_revision: f5a6b7c8d9e0)
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/contracts.ts` — types, API client, color/label maps
- [x] Frontend pages (7 pages):
  - Dashboard (KPI strip, recent contracts, expiring alerts, AI alerts)
  - All Contracts list (status + party type filters)
  - Contract Detail (5 tabs: terms, rebates, performance, version history, approval log + lifecycle buttons)
  - New Contract form (type, party, dates, renewal settings)
  - Expiring Contracts (30/60/90d filter, days-left urgency coloring)
  - Reports (portfolio KPI, achievement chart, rebate league table)
  - AI Insights (3-agent panel, ack/dismiss)
- [x] Nav-config: "Contract Management" section with 6 links

## Next: Prompt 31 — Sales Commission Tracking

---

## Phase 29 — Van Sales / Mobile POS ✅ COMPLETED

---

## Phase 29 — Van Sales / Mobile POS ✅

- [x] `backend/app/models/van_sales.py` — 9 enums + 9 models (UUID PKs): Van, VanStock, VanStockMovement, VanVisit, VanSalesTxn, VanSalesTxnLine, VanPayment, VanReconciliation, VSAIRecommendation
- [x] `backend/app/schemas/van_sales.py` — Pydantic v2 schemas (van CRUD, stock load, visits, txns, payments, reconciliation, offline sync, AI)
- [x] `backend/app/services/van_sales_service.py`:
  - Van CRUD
  - Van stock load / deduct (on sale) / add (on return)
  - Visit lifecycle: create → check-in → check-out / missed
  - Transaction creation with line-level price/discount/tax calc
  - Payment collection with receipt no generation
  - Offline sync: dedup by offline_id, batch visits/txns/payments
  - Daily reconciliation: aggregate sales/returns/payments by van
  - Reports: van summary, route performance, driver performance
  - 3 AI agents: ROUTE_OPTIMIZER (missed visits), SALES_ASSISTANT (inactive vans), RISK_MONITOR (high discounts)
- [x] `backend/app/api/v1/endpoints/van_sales.py` — 25+ routes at /api/v1/van-sales/
- [x] `backend/alembic/versions/f5a6b7c8d9e0_van_sales.py` — migration (down_revision: e4f5a6b7c8d9)
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/van_sales.ts` — types, API client, color maps
- [x] Frontend pages (8 pages):
  - Dashboard (KPI cards, van list, AI alerts, quick nav)
  - Vans list + new van form
  - Van detail (4 tabs: transactions, stock, visits, reconciliation)
  - Mobile POS (sale/return flow → items → payment → receipt)
  - Route Execution (visit sequence, check-in/out, missed marking)
  - Van Stock (load stock panel, current stock table)
  - Reconciliation (daily close-out, approval workflow, history)
  - Reports (route performance bar chart, driver league table)
  - AI Insights (3-agent panel, ack/dismiss)
- [x] Nav-config: "Van Sales / Mobile POS" section with 8 links

## Next: Prompt 30 — Contract Management

---

## Phase 28 — Subscription / Recurring Orders ✅ COMPLETED

---

## Phase 28 — Subscription / Recurring Orders ✅

- [x] `backend/app/models/subscription.py` — 8 enums + 5 models (UUID PKs):
  - Enums: RecurrenceType, SubscriptionStatus, GenerationMode, PriceSource, GenerationStatus, PauseSkipAction, SubAIAgentType, SubAIRecStatus
  - Models: SubscriptionTemplate, SubscriptionLine, SubscriptionGenerationLog, SubscriptionPauseSkip, SubAIRecommendation
- [x] `backend/app/schemas/subscription.py` — Pydantic v2 schemas (template CRUD, generation log, pause/skip, AI rec, upcoming demand)
- [x] `backend/app/services/subscription_service.py`:
  - Recurrence engine: WEEKLY, BIWEEKLY, MONTHLY_DATE, MONTHLY_DAY, CUSTOM_DAYS, ROUTE_BASED
  - Pre-generation validation (customer active, credit hold, item active, duplicate guard, pause/skip check)
  - Sales order generation with generation mode (DRAFT_ONLY / APPROVAL_REQUIRED / AUTO_CONFIRM)
  - next_generation_date calculation after each run
  - Scheduler: run_scheduled_generation() — processes all due active templates
  - Pause / skip / resume / cancel workflow
  - Upcoming demand feed for MRP/planning
  - 3 AI agents: DEMAND_PREDICTOR, RISK_MONITOR, OPTIMIZATION_ASSISTANT
  - Reports: template health, generation by status, failed generations
- [x] `backend/app/api/v1/endpoints/subscription.py` — 20 routes at /api/v1/recurring-orders/
- [x] `backend/alembic/versions/e4f5a6b7c8d9_subscription_recurring_orders.py` — migration (down_revision: d3e4f5a6b7c8)
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/subscription.ts` — TypeScript types, API client, color/label maps
- [x] Frontend pages (6 screens):
  - Dashboard (stats, recent templates, generation stats, AI alerts)
  - Template List (filterable by status)
  - Template Detail (4 sections: info grid, lines tab, generation log tab, pause history tab)
  - New Template form (recurrence settings, generation mode, lines)
  - Generation Calendar (8-week calendar + next-date list)
  - Upcoming Demand (grouped by date, MRP feed)
  - Reports (health KPIs, bar chart, failed log)
  - AI Insights (3-agent descriptions, rec acknowledge/dismiss)
- [x] Nav-config: "Recurring Orders" section with 6 links

## Next: Prompt 29 — Van Sales / Mobile POS

---

## Phase 24 — Customer / Distributor Portal ✅ COMPLETED

---

## Phase 24 — Customer / Distributor Portal ✅

- [x] **Import fixes** — corrected `from app.database import` → `from app.db.base import` and `from app.db.session import` in `tpm.py`, `crm.py`, `tpm endpoint`, `crm_pipeline endpoint`
- [x] `backend/app/models/portal.py` — 12 enums + 7 models:
  - Enums: PortalAccountType, PortalAccountStatus, PortalUserRole, PortalActivityType, PortalClaimType, PortalClaimStatus, PortalOrderMode, PortalDraftOrderStatus, PortalAIAgentType, PortalAIRecStatus
  - Models: PortalAccount, PortalUser, PortalActivityLog, PortalClaim, PortalDraftOrder, PortalDraftOrderLine, PortalAIRecommendation
- [x] `backend/app/schemas/portal.py` — full Pydantic v2 schemas (account CRUD, user invite, login/activate, claims, draft orders, dashboard, AI rec)
- [x] `backend/app/services/portal_service.py`:
  - Account CRUD (create, update, activate, suspend) with auto-code PA-XXXXX
  - User invite (invitation token, 7-day expiry, SHA-256 password hashing)
  - activate_user_with_password (token verification + password set)
  - login (email/password auth, status check, activity log)
  - Scoped queries — orders/shipments/invoices/payments filtered by linked_customer_id or linked_distributor_id
  - get_portal_dashboard (outstanding balance, aging 0-30/31-60/61-90/90+, open orders, recent invoices, open claims)
  - get_portal_statement (period-filtered invoice + payment reconciliation)
  - create_claim / review_claim (claim_no CLM-XXXXX, status workflow)
  - create_draft_order / submit_draft_order / review_draft_order (draft_no DRF-XXXXX, line total calc)
  - reorder_from_order (clones SO lines into a draft order for the same account)
  - Activity logging for all key actions
  - AI Agent 1: Support Assistant (accounts with ≥3 open claims)
  - AI Agent 2: Friction Monitor (5+ logins but no orders in 30 days)
  - AI Agent 3: Commercial Opportunity (last order > 45 days ago)
  - portal_adoption_report (total/active accounts, users, 30-day logins/orders/claims)
- [x] `backend/app/api/v1/endpoints/portal.py` — 30+ routes at /api/v1/portal/
  - POST /portal/auth/login + /portal/auth/activate
  - GET/POST /portal/accounts + GET/PATCH/POST activate/suspend per account
  - GET/POST /portal/accounts/{id}/users/invite, POST /portal/users/{id}/deactivate
  - GET /portal/accounts/{id}/dashboard | orders | orders/{oid} | shipments | invoices | payments | statement
  - GET/POST /portal/accounts/{id}/claims + PATCH /portal/claims/{id}/review
  - GET/POST /portal/accounts/{id}/draft-orders + POST submit + PATCH /portal/draft-orders/{id}/review
  - POST /portal/accounts/{id}/reorder/{source_order_id}
  - GET /portal/accounts/{id}/activity
  - GET /portal/reports/adoption
  - POST /portal/ai/run-support-assistant | run-friction-monitor | run-commercial-opportunity
  - GET/PATCH /portal/ai/recommendations
- [x] `backend/alembic/versions/a0b1c2d3e4f5_portal.py` — migration (down_revision: f9a0b1c2d3e4), 7 tables
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/portal.ts` — TypeScript types, API client, label/color maps, fmtCurrency
- [x] Frontend pages (9 screens):
  - Portal Admin Dashboard (adoption KPIs, account list with activate/suspend, quick links)
  - Portal Accounts List (card view with type/status filters, manage + portal view links)
  - Portal Account Detail (6 tabs: overview/users/orders/invoices/claims/drafts + invite modal + aging chart)
  - Portal Customer View (clean B2B portal layout, 8 tabs: dashboard/orders/shipments/invoices/payments/statement/claims/new order)
  - Draft Order Review Queue (submitted drafts across all accounts, approve/reject)
  - Claims Review (claim list + side review panel with resolve/reject/under-review actions)
  - Portal Users (all users across accounts, role/status filters, deactivate)
  - Activity Log (per-account activity timeline)
  - Reports (adoption KPIs, activation rate bar, 30-day activity summary)
  - AI Agents (3 agents + recommendation ack workflow)
- [x] Sidebar: "Customer / Distributor Portal" section added (8 items)

## Phase 25 — Supplier Portal ✅ COMPLETED

- [x] `backend/app/models/supplier_portal.py` — 9 enums + 7 models:
  - Enums: SPAccountStatus, SPUserRole, SPActivityType, SPPOResponseStatus, SPETAStatus, SPDocUploadType, SPDocReviewStatus, SPPaymentVisibility, SPAIAgentType, SPAIRecStatus
  - Models: SPAccount, SPUser, SPPermissionProfile, SPActivityLog, SPDocument, SPPOResponse, SPETALog, SPAIRecommendation
- [x] `backend/app/schemas/supplier_portal.py` — full Pydantic v2 schemas
- [x] `backend/app/services/supplier_portal_service.py`:
  - Account CRUD (create, update, list, get by supplier)
  - User invite + deactivate + password reset
  - Login with activity logging
  - Scoped PO list + detail (filtered by supplier_id)
  - PO acknowledgment / response workflow (accept/reject/partial/revised ETA)
  - ETA proposal + revision history + buyer review
  - Document upload (all 13 types) + review workflow
  - Expiring document detection (configurable days)
  - Payment status visibility (policy-gated)
  - Portal activity log
  - Dashboard (open POs, pending ACK, doc uploads, expiring certs, recent activity, AI alerts)
  - AI Agent 1: Collaboration Monitor (overdue PO acknowledgments)
  - AI Agent 2: Friction Assistant (low portal adoption)
  - AI Agent 3: Risk Signal (expiring compliance docs)
  - Reports: adoption, PO ack time, ETA revisions, non-responding suppliers
- [x] `backend/app/api/v1/endpoints/supplier_portal.py` — 25+ routes at /api/v1/supplier-portal/
- [x] `backend/alembic/versions/b1c2d3e4f5a6_supplier_portal.py` — migration (down_revision: a0b1c2d3e4f5), 7 tables
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/supplier_portal.ts` — TypeScript types, API client, color/label maps
- [x] Frontend pages (10 screens):
  - Portal Admin (account list + onboarding modal, status KPIs)
  - Account Detail (dashboard KPIs + quick links + AI alerts + recent activity)
  - Purchase Orders per account (list + PO acknowledge/reject/propose-ETA modal)
  - ETA Management (history view + propose modal + buyer review modal)
  - Document Center (upload all 13 doc types + review workflow + expiry alert banner)
  - Invoice Submission (upload invoices with metadata + PO link)
  - Payment Status (invoice payment tracking, policy-gated)
  - Portal Users (invite + deactivate + role management)
  - Activity Log (full audit trail per account)
  - Reports (4 reports: adoption, ack time, ETA revisions, non-responding)
  - AI Agents (3 agents + recommendation ack/dismiss/action workflow)
- [x] Sidebar: "Supplier Portal" section added (10 items)

## Phase 26 — Dunning / Overdue Collection ✅ COMPLETED

- [x] `backend/app/models/dunning.py` — 8 enums + 9 models: DunningPolicy, DunningLevel, DunningTemplate, DunningCase, DunningCaseInvoice, DunningActionLog, DunningPTP, DunningException, DunningAIRecommendation
- [x] `backend/app/schemas/dunning.py` — full Pydantic v2 schemas
- [x] `backend/app/services/dunning_service.py`:
  - Policy CRUD + priority resolution hierarchy (customer → segment → channel → country → default)
  - Level CRUD + level resolution from days_overdue
  - Template CRUD + merge-field rendering
  - Overdue detection engine (scans invoices past due_date, computes balance)
  - Case creation/update (one open case per customer, auto credit hold from policy thresholds)
  - PO level determination, priority scoring (amount + age + broken PTPs)
  - PO Acknowledgment / reminder / manual note / dispute flagging
  - PTP create/update/broken-check workflow
  - Exception CRUD
  - Credit hold apply + release
  - 4 reports: dashboard, aging, effectiveness, workqueue, PTP fulfillment
  - AI Agent 1: Collection Prioritization (unassigned high-priority cases)
  - AI Agent 2: Payment Risk Monitor (repeated broken PTPs)
  - AI Agent 3: Effectiveness Assistant (stale cases 14+ days without action)
- [x] `backend/app/api/v1/endpoints/dunning.py` — 30+ routes at /api/v1/dunning/
- [x] `backend/alembic/versions/c2d3e4f5a6b7_dunning.py` — migration (down_revision: b1c2d3e4f5a6), 9 tables
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/dunning.ts` — TypeScript types, API client, color/label maps
- [x] Frontend pages (9 screens):
  - Dashboard (KPI cards, priority case list, quick links, run detection button)
  - Aging Report (customer-level aging buckets: current/1-7/8-14/15-30/31-60/61-90/90+, totals row)
  - Case List (filterable by status + credit hold, priority bar)
  - Case Detail (5 tabs: overview, invoices, timeline, PTPs, exceptions + send reminder + add note + PTP record + credit hold)
  - Policies (policy list + level editor with drag/visual step view + add level modal)
  - Collector Workqueue (priority-sorted queue, check broken PTPs)
  - Credit Hold Management (all holds, release flow)
  - Templates (create message templates with merge fields + preview)
  - Reports (KPIs, PTP fulfillment bar, effectiveness table)
  - AI Agents (3 agents, ack/action/dismiss workflow)
- [x] Sidebar: "Dunning & Collections" section added (9 links)

## Phase 27 — Price List & Discount Enhancement ✅ COMPLETED

- [x] `backend/app/models/price_list.py` — 9 enums + 8 models: PLHeader, PLLine, PLTier, PLAssignment, PLDiscountRule, PLApproval, PLChangeHistory, PLAIRecommendation
- [x] `backend/app/schemas/price_list.py` — full Pydantic v2 schemas
- [x] `backend/app/services/price_list_service.py`:
  - Header CRUD with draft/review/approve/activate/archive lifecycle
  - PLLine CRUD (locked when active — must clone for edits)
  - PLTier CRUD (quantity break pricing: unit price override, discount%, fixed discount)
  - PLAssignment CRUD (customer / distributor / channel / region / country / segment)
  - PLDiscountRule CRUD (scope, type, max%, approval gate, margin floor, reason requirement)
  - Approval workflow (submit → review → approve/reject → activate)
  - Price resolution engine (7-level hierarchy: customer-specific → assignment → promo → channel/region → default/standard)
  - Margin check engine (BELOW_COST=blocked, <10%=approval, <20%=warning, ≥20%=OK)
  - Bulk CSV import (validates product codes, upserts lines, logs change history)
  - Template CSV generator
  - Change history log (every CRUD action logged)
  - 4 reports: dashboard KPIs, expiring lists, below-margin lines, version comparison diff
  - AI Agent 1: Pricing Risk Monitor (expired active lists, below-margin lines)
  - AI Agent 2: Price Optimization (overlapping list consolidation)
  - AI Agent 3: Discount Abuse Detector (no-margin-guard customer lists)
- [x] `backend/app/api/v1/endpoints/price_list.py` — 30+ routes at /api/v1/price-lists/
- [x] `backend/alembic/versions/d3e4f5a6b7c8_price_list.py` — migration (down_revision: c2d3e4f5a6b7), 8 tables
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/price_list.ts` — TypeScript types, API client, color/label maps
- [x] Frontend pages (8 screens):
  - Dashboard (KPI cards, expiring alert banner, create price list modal, filterable table)
  - Price List Detail (5 tabs: lines, tiers, assignments, history, approvals + workflow buttons)
  - Approval Queue (review/approve/reject with reviewer name + notes)
  - Discount Rules (create rules with scope/type/approval/margin guards)
  - Margin Guardrails (live margin check + BELOW_COST/BELOW_MIN/WARNING/OK logic + below-margin report)
  - Version Compare (diff two price lists by price delta and delta%)
  - Bulk Import (CSV paste + download template + error reporting)
  - Reports (dashboard KPIs, expiring 60d, below-margin)
  - AI Agents (3 agents + ack/action/dismiss workflow)
- [x] Sidebar: "Price Lists & Discounts" section added (8 links)

## Next Immediate Task
Phase 28 — Subscription / Recurring Orders

## Blockers
None

---

## Phase 23 — Advanced CRM Pipeline ✅ COMPLETED

---

## Phase 23 — Advanced CRM Pipeline ✅

- [x] `backend/app/models/crm.py` — 12 enums + 7 models:
  - Enums: CRMRecordType, CRMAccountType, CRMSourceType, CRMStageType, CRMTemperature, CRMStatus, CRMActivityType, CRMActivityResult, CRMLossReason, CRMWinReason, CRMAIAgentType, CRMAIRecStatus
  - Models: CRMPipelineStage, CRMRecord, CRMInterestLine, CRMActivity, CRMCompetitor, CRMWinLoss, CRMAIRecommendation
- [x] `backend/app/schemas/crm.py` — full Pydantic v2 schemas (stage CRUD, record CRUD, qualify, convert, close-won/lost, forecast rows, win-loss report, AI rec ack)
- [x] `backend/app/services/crm_pipeline_service.py`:
  - Stage CRUD + seed_default_stages (10 default stages)
  - Record CRUD (leads + opportunities) with auto-code generation (LD-XXXXX, OPP-XXXXX)
  - Auto-probability from stage assignment
  - qualify_record (6-point fit checklist, score bonus)
  - convert_to_opportunity (type change, code assignment, audit trail)
  - close_won / close_lost (status update + win/loss record creation)
  - put_on_hold / reopen
  - add_interest_line / delete_interest_line
  - Activity CRUD + complete_activity
  - Competitor intelligence add
  - check_duplicates (company/email/phone dedup)
  - update_lead_score (source, activity, qualification, revenue, next action, interest lines)
  - Dashboard aggregation (12 KPIs + stage distribution + top reps)
  - Forecast (monthly bucketing, expected + weighted revenue, N months ahead)
  - Pipeline report (by stage with weighted values)
  - Win/Loss analytics (by reason, by win reason, competitor causes)
  - AI Agent 1: Lead Prioritization (stale leads 7+ days, closing soon within 30 days)
  - AI Agent 2: Pipeline Risk Monitor (overdue close dates, stage bottlenecks >5 records)
  - AI Agent 3: Win/Loss Insight (recurring loss reasons ≥3, competitor patterns ≥2)
- [x] `backend/app/api/v1/endpoints/crm_pipeline.py` — 25+ routes at /api/v1/crm/
  - GET/POST /crm/stages + PATCH + POST seed-defaults
  - GET/POST /crm/leads + /crm/opportunities + /crm/records
  - GET/PATCH /crm/records/{id}
  - POST /crm/records/{id}/qualify | convert-to-opportunity | close-won | close-lost | on-hold | reopen | update-score
  - POST /crm/records/{id}/interest-lines + DELETE /crm/interest-lines/{id}
  - GET/POST /crm/activities + POST /crm/activities/{id}/complete
  - POST /crm/competitors
  - GET /crm/check-duplicates
  - GET /crm/dashboard | /crm/forecast | /crm/reports/pipeline | /crm/reports/win-loss
  - POST /crm/ai/run-lead-prioritization | run-pipeline-risk | run-win-loss-insight
  - GET/PATCH /crm/ai/recommendations
- [x] `backend/alembic/versions/f9a0b1c2d3e4_crm_pipeline.py` — migration (down_revision: e7f8a9b0c1d2)
  - 7 tables: crm_pipeline_stages, crm_records, crm_interest_lines, crm_activities, crm_competitors, crm_win_loss, crm_ai_recommendations
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/crm_pipeline.ts` — TypeScript types, API client, label maps, color maps, fmtCurrency
- [x] Frontend pages (11 screens):
  - CRM Dashboard (KPI cards, pipeline value, weighted pipeline, stage distribution, top reps, quick links)
  - Lead List (filters by status/temperature, create modal, score bar, temperature badge)
  - Opportunity List (pipeline/weighted summary, filters, create modal)
  - Pipeline Kanban Board (drag-drop stage movement, cards with revenue/probability/close date)
  - Record Detail (6 tabs: overview, activities, products, competitors, close deal + convert modal)
  - Activity Timeline (filters: overdue/type/status, complete/reschedule actions, linked record)
  - Forecast Dashboard (monthly bar chart, expected vs weighted, pipeline by stage table)
  - Win/Loss Analysis (win rate bar, loss reasons, win reasons, competitor causes)
  - Lead Qualification Panel (6-point BANT+PG checklist, score meter, qualify/disqualify)
  - Overdue Follow-Up Queue (urgency-colored cards, complete/reschedule actions)
  - Stage Configuration (CRUD, seed defaults, activate/deactivate)
  - AI Agents (3 agents: Lead Prioritization + Pipeline Risk + Win/Loss Insight, ack workflow)
- [x] Sidebar: "CRM Pipeline" section added (11 items)

## Next Immediate Task
Phase 24 — Customer / Distributor Portal

## Blockers
None

---

## Phase 22 — Trade Promotion Management Enhancement ✅

- [x] `backend/app/models/tpm.py` — 11 enums + 8 models:
  - Enums: TPMPeriodType, TPMPlanStatus, TPMPromotionType, TPMObjectiveType, TPMPromotionStatus, TPMBudgetType, TPMBaselineMethod, TPMClaimantType, TPMClaimType, TPMClaimStatus, TPMAIAgentType, TPMAIRecStatus
  - Models: TPMPlan, TPMPromotion, TPMBudgetLine, TPMExpectedPerf, TPMActualPerf, TPMClaim, TPMClaimLine, TPMAIRecommendation
- [x] `backend/app/schemas/tpm.py` — full Pydantic v2 schemas with `from __future__ import annotations` + `model_rebuild()`
- [x] `backend/app/services/tpm_service.py`:
  - Plan CRUD + approve + status transitions
  - Promotion CRUD + approve + scheme linkage
  - Budget line management with remaining-budget tracking
  - Expected performance upsert (baseline_method, target volume, expected ROI)
  - Actual performance upsert with auto-computed uplift_pct and roi_pct
  - Claim CRUD + auto claim_no generation + review workflow (approve/reject) + settlement (partial and full)
  - Dashboard aggregations (active plans, promotions, open claims, budget utilization)
  - Budget vs Actual report (per promotion, with variance and utilization_pct)
  - ROI report (expected vs actual ROI + uplift, sorted by actual ROI)
  - Claim aging report (open claims ordered by age in days)
  - AI Agent 1: ROI Analyst (completed promotions with <50% expected ROI achievement)
  - AI Agent 2: Budget Risk Monitor (active promotions ≥90% budget consumed)
  - AI Agent 3: Planner Assistant (overlapping promotions same channel/brand, cannibalization risk)
- [x] `backend/app/api/v1/endpoints/tpm.py` — 20+ routes at /api/v1/tpm/
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/tpm.ts` — TypeScript client + all labels + fmtCurrency
- [x] Frontend pages (9 screens):
  - TPM Dashboard (KPI cards, budget bar, promotions by status, quick links)
  - Promotion Calendar (month grid with overlap detection and color-coded type bars)
  - TPM Plans list (CRUD + approve + activate + close)
  - New Plan form
  - Trade Promotions list (CRUD + status workflow)
  - New Promotion form (targeting scope: brand/channel/region/distributor)
  - Promotion Detail (tabbed: overview, budget, performance, claims)
  - Budget & Spend Monitor (planned/approved/actual/accrued/variance/utilization bar per promotion)
  - Claims & Deduction Queue (submit/review/approve/reject/settle workflow)
  - Settlement Tracker (pending vs partial vs settled claims)
  - ROI / Post-Event Analysis (expected vs actual ROI, uplift, top performers vs underperformers)
  - AI Agents (ROI Analyst + Budget Risk Monitor + Planner Assistant)
- [x] Sidebar: "Trade Promotion Mgmt" section added to nav-config.tsx (9 items)

## Next Immediate Task
Phase 23 — Advanced CRM Pipeline

## Blockers
None

---

## Phase 21 — Promotional Schemes Auto-Apply ✅

- [x] `backend/app/models/promotions.py` — 8 enums + 9 models:
  - Enums: SchemeStatus, SchemeType, TriggerBasis, RewardType, PromoApplicationType, PromoImpactType, OverrideStatus, PromoAIAgentType, PromoAIRecStatus
  - Models: PromoScheme, PromoEligibility, PromoRuleLine, PromoTierLine, SalesOrderPromo, SalesOrderPromoLine, PromoUsageTally, OverrideRequest, PromoAIRecommendation
- [x] `backend/app/schemas/promotions.py` — full Pydantic v2 schemas with `from __future__ import annotations` + `model_rebuild()`
- [x] `backend/app/services/promotions_service.py`:
  - Eligibility engine (customer, channel, region, category, brand scoping with OR logic)
  - Rule evaluation engine (_evaluate_rule, _build_line_impact, _build_order_level_impact)
  - 10 scheme types: BUY_X_GET_Y, PERCENT_DISCOUNT, FIXED_DISCOUNT, TIERED_DISCOUNT, QTY_BREAK_PRICE, SPEND_BASED, MIX_AND_MATCH, BUNDLE, FREE_GOODS_DIFF_SKU, CHANNEL_DEAL
  - Stacking/exclusivity conflict resolution (priority_rank + exclusive flag)
  - Next-threshold hints (add N units to unlock %)
  - Monthly cost tally upsert (UNIQUE scheme_id + tally_month)
  - Override approval workflow
  - AI Agent 1: Conflict Advisor (overlapping schemes, stacking conflicts)
  - AI Agent 2: Cost Monitor (schemes over monthly budget)
  - AI Agent 3: Upsell Assistant (near-threshold orders)
- [x] `backend/app/api/v1/endpoints/promotions.py` — 20+ routes at /api/v1/promotions/
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/promotions.ts` — TypeScript client + labels + fmtCurrency
- [x] Frontend pages (8 screens):
  - Dashboard (KPIs + active/expiring schemes)
  - Scheme Master List (with activate/suspend/resume actions)
  - New Scheme — Rule Builder (header + eligibility scopes + dynamic rule lines)
  - Scheme Detail (full read-only view with usage stats)
  - Promotion Simulator (test promotions against sample orders)
  - Override Approval Queue (approve/reject pending requests)
  - Cost Analytics (usage table + cost share progress bars)
  - AI Agents (Conflict Advisor + Cost Monitor + Upsell Assistant)
- [x] Sidebar: "Promotional Schemes" section added to nav-config.tsx

## Next Immediate Task
Phase 22 — Trade Promotion Management Enhancement

## Blockers
None

---

## Phase 20 — Accounting Dimensions / Cost Centers ✅

- [x] `backend/app/models/dimensions.py` — 9 enums + 11 models:
  - Enums: DimensionScope, CostCenterType, DimSourceType, AllocationBasis, AllocationFrequency, AllocationRunStatus, ValidationSeverity, DimAIAgentType, DimAIRecStatus
  - Models: DimType, DimValue (hierarchical), CostCenter (hierarchical), TransactionDimension, DimValidationRule, AllocationRule, AllocationRuleLine, AllocationRun, AllocationRunLine, DimDefaultRule, DimReclassification, DimAIRecommendation
- [x] `backend/app/schemas/dimensions.py` — full Pydantic v2 schemas for all create/read/request DTOs
- [x] `backend/app/services/dimensions_service.py`:
  - CRUD for dim types, values, cost centers
  - Transaction tagging (upsert with lock enforcement)
  - Default derivation engine (priority-ordered rule matching)
  - Validation engine (check mandatory dimensions per transaction type)
  - Allocation engine (FIXED_PCT + weight-based, dry-run/post modes)
  - Reclassification service (audit trail + tag update)
  - AI Agent 1: Completeness Monitor (empty types, untagged mandatory)
  - AI Agent 2: Allocation Optimizer (missing lines, pct ≠ 100)
  - AI Agent 3: Profitability Lens (no production cost centers)
- [x] `backend/app/api/v1/endpoints/dimensions.py` — 25+ routes at /api/v1/dimensions/
- [x] `backend/app/models/__init__.py` + `router.py` updated
- [x] `frontend/src/lib/dimensions.ts` — TypeScript client + labels
- [x] Frontend pages (10 screens):
  - Dashboard (KPIs + quick links)
  - Dimension Type Manager
  - Dimension Value Tree Manager
  - Cost Center Master
  - Allocation Rule Manager
  - Allocation Run Screen
  - Validation Rule Manager
  - Default Derivation Rules
  - Reclassification Workflow
  - Tagging Completeness Report
  - AI Agents
- [x] Sidebar: "Accounting Dimensions" section added to nav-config.tsx

## Next Immediate Task
Phase 21 — Promotional Schemes Auto-Apply

## Blockers
None

---

## Phase 19 — Fixed Asset Accounting + Depreciation ✅ COMPLETED

---

## Phase 15 — Subcontracting System ✅ COMPLETED

---

## Phase 15 — Subcontracting System ✅

- [x] `backend/app/models/subcontracting.py` — 6 enums + 10 models:
  - Enums: SCOrderStatus (8), SCIssueStatus, SCReceiptStatus, SCYieldStatus, SCAIAgentType, ScrapReasonCode
  - Models: SubcontractorLocation (virtual warehouse per supplier), SubcontractOrder (header), SubcontractOrderLine (what to produce), SubcontractMaterialIssue (material send header), SubcontractMaterialIssueLine (per-material with lots), SubcontractReceipt (goods received header), SubcontractReceiptLine (per FG line), SubcontractYieldRecord (yield/variance per order line), SCPerformanceRecord (KPI per order), SCAIRecommendation
- [x] `backend/app/schemas/subcontracting.py` — full Pydantic v2 schemas
- [x] `backend/app/services/subcontracting_service.py`:
  - create_order / approve_order / complete_order
  - issue_materials → stock movement source warehouse → subcontractor virtual location
  - receive_goods → stock movement subcontractor → factory, updates order line qty
  - _recalculate_yield → actual vs expected yield, scrap tracking, yield status
  - _upsert_performance → KPI calc: delay days, rejection rate, yield, cost variance, score 0-100
  - get_subcontractor_stock → aggregate materials at active subcontractor locations
  - AI Agent 1: Performance Analyzer (low yield + overdue orders)
  - AI Agent 2: Cost Optimizer (high wastage cost detection)
  - AI Agent 3: Risk Detector (missing locations + near-deadline orders)
- [x] `backend/app/api/v1/endpoints/subcontracting.py` — 20 routes at /api/v1/subcontracting/
- [x] `frontend/src/lib/subcontracting.ts` — types, API client, color helpers
- [x] Frontend pages:
  - Dashboard (KPIs, recent orders, quick links)
  - Orders (list + create + detail with issues/receipts/yield)
  - SC Locations (virtual warehouse management)
  - Subcontractor Stock (materials at external sites, grouped by supplier)
  - Yield Analysis (actual vs expected, variance, scrap)
  - Performance (KPI table with scoring bars, delivery/quality/cost)
  - AI Agents (3 agents, risk badges, action tracking)
- [x] Nav: "Subcontracting" section with 7 links

**DB MIGRATION STATUS — FULLY APPLIED ✅**
- Tables already existed from prior worktree work
- Migration marker `4a1b1eba5eed_subcontracting_system` applied ✅
- Single clean head: `4a1b1eba5eed` ✅
- All 20 API endpoints verified ✅

---

## Next: Prompt 16 — Landed Cost Allocation

## Blockers
None

---

## Phase 14 — Procurement Suggestion Engine ✅ COMPLETED

---

## Phase 14 — Procurement Suggestion Engine ✅

- [x] `backend/app/models/procurement_suggestion.py` — 6 enums + 5 models:
  - Enums: PSRunStatus, PSSuggestionStatus, PSUrgencyLevel, PSGroupStatus, PSAIAgentType, SupplierItemPriority
  - Models: SupplierItemPrice (multi-supplier per material with MOQ/lead-time), ProcurementSuggestionRun (engine header), ProcurementSuggestionLine (per-item suggestion with full detail), ProcurementSuggestionGroup (consolidated supplier orders), PSAIRecommendation (3 AI agents)
- [x] `backend/app/schemas/procurement_suggestion.py` — full Pydantic v2 schemas
- [x] `backend/app/services/procurement_suggestion_service.py`:
  - Core engine: MRP shortage pull + safety stock/reorder point sweep
  - Supplier scoring: priority + reliability + performance + preferred supplier weighted score
  - MOQ enforcement + pack_size rounding (ceil to valid multiple)
  - Lead-time planning: lead + buffer + customs days → suggested order date
  - Urgency classification: CRITICAL/HIGH/MEDIUM/LOW
  - Risk detection: single-supplier, long lead time, no supplier mapped
  - Recommendation scoring 0-100
  - Supplier grouping/consolidation by supplier
  - Convert group → Purchase Requisition
  - Supplier comparison engine (all suppliers for a material, scored)
  - Dashboard stats
  - Shortage report
  - AI Agent 1: Supplier Optimizer (cheapest alternative finder)
  - AI Agent 2: Demand Risk Predictor (critical shortage + unmapped material alerts)
  - AI Agent 3: Cost Optimizer (bulk purchase opportunity detector)
- [x] `backend/app/api/v1/endpoints/procurement_suggestion.py` — 20+ routes at /api/v1/procurement/suggestions/
- [x] `frontend/src/lib/procurement_suggestion.ts` — types, API client, color helpers
- [x] `frontend/src/app/dashboard/procurement-suggestion/` — 7 pages:
  - Dashboard (run engine, latest runs, KPIs, quick links)
  - Suggestions list (filter by urgency/status/risk, approve/reject, supplier compare panel)
  - Grouped orders (consolidated by supplier, convert-to-PR modal)
  - Supplier prices (CRUD for supplier-item price mappings)
  - Supplier compare (score all suppliers for a material)
  - Shortage report (detailed shortage analysis with cost projection)
  - AI agents (run all 3 agents, view/action recommendations)
- [x] Nav: "Procurement Suggestion Engine" section with 7 links

**DB MIGRATION STATUS — FULLY APPLIED ✅**
- Merged 3 diverging heads → `87ad3195d2c5_merge_all_heads` ✅
- Generated `4cddbd375e74_procurement_suggestion_engine` ✅
- Removed accidental table drops (currencies, system_configs, number_series, uom_conversions) ✅
- Added missing `app.models.utilities` import to `__init__.py` ✅
- Applied migration: `alembic upgrade head` ✅
- Verified: 297 tables, 5 new tables (supplier_item_prices, procurement_suggestion_runs/lines/groups, ps_ai_recommendations) ✅
- API tested: CREATE/EXECUTE run → 40 suggestions, 28 AI recs ✅
- Single clean head: `4cddbd375e74` ✅

---

## Next: Prompt 15 — Subcontracting

## Blockers
None

---

## Previous Phase
Phase 13 — Allergen + Nutrition Management System ✅ COMPLETED

---

## Phase 13 — Allergen + Nutrition Management System ✅

- [x] `backend/app/models/allergen.py` — 8 enums + 10 models:
  - Enums: AllergenCategory, PresenceType, CrossContactRisk, NutrientBasis, NutrientSource, LabelBasisType, AllergenChangeType, ANAIAgentType, ANAIRecStatus
  - Models: AllergenMaster, MaterialAllergenProfile, MaterialAllergenLine, NutritionProfile, NutritionProfileLine, ProductAllergenSummary, ProductNutritionSummary, AllergenChangeLog, ProductServingConfig, ANAIRecommendation
- [x] `backend/app/schemas/allergen.py` — full Pydantic v2 schemas including roll-up results, BOM comparison, label readiness
- [x] `backend/app/services/allergen_service.py`:
  - Default allergen seeder (15 EU/FDA major allergens)
  - Allergen master CRUD
  - Material allergen profile CRUD with line management (presence_type, declaration_required, critical_flag)
  - Nutrition profile CRUD with line management (per 100g values, source type, approval)
  - Allergen roll-up from BOM (recursive multi-level + child BOM traversal)
  - Allergen roll-up from Recipe (material-weighted)
  - Nutrition roll-up from BOM (yield/loss-aware, weight-factor accumulation per 100g)
  - Nutrition roll-up from Recipe (weighted sum normalized to output qty)
  - Product allergen summary save/refresh with label statement generation
  - Product nutrition summary save/refresh with per-100g and per-serving values
  - BOM allergen comparison (added/removed/changed presence/declaration changes)
  - BOM nutrition comparison (% change per nutrient, significance threshold)
  - Label readiness check (6-point checklist, readiness score 0–100)
  - Allergen change log management with label/QC review workflow
  - AI Agent 1: Allergen Risk Monitor (missing profiles, stale summaries, high cross-contact)
  - AI Agent 2: Nutrition Change Analyzer (stale nutrition, missing nutrition profiles)
  - AI Agent 3: Label Compliance Assistant (missing serving config, open label reviews)
  - Dashboard aggregation
- [x] `backend/app/api/v1/endpoints/allergen.py` — 45+ routes at /api/v1/allergen/:
  - GET /allergen/dashboard
  - CRUD /allergen/allergens + POST /allergen/allergens/seed-defaults
  - GET/POST /allergen/materials/allergen-profiles + /materials/{id}/allergen-profile
  - GET/POST /allergen/materials/{id}/nutrition-profile
  - GET/POST /allergen/products/{id}/nutrition-profile
  - POST /allergen/nutrition-profiles/{id}/lines, PATCH /allergen/nutrition-profiles/lines/{id}
  - GET /allergen/bom/{id}/allergen-rollup, /bom/{id}/nutrition-rollup
  - GET /allergen/recipe/{id}/allergen-rollup, /recipe/{id}/nutrition-rollup
  - GET /allergen/products/allergen-summaries, /products/{id}/allergen-summary
  - POST /allergen/products/{id}/allergen-summary/calculate
  - GET /allergen/products/nutrition-summaries, /products/{id}/nutrition-summary
  - POST /allergen/products/{id}/nutrition-summary/calculate
  - GET/POST /allergen/products/{id}/serving-config
  - GET /allergen/products/{id}/label-readiness
  - GET /allergen/bom/compare/{a}/{b}/allergens, /bom/compare/{a}/{b}/nutrition
  - GET/PATCH /allergen/change-logs
  - POST /allergen/ai/run-* (3 agents), GET+PATCH /allergen/ai/recommendations
  - Reports: rm-allergens, fg-allergens, nutrition-completeness, missing-statements
- [x] `frontend/src/lib/allergen.ts` — types, API client, color maps, default nutrients
- [x] `frontend/src/app/dashboard/allergen/` — 11 pages:
  - page.tsx (dashboard KPIs, quick navigation, AI run buttons, missing profile alerts)
  - allergens/page.tsx (allergen master CRUD, seed defaults button, category badges)
  - material-profiles/page.tsx (material allergen profiling with multi-line allergen entry, cross-contact risk, detail modal)
  - nutrition/page.tsx (nutrition profile grid with per-100g values, add line modal)
  - product-allergens/page.tsx (product allergen summaries table, recalculate modal, stale indicators)
  - product-nutrition/page.tsx (nutrition summary table with key nutrients, nutrition panel modal, recalculate)
  - rollup/page.tsx (BOM/recipe roll-up viewer with side-by-side allergen + nutrition results)
  - label-readiness/page.tsx (6-point readiness checklist with score bar, warning panel)
  - change-logs/page.tsx (allergen change logs with label/QC review workflow)
  - reports/page.tsx (4 report tabs: RM allergens, FG declaration, nutrition completeness, missing statements)
  - ai/page.tsx (3 AI agents, recommendations list, accept/reject workflow)
- [x] Nav: "Allergen & Nutrition" section with 11 links added (warning triangle icon)
- [x] Router, models/__init__.py updated

**DB MIGRATION NEEDED:** `alembic revision --autogenerate -m "allergen_nutrition_system"` then `alembic upgrade head`

---

## Phase 12 — GS1 Barcode + Label Printing System ✅

- [x] `backend/app/models/gs1.py` — 8 enums + 9 models:
  - Enums: BarcodeType, PackagingLevel, PrintJobStatus, SSCCStatus, LabelTemplateStatus, PrintTrigger, GS1AIAgentType, GS1AIRecStatus
  - Models: GS1CompanyConfig, ProductGS1Config, LotBarcodeRecord, SSCCPallet, SSCCPalletLot, GS1LabelTemplate, LabelPrintJob, LabelPrintJobItem, GS1AIRecommendation
- [x] `backend/app/schemas/gs1.py` — full Pydantic v2 schemas
- [x] `backend/app/services/gs1_service.py`:
  - GS1 check digit algorithms (EAN-13, GTIN-14, SSCC mod-10)
  - GS1 AI string builder (01 GTIN, 10 lot, 17 expiry, 11 prod date, 21 serial)
  - GS1 string parser (human-readable parens + FNC1 raw)
  - SSCC generator (18-digit, auto-incrementing serial reference)
  - Barcode image generation (python-barcode SVG + QR via qrcode[pil])
  - Fallback pure-Python SVG barcode (no dependency required)
  - CRUD for all models
  - AI Agent 1: Label Validator (missing GTINs, unconfigured products, invalid check digits)
  - AI Agent 2: Packaging Optimizer (missing hierarchy, over-mixed pallets)
  - Dashboard aggregation, print history, SSCC tracking, packaging hierarchy, barcode usage reports
- [x] `backend/app/api/v1/endpoints/gs1.py` — 35+ routes at /api/v1/gs1/:
  - GET /gs1/dashboard
  - CRUD /gs1/config (company GS1 config)
  - CRUD /gs1/products (product GS1 config), GET /gs1/products/by-product/{id}
  - POST /gs1/barcode/generate, GET /gs1/barcode
  - POST+GET /gs1/scan/decode
  - POST /gs1/sscc/generate, GET /gs1/sscc, POST /gs1/sscc/{id}/lots, PATCH /gs1/sscc/{id}/status
  - CRUD /gs1/labels/templates
  - POST /gs1/labels/print, GET, POST /gs1/labels/print/{id}/complete
  - POST /gs1/ai/run-label-validator, POST /gs1/ai/run-packaging-optimizer
  - GET+PATCH /gs1/ai/recommendations
  - GET /gs1/reports/{print-history|sscc-tracking|packaging-hierarchy|barcode-usage}
- [x] `backend/requirements.txt` — added python-barcode, qrcode[pil], Pillow
- [x] `frontend/src/lib/gs1.ts` — types, API client, color maps
- [x] `frontend/src/app/dashboard/gs1/` — 9 pages:
  - page.tsx (dashboard with KPIs, recent barcodes, recent SSCC, AI run buttons)
  - config/page.tsx (GS1 company config + product GS1 config with packaging hierarchy)
  - barcodes/page.tsx (barcode generator with live preview, barcode image, QR code, history)
  - labels/page.tsx (label template editor with HTML template, field toggles, preview modal)
  - print-queue/page.tsx (print job management with trigger types, status tracking)
  - sscc/page.tsx (SSCC pallet generation, lot linking, status lifecycle)
  - scan/page.tsx (GS1 string decoder, AI reference table, validation, lot/product lookup)
  - reports/page.tsx (4 report tabs: print history, SSCC tracking, packaging hierarchy, barcode usage)
  - ai/page.tsx (AI agent runner, recommendation review with accept/reject workflow)
- [x] Nav: "GS1 & Label Printing" section with 9 links added
- [x] Router, models/__init__.py updated

**DB MIGRATION NEEDED:** `alembic revision --autogenerate -m "gs1_barcode_label_system"` then `alembic upgrade head`

---

## Phase 11 — Quality Checkpoints + Release Logic + HACCP / Food Safety ✅

---

## Phase 11 — Quality Checkpoints + Release Logic + HACCP / Food Safety ✅

- [x] `backend/app/models/quality.py` — Extended with 9 new enums + 11 new models:
  - New enums: SamplingMethod, HazardType, RiskLevel, DeviationStatus, CorrectiveActionStatus, ReleaseStatus, QMSAIAgentType, QMSAIRecStatus
  - Extended QCType with RETEST; QCInspection extended with template_id, qc_sub_type, work_order_id, is_mandatory, blocks_progression, release_required, hold_flag
  - QCTemplate + QCTemplateParameter — reusable inspection templates per item/stage/category
  - HazardAnalysis — HACCP hazard records with likelihood × severity risk scoring
  - CriticalControlPoint — CCP definitions with critical limits, monitoring, and corrective action
  - CCPMonitoringLog — real-time monitoring entries with auto-violation detection
  - CorrectiveAction + CorrectiveActionStep — CA workflow with step-by-step tracking
  - QCDeviation — deviation records linked to inspections/lots/products
  - LotQualityStatus — per-lot release gate controlling FEFO eligibility and shipment
  - AllergenValidationRecord — allergen cleaning validation between production runs
  - QMSAIRecommendation — 3 AI agent recommendations with review workflow
- [x] `backend/app/schemas/qms.py` — Pydantic v2 schemas for all QMS models
- [x] `backend/app/services/qms_service.py`:
  - QC Template CRUD
  - Sampling plan calculation (fixed/percentage/frequency/time-based)
  - QC gate check — blocks progression if mandatory QC is pending or failed
  - Lot hold and release with FEFO/shipment eligibility flags
  - Lot quality status sync from inspection decision
  - HACCP hazard analysis creation with risk score calculation
  - CCP creation with auto-number
  - CCP limit checking with violation detection
  - CCP monitoring recording with auto corrective action creation on violation
  - Auto corrective action creation from CCP violations (steps parsed from CA description)
  - Deviation creation and auto-creation from failed inspections
  - Allergen validation creation
  - QMS dashboard aggregation (17 KPIs)
  - AI Agent 1: Quality Risk Predictor — high failure rate lots, open deviations
  - AI Agent 2: Deviation Analyzer — recurring type patterns, repeated CCP violations
  - AI Agent 3: HACCP Assistant — missing CCPs for high-risk hazards, unmonitored CCPs, allergen CCP gaps
- [x] `backend/app/api/v1/endpoints/qms.py` — 40+ routes at /api/v1/qms/:
  - GET /qms/dashboard
  - GET /qms/gate-check — lot progression gate check
  - CRUD /qms/templates + /qms/templates/{id}
  - CRUD /qms/haccp/hazards + /qms/haccp/hazards/{id}
  - CRUD /qms/haccp/ccp + /qms/haccp/ccp/{id}
  - GET /qms/haccp/ccp/{id}/logs, POST /qms/haccp/monitoring
  - GET /qms/haccp/violations
  - CRUD /qms/deviations + /qms/deviations/{id}
  - CRUD /qms/corrective-actions + steps completion + verification
  - GET/POST /qms/lot-status, /qms/lot-status/release, /qms/lot-status/hold
  - CRUD /qms/allergen-validations
  - GET/POST /qms/ai/recommendations + run endpoints (3 agents)
  - Reports: /qms/reports/qc-summary, ccp-violations, deviations, lot-quality
- [x] `backend/app/models/__init__.py` — all new models + enums exported
- [x] `backend/app/api/v1/router.py` — /api/v1/qms wired
- [x] `frontend/src/lib/qms.ts` — types, API client (35+ methods), color maps
- [x] `frontend/src/app/dashboard/qms/page.tsx` — QMS Dashboard (5 KPI sections, quick nav)
- [x] `frontend/src/app/dashboard/qms/inspections/page.tsx` — QC Inspection list with type/status filters
- [x] `frontend/src/app/dashboard/qms/templates/page.tsx` — QC Template editor with parameter viewer
- [x] `frontend/src/app/dashboard/qms/haccp/page.tsx` — HACCP Hazard Analysis with new record form
- [x] `frontend/src/app/dashboard/qms/ccp/page.tsx` — CCP Monitoring Dashboard with live monitoring entry
- [x] `frontend/src/app/dashboard/qms/deviations/page.tsx` — Deviation Management with resolve workflow
- [x] `frontend/src/app/dashboard/qms/corrective-actions/page.tsx` — CA Tracker with step completion and verification
- [x] `frontend/src/app/dashboard/qms/quarantine/page.tsx` — Quarantine/Hold Management with release modal
- [x] `frontend/src/app/dashboard/qms/allergen/page.tsx` — Allergen Validation records
- [x] `frontend/src/app/dashboard/qms/ai/page.tsx` — AI Quality Agents (run, review, accept/reject)
- [x] `frontend/src/app/dashboard/qms/reports/page.tsx` — QMS Reports (4 report panels)
- [x] `frontend/src/components/nav-config.tsx` — "QMS & HACCP" section with 11 nav links

**DB MIGRATION NEEDED:** `alembic revision --autogenerate -m "qms_haccp_system"` then `alembic upgrade head`

## Next Immediate Task: Prompt 12 — GS1 Barcode + Label Printing

## In Progress
- None — Prompt 11 complete

## Blockers
- None

---

## Phase 10 — Full Lot Traceability + Batch Recall Management ✅ COMPLETED

---

## Completed in This Run

### Phase 10 — Lot Traceability + Batch Recall Management ✅
- [x] `backend/app/models/traceability.py` — 9 models, 13 enums:
  - Enums: TraceEventType(13), TraceItemStage(13), GenealogyRelType(10), RecallType(5),
    RecallTrigger(6), RecallSeverity(4), RecallStatus(8), RecallActionType(11),
    RecallActionStatus(5), RecallRiskStatus(4), TRRecAIAgentType(3), TRRecAIRecStatus(4)
  - TraceEvent — immutable event header (receipt/issue/transformation/packaging/shipment/rework/scrap)
  - TraceEventLine — source_lot → child_lot movement per event with stage, quantity, customer/supplier links
  - LotGenealogyLink — directed graph edge (parent_lot → child_lot) with rel_type and quantity
  - RecallHeader — full recall header with time-to-trace, effectiveness, recovery_pct
  - RecallScopeLine — per-lot affected quantities by state (stock/transit/shipped/returned/quarantined/scrapped/reworked)
  - RecallAction — 11 action types with due date, completion, evidence
  - RecallCustomerImpact — per-customer delivery/notification/return tracking
  - RecallReturnRecord — quantity return tracking with discrepancy and follow-up flags
  - TRRecAIRecommendation — 3 AI agents (scope_validator, risk_prioritizer, investigation_assistant)
- [x] `backend/app/schemas/traceability.py` — all Pydantic v2 request/response schemas
- [x] `backend/app/services/traceability_service.py`:
  - Trace event create with auto-genealogy link creation
  - List events by lot or event type
  - Genealogy link CRUD + directional list
  - Forward trace BFS engine (descendant lots → shipments → customers, quantity by state)
  - Backward trace BFS engine (ancestor lots → production orders → suppliers → GRNs)
  - Genealogy tree builder (directed graph nodes + edges, stage summary)
  - Traceability search by lot number / batch / product / material / supplier / customer
- [x] `backend/app/services/recall_service.py`:
  - Recall initiation with auto-generated recall number
  - Recall status update workflow (draft → under_review → active → contained → completed → closed)
  - Scope calculation: forward-traces all source lots, builds per-lot RecallScopeLine records
  - Containment: places is_blocked=True on all affected Stock records, records hold timestamps
  - Recall action CRUD + completion workflow with evidence capture
  - Customer impact building from shipment trace event lines
  - Customer notification tracking
  - Return recording with discrepancy computation and follow-up flags
  - Recovery % auto-update on each return
  - Recall close with effectiveness score
  - Regulatory report generation (narrative summary + lot list + actions + metrics)
  - Recall dashboard KPIs
  - 3 AI agents: ScopeValidator, RiskPrioritizer, InvestigationAssistant
- [x] `backend/app/api/v1/endpoints/traceability.py` — 28 routes at /api/v1/traceability/
- [x] `backend/app/api/v1/router.py` — wired traceability router
- [x] `backend/app/models/__init__.py` — all 9 models + 13 enums exported
- [x] `frontend/src/lib/traceability.ts` — types, API client (32 methods), label/color maps
- [x] `frontend/src/app/dashboard/traceability/page.tsx` — Recall Dashboard (KPIs, recent recalls, quick nav)
- [x] `frontend/src/app/dashboard/traceability/search/page.tsx` — Trace Search Console (multi-field, results with trace links)
- [x] `frontend/src/app/dashboard/traceability/backward/page.tsx` — Backward Trace Viewer (ancestor lots, POs, suppliers, GRNs)
- [x] `frontend/src/app/dashboard/traceability/forward/page.tsx` — Forward Trace Viewer (qty breakdown, descendant lots, shipments)
- [x] `frontend/src/app/dashboard/traceability/genealogy/page.tsx` — Genealogy Graph/Tree (table + node view, stage summary)
- [x] `frontend/src/app/dashboard/traceability/recalls/page.tsx` — Recall List (all recalls, status filters, initiate modal)
- [x] `frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx` — Recall Detail (6-tab: overview/scope/actions/customers/returns/AI)
- [x] `frontend/src/app/dashboard/traceability/mock-recall/page.tsx` — Mock Recall Drill (end-to-end timed drill, effectiveness score)
- [x] `frontend/src/app/dashboard/traceability/regulatory/page.tsx` — Regulatory Report (print-ready, recall summary, actions, metrics)
- [x] `frontend/src/components/nav-config.tsx` — "Traceability & Recall" cluster + 8 nav links

**DB MIGRATION NEEDED:** `alembic revision --autogenerate -m "lot_traceability_recall"` then `alembic upgrade head`

---

## Next Immediate Task: Prompt 11 — Quality Checkpoints + Release Logic + HACCP / Food Safety

## In Progress
- None — Prompt 10 complete

## Blockers
- None — `python -c "from app.main import app; print('OK')"` passes cleanly

---

## Phase 9 — FEFO + Shelf-Life Control ✅ COMPLETED

- [x] 10 models, 15 enums
- [x] FEFO ranking engine, expiry validation, retest, disposition, compliance audit, 3 AI agents
- [x] 39 routes at /api/v1/shelf-life/
- [x] 12 frontend pages

---

## Phase 8 — Machine + Operator Intelligence ✅ COMPLETED
## Phase 7 — Material Flow Engine ✅ COMPLETED
## Phase 6 — Advanced Production Planning Suite ✅ COMPLETED
## Phase 5 — MPS Engine ✅ COMPLETED
## Phase 4 — MRP + Demand Forecasting ✅ COMPLETED
## Phase 3 — AI Production Intelligence ✅ COMPLETED
## Phase 2 — Production Costing Engine ✅ COMPLETED
## Phase 1 — Utility Management ✅ COMPLETED
## Phase 0 — Inventory Bugfixes ✅ COMPLETED

---

## Architecture Notes
- Genealogy is a directed graph: TraceEvent creation auto-creates LotGenealogyLink edges
- Forward/backward trace uses BFS with visited-set to prevent cycles
- Recall scope calculation runs forward_trace from source lot(s) — builds RecallScopeLine per lot
- Containment: sets Stock.is_blocked = True for all stocks associated with scope lot IDs
- RecallCustomerImpact built from TraceEventLine records with event_type=shipment
- TRRecAIRecommendation always requires human review before any action is taken
- Mock recall drill records effectiveness_score from time-to-trace performance
- All monetary values in KES; all quantities in item-native UOM
- DB migration needed: `alembic revision --autogenerate -m "lot_traceability_recall"` before first use
