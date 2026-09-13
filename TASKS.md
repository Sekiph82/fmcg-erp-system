# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

`TASKS_HISTORY.md` preserves the previous detailed tracker as immutable/reference evidence. Historical Done states remain accepted. `PLANS.md` is architecture/strategy reference only. No other file is an active competing tracker.

---

## Project Status

- **Current Milestone:** M20 — Master Production Scheduling
- **Current Sprint:** M20.S01 — MPS Domain Reconciliation
- **Current Task:** M20.S01.T001 — Reconcile current MPS engine against bounded enterprise scope
- **Current Task Status:** READY
- **Next Task/Action:** Execute M20 remaining PARTIAL scope only; do not rebuild capabilities already present.
- **Required Actor:** BUILDER
- **Tracking Repository:** Sekiph82/fmcg-erp-system
- **Tracking Branch:** main
- **M00 Gate:** COMPLETE

## Status Legend

- `[x]` DONE
- `[~]` IN_PROGRESS
- `[ ]` PLANNED
- `[!]` BLOCKED
- `[-]` SUPERSEDED
- `[P]` PARTIAL / existing capability with bounded remaining scope
- `[D]` DEFERRED

## Mandatory Execution Rules

1. Milestone → Sprint → Task is the canonical hierarchy.
2. Existing capabilities are extended, never rebuilt without evidence that replacement is required.
3. A task may become DONE only with implementation evidence and appropriate tests/checks.
4. Historical tasks already marked Done remain accepted unless a later remediation explicitly supersedes them.
5. External credentials, live providers, production devices and live-DB acceptance must never be fabricated as PASS.
6. Cross-module changes must preserve RBAC, auditability, migrations, API contracts, frontend/backend consistency and tenant/company boundaries.
7. M20–M35 are enterprise upgrades layered on M01–M19 foundations.
8. Graphify is reference tooling only. Do not run refreshes without an explicit project need; no hooks, watchers or competing tracker state.
9. Every completed implementation task updates this ledger in the same GitHub-tracked change set or immediately following it.
10. Builder logs are evidence claims, not acceptance by themselves.

---

# M00 — Governance & Repository Baseline

**Status: DONE**

## M00.S01 — Canonical Tracker Migration
- [x] M00.S01.T001 — Preserve previous tracker as `TASKS_HISTORY.md`
- [x] M00.S01.T002 — Establish root `TASKS.md` as canonical H!veAI ledger
- [x] M00.S01.T003 — Preserve historical task IDs/status evidence
- [x] M00.S01.T004 — Migrate TASK-001 through TASK-027 families
- [x] M00.S01.T005 — Preserve Manual/Help/Push/Local-Staging/Data-Cleanup families

## M00.S02 — Repository Capability Inventory
- [x] M00.S02.T001 — Backend architecture/module inventory
- [x] M00.S02.T002 — Frontend route/page/component inventory
- [x] M00.S02.T003 — Database model/migration/schema inventory
- [x] M00.S02.T004 — API/router/service inventory
- [x] M00.S02.T005 — Jobs/queues/schedulers/event inventory
- [x] M00.S02.T006 — CSV/import/export/reporting inventory
- [x] M00.S02.T007 — Integration/provider inventory
- [x] M00.S02.T008 — Tests/CI/Docker/deployment inventory
- [x] M00.S02.T009 — Documentation/reference inventory

## M00.S03 — Existing-System Audit M01–M19
- [x] M00.S03.T001 — M01 Platform / Infrastructure audit — PARTIAL
- [x] M00.S03.T002 — M02 Authentication / RBAC audit — PARTIAL
- [x] M00.S03.T003 — M03 Master Data audit — PARTIAL
- [x] M00.S03.T004 — M04 Product / Material / Supplier Master audit — ALREADY_DONE
- [x] M00.S03.T005 — M05 Warehouse & Inventory audit — PARTIAL
- [x] M00.S03.T006 — M06 Procurement audit — PARTIAL
- [x] M00.S03.T007 — M07 Sales / Distributor Operations audit — PARTIAL
- [x] M00.S03.T008 — M08 Production Core audit — PARTIAL
- [x] M00.S03.T009 — M09 Recipes / BOM audit — PARTIAL
- [x] M00.S03.T010 — M10 Quality audit — PARTIAL
- [x] M00.S03.T011 — M11 Maintenance audit — PARTIAL
- [x] M00.S03.T012 — M12 Utilities audit — ALREADY_DONE
- [x] M00.S03.T013 — M13 Finance / Costing audit — PARTIAL
- [x] M00.S03.T014 — M14 HR / Operator / Shift audit — PARTIAL
- [x] M00.S03.T015 — M15 Reporting / Analytics audit — ALREADY_DONE
- [x] M00.S03.T016 — M16 AI audit — PARTIAL
- [x] M00.S03.T017 — M17 Integrations audit — PARTIAL
- [x] M00.S03.T018 — M18 Kenya Localization audit — PARTIAL
- [x] M00.S03.T019 — M19 Security / Deployment / Hardening audit — PARTIAL

## M00.S04 — M20–M35 Existing-vs-Planned Reconciliation
- [x] M00.S04.T001 — M20 MPS reconciliation — PARTIAL
- [x] M00.S04.T002 — M21 Advanced BOM reconciliation — PARTIAL
- [x] M00.S04.T003 — M22 Production/Work Order reconciliation — PARTIAL
- [x] M00.S04.T004 — M23 Shop Floor reconciliation — PARTIAL
- [x] M00.S04.T005 — M24 Material Flow reconciliation — PARTIAL
- [x] M00.S04.T006 — M25 Cross-Border/Landed Cost reconciliation — PARTIAL
- [x] M00.S04.T007 — M26 Machine/Operator Intelligence reconciliation — PARTIAL
- [x] M00.S04.T008 — M27 Quality Gates reconciliation — PARTIAL
- [x] M00.S04.T009 — M28 Traceability reconciliation — PARTIAL
- [x] M00.S04.T010 — M29 Maintenance/OEE reconciliation — PARTIAL
- [x] M00.S04.T011 — M30 AI Decision/Simulation reconciliation — PARTIAL
- [x] M00.S04.T012 — M31 API/Event reconciliation — PARTIAL
- [x] M00.S04.T013 — M32 Advanced Planning reconciliation — PARTIAL
- [x] M00.S04.T014 — M33 Warehouse Enterprise reconciliation — PARTIAL
- [x] M00.S04.T015 — M34 Procurement Enterprise reconciliation — PARTIAL
- [x] M00.S04.T016 — M35 QC/QA Enterprise reconciliation — PARTIAL

## M00.S05 — Strict Pre-Enhancement Full System Audit
- [x] M00.S05.T001 — Backend architecture audit
- [x] M00.S05.T002 — Frontend architecture audit
- [x] M00.S05.T003 — Database/schema audit
- [x] M00.S05.T004 — API/route audit
- [x] M00.S05.T005 — Authentication/RBAC audit
- [x] M00.S05.T006 — Master Data audit
- [x] M00.S05.T007 — Inventory/Warehouse audit
- [x] M00.S05.T008 — Procurement audit
- [x] M00.S05.T009 — Sales audit
- [x] M00.S05.T010 — Production audit
- [x] M00.S05.T011 — BOM/Recipes audit
- [x] M00.S05.T012 — QC/QA audit
- [x] M00.S05.T013 — Maintenance audit
- [x] M00.S05.T014 — Utilities audit
- [x] M00.S05.T015 — Finance/Costing audit
- [x] M00.S05.T016 — HR/Operator/Shift audit
- [x] M00.S05.T017 — AI subsystem audit
- [x] M00.S05.T018 — Integrations audit
- [x] M00.S05.T019 — Kenya localization audit
- [x] M00.S05.T020 — Security/deployment/data-integrity/cross-module audit consolidation

## M00.S06 — Audit Findings & Enhancement Gate
- [x] M00.S06.T001 — Classify findings P0/P1/P2/P3
- [x] M00.S06.T002 — Confirm no source-level P0 blocker
- [x] M00.S06.T003 — Carry live/provider/runtime findings as explicit gates
- [x] M00.S06.T004 — Bound M20–M35 to remaining scope
- [x] M00.S06.T005 — Open M20 enhancement execution gate

---

# M01 — Platform / Infrastructure

**Status: PARTIAL — baseline exists; hardening remains**

## M01.S01 — Application Foundation
- [x] M01.S01.T001 — FastAPI modular backend foundation
- [x] M01.S01.T002 — Next.js App Router frontend foundation
- [x] M01.S01.T003 — PostgreSQL/SQLAlchemy/Alembic persistence foundation
- [x] M01.S01.T004 — Redis/cache/runtime service foundation
- [x] M01.S01.T005 — Docker development/production topology

## M01.S02 — Shared Enterprise Platform Services
- [x] M01.S02.T001 — Health/readiness/metrics surfaces
- [x] M01.S02.T002 — Centralized configuration/environment handling
- [x] M01.S02.T003 — Shared approval/workflow/custom-field/activity infrastructure
- [x] M01.S02.T004 — Import/export/report/help infrastructure
- [P] M01.S02.T005 — Complete production document binary storage/upload pipeline

## M01.S03 — Runtime Reliability
- [P] M01.S03.T001 — Prove always-running background/event dispatch ownership
- [P] M01.S03.T002 — Validate migration ownership on live-like database
- [D] M01.S03.T003 — Execute LOCAL-STAGING-001 when deployment environment is available
- [ ] M01.S03.T004 — Establish operational backup/restore rehearsal evidence

---

# M02 — Authentication / RBAC

**Status: PARTIAL**

## M02.S01 — Authentication Baseline
- [x] M02.S01.T001 — JWT/cookie authentication
- [x] M02.S01.T002 — Password hashing/policy/login lockout
- [x] M02.S01.T003 — JTI logout revocation/audit events
- [x] M02.S01.T004 — TOTP/email/SMS 2FA and recovery codes

## M02.S02 — Authorization Baseline
- [x] M02.S02.T001 — Role/permission model
- [x] M02.S02.T002 — Backend permission/scope helpers
- [x] M02.S02.T003 — Frontend permission/scope gating
- [x] M02.S02.T004 — AccessScope foundation

## M02.S03 — Session & Privilege Hardening
- [ ] M02.S03.T001 — Implement/verify refresh-token rotation lifecycle
- [ ] M02.S03.T002 — Implement inactivity/session-expiry policy
- [ ] M02.S03.T003 — Prove user-wide issued-session revocation
- [ ] M02.S03.T004 — Enforce privileged-role 2FA policy
- [ ] M02.S03.T005 — Verify CSRF and tenant/company isolation in production-like runtime

---

# M03 — Master Data

**Status: PARTIAL**

## M03.S01 — Shared Master Framework
- [x] M03.S01.T001 — Company/organizational master foundation
- [x] M03.S01.T002 — Custom fields/values/validation/layout framework
- [x] M03.S01.T003 — Bulk import framework
- [x] M03.S01.T004 — Audit and permission infrastructure

## M03.S02 — Governance Upgrade
- [ ] M03.S02.T001 — Standardize duplicate detection across masters
- [ ] M03.S02.T002 — Standardize merge/deactivation semantics
- [ ] M03.S02.T003 — Standardize version/effective-date governance
- [ ] M03.S02.T004 — Define master-data stewardship workflow
- [ ] M03.S02.T005 — Validate referential integrity across master domains

---

# M04 — Product / Material / Supplier Master

**Status: DONE baseline**

## M04.S01 — Product & Material Masters
- [x] M04.S01.T001 — Product model/API/UI
- [x] M04.S01.T002 — Material model/API/UI
- [x] M04.S01.T003 — Product/material CSV bulk import
- [x] M04.S01.T004 — Product editing and guarded deletion

## M04.S02 — Supplier & Warehouse Masters
- [x] M04.S02.T001 — Supplier model/API/UI
- [x] M04.S02.T002 — Warehouse master model/API/UI
- [x] M04.S02.T003 — Supplier/warehouse bulk import
- [x] M04.S02.T004 — FMCG-oriented reference/seed catalogs

---

# M05 — Warehouse & Inventory

**Status: PARTIAL; enterprise extension continues in M33**

## M05.S01 — Inventory Core
- [x] M05.S01.T001 — Lots and stock balances
- [x] M05.S01.T002 — Inventory movements
- [x] M05.S01.T003 — Warehouse/location linkage
- [x] M05.S01.T004 — Opening/seed stock support

## M05.S02 — WMS Baseline
- [x] M05.S02.T001 — WMS zones/locations
- [x] M05.S02.T002 — Cycle count
- [x] M05.S02.T003 — Shelf-life/FEFO support
- [x] M05.S02.T004 — Trace events
- [x] M05.S02.T005 — Inventory operational UI/manual coverage

## M05.S03 — Baseline Integrity
- [P] M05.S03.T001 — Validate reservation/allocation consistency
- [P] M05.S03.T002 — Validate transaction integrity across production/procurement/sales
- [P] M05.S03.T003 — Validate negative-stock/concurrency safeguards

---

# M06 — Procurement

**Status: PARTIAL; enterprise extension continues in M34**

## M06.S01 — Source-to-Order Baseline
- [x] M06.S01.T001 — Purchase requisitions
- [x] M06.S01.T002 — RFQ workflow
- [x] M06.S01.T003 — Purchase orders
- [x] M06.S01.T004 — Supplier master/portal integration

## M06.S02 — Receiving & Commercial Controls
- [x] M06.S02.T001 — Deliveries/receiving surfaces
- [x] M06.S02.T002 — Blanket/reorder concepts
- [x] M06.S02.T003 — Procurement suggestions
- [x] M06.S02.T004 — Subcontracting foundation
- [x] M06.S02.T005 — Invoice matching/landed-cost surfaces

## M06.S03 — Baseline Verification
- [P] M06.S03.T001 — Verify three-way-match transaction chain
- [P] M06.S03.T002 — Verify landed-cost accounting integration
- [P] M06.S03.T003 — Verify supplier performance data completeness

---

# M07 — Sales / Distributor Operations

**Status: PARTIAL**

## M07.S01 — Order-to-Cash Core
- [x] M07.S01.T001 — Customers and quotations
- [x] M07.S01.T002 — Sales orders
- [x] M07.S01.T003 — Invoices
- [x] M07.S01.T004 — Shipments/collections/returns
- [x] M07.S01.T005 — Pricing foundation

## M07.S02 — Distributor & Commercial Operations
- [x] M07.S02.T001 — Distributor/secondary sales
- [x] M07.S02.T002 — Van/field sales
- [x] M07.S02.T003 — Commissions
- [x] M07.S02.T004 — Recurring billing
- [x] M07.S02.T005 — Loyalty/NPS/customer analytics

## M07.S03 — Live Commercial Verification
- [P] M07.S03.T001 — Verify order-to-cash accounting closure
- [!] M07.S03.T002 — Validate live payment/provider flows when credentials exist
- [!] M07.S03.T003 — Validate live tax/eTIMS invoice flow when credentials exist

---

# M08 — Production Core

**Status: PARTIAL; enterprise extension continues in M22–M24**

## M08.S01 — Production Foundation
- [x] M08.S01.T001 — Work orders
- [x] M08.S01.T002 — Scheduling
- [x] M08.S01.T003 — Batch lots
- [x] M08.S01.T004 — Routing/work centers
- [x] M08.S01.T005 — Labor/shifts/time tracking

## M08.S02 — Performance & Execution Baseline
- [x] M08.S02.T001 — Shop-floor/execution surfaces
- [x] M08.S02.T002 — OEE
- [x] M08.S02.T003 — Downtime
- [x] M08.S02.T004 — Waste/yield
- [x] M08.S02.T005 — Production reporting/manual coverage

## M08.S03 — Baseline Integrity
- [P] M08.S03.T001 — Harden state-transition invariants
- [P] M08.S03.T002 — Verify production/inventory transaction atomicity
- [P] M08.S03.T003 — Verify production/QC/finance closure

---

# M09 — Recipes / BOM

**Status: PARTIAL; enterprise extension continues in M21**

## M09.S01 — Recipe Foundation
- [x] M09.S01.T001 — Recipe master/API/UI
- [x] M09.S01.T002 — Recipe BOM items
- [x] M09.S01.T003 — Process parameters
- [x] M09.S01.T004 — CSV import
- [x] M09.S01.T005 — Draft/edit constraints

## M09.S02 — BOM Foundation
- [x] M09.S02.T001 — BOM master/types
- [x] M09.S02.T002 — BOM lifecycle/statuses
- [x] M09.S02.T003 — BOM items and default semantics
- [P] M09.S02.T004 — Standardize effective-date/version governance

---

# M10 — Quality

**Status: PARTIAL; enterprise extension continues in M27/M35**

## M10.S01 — QC Baseline
- [x] M10.S01.T001 — QC parameters
- [x] M10.S01.T002 — QC inspections
- [x] M10.S01.T003 — Quality-control UI/API
- [x] M10.S01.T004 — Cross-module QC links

## M10.S02 — QMS Baseline
- [x] M10.S02.T001 — HACCP/PDCA/audit scheduling foundations
- [x] M10.S02.T002 — Allergen/compliance features
- [x] M10.S02.T003 — Complaint/recall domain
- [P] M10.S02.T004 — Harden hold/release transaction enforcement

---

# M11 — Maintenance

**Status: PARTIAL; enterprise extension continues in M29**

## M11.S01 — Maintenance Core
- [x] M11.S01.T001 — Asset register
- [x] M11.S01.T002 — Breakdown records
- [x] M11.S01.T003 — PM plans/work orders
- [x] M11.S01.T004 — Spare parts

## M11.S02 — Reliability Baseline
- [x] M11.S02.T001 — Predictive maintenance foundation
- [x] M11.S02.T002 — MTBF/MTTR reporting
- [x] M11.S02.T003 — Downtime reporting
- [x] M11.S02.T004 — Utility-alarm→maintenance integration

---

# M12 — Utilities

**Status: DONE baseline**

## M12.S01 — Utility Domains
- [x] M12.S01.T001 — Electricity
- [x] M12.S01.T002 — Water/soft water
- [x] M12.S01.T003 — Steam/boiler
- [x] M12.S01.T004 — Compressed air
- [x] M12.S01.T005 — Solar
- [x] M12.S01.T006 — Chemical treatment/wastewater

## M12.S02 — Utility Intelligence
- [x] M12.S02.T001 — Assets/devices/readings/transactions
- [x] M12.S02.T002 — Alarms/anomaly detection
- [x] M12.S02.T003 — KPI center/reporting
- [x] M12.S02.T004 — Production/inventory/QC/maintenance/finance integration

---

# M13 — Finance / Costing

**Status: PARTIAL**

## M13.S01 — Accounting Core
- [x] M13.S01.T001 — Chart of accounts/cost centers
- [x] M13.S01.T002 — Fiscal years/periods
- [x] M13.S01.T003 — GL/journal foundations
- [x] M13.S01.T004 — Cashbook/receivables/budget

## M13.S02 — Finance Operations
- [x] M13.S02.T001 — Bank reconciliation/API surfaces
- [x] M13.S02.T002 — Fixed assets
- [x] M13.S02.T003 — Payroll/expenses/contracts
- [x] M13.S02.T004 — Production costing
- [x] M13.S02.T005 — eTIMS/tax surfaces

## M13.S03 — Live Finance Verification
- [P] M13.S03.T001 — Verify landed-cost posting chain
- [!] M13.S03.T002 — Validate live bank integration when credentials exist
- [!] M13.S03.T003 — Validate live eTIMS posting when credentials exist
- [ ] M13.S03.T004 — Rehearse period close/reconciliation on staging/live-like DB

---

# M14 — HR / Operator / Shift

**Status: PARTIAL**

## M14.S01 — HR Core
- [x] M14.S01.T001 — Employees
- [x] M14.S01.T002 — Attendance/leave
- [x] M14.S01.T003 — Payroll
- [x] M14.S01.T004 — Recruitment/ESS
- [x] M14.S01.T005 — Appraisals/training

## M14.S02 — Workforce Operations
- [x] M14.S02.T001 — Shifts
- [x] M14.S02.T002 — Timesheets/expenses
- [x] M14.S02.T003 — Production labor/operator concepts
- [P] M14.S02.T004 — Extend skill/qualification enforcement in M26

---

# M15 — Reporting / Analytics

**Status: DONE baseline**

## M15.S01 — Reporting Platform
- [x] M15.S01.T001 — Report Builder
- [x] M15.S01.T002 — Scheduled/report infrastructure
- [x] M15.S01.T003 — Notification center
- [x] M15.S01.T004 — Module report surfaces

## M15.S02 — Analytics
- [x] M15.S02.T001 — Dashboards/KPIs
- [x] M15.S02.T002 — Operational analytics
- [x] M15.S02.T003 — Cross-module reporting foundations

---

# M16 — AI

**Status: PARTIAL; enterprise extension continues in M30**

## M16.S01 — Provider & Forecast Foundation
- [x] M16.S01.T001 — Anthropic provider support
- [x] M16.S01.T002 — OpenAI provider support
- [x] M16.S01.T003 — Gemini provider support
- [x] M16.S01.T004 — Provider auto-detection/fallback
- [x] M16.S01.T005 — Local Holt-Winters forecasting

## M16.S02 — Applied AI
- [x] M16.S02.T001 — AI models/services foundation
- [x] M16.S02.T002 — Module recommendations/agents
- [!] M16.S02.T003 — Live-provider acceptance with real API key
- [P] M16.S02.T004 — Govern confidence/explainability/autonomy in M30

---

# M17 — Integrations

**Status: PARTIAL / externally blocked in places**

## M17.S01 — Implemented Integration Foundations
- [x] M17.S01.T001 — Capability registry
- [x] M17.S01.T002 — M-Pesa integration foundation
- [x] M17.S01.T003 — WhatsApp integration foundation
- [x] M17.S01.T004 — eTIMS integration foundation
- [x] M17.S01.T005 — AI integration foundation
- [x] M17.S01.T006 — Webhook/event foundation

## M17.S02 — Provider Completion
- [!] M17.S02.T001 — M-Pesa live credentials/acceptance
- [!] M17.S02.T002 — eTIMS live credentials/acceptance
- [P] M17.S02.T003 — Replace/complete bank simulation with production connector
- [P] M17.S02.T004 — Complete physical printer execution
- [D] M17.S02.T005 — IoT/CRM/e-commerce/GraphQL stub families until prioritized

---

# M18 — Kenya Localization

**Status: PARTIAL / live-provider gates remain**

## M18.S01 — Kenya Operational Localization
- [x] M18.S01.T001 — Kenya go-live/admin documentation
- [x] M18.S01.T002 — Kenya payroll/tax-related surfaces
- [x] M18.S01.T003 — Turkey→Kenya logistics/customs workflow
- [x] M18.S01.T004 — Kenya-oriented training/manual coverage

## M18.S02 — Kenya Provider Integrations
- [x] M18.S02.T001 — KRA/eTIMS source implementation
- [x] M18.S02.T002 — M-Pesa source implementation
- [!] M18.S02.T003 — KRA/eTIMS live acceptance
- [!] M18.S02.T004 — M-Pesa live acceptance

---

# M19 — Security / Deployment / Hardening

**Status: PARTIAL**

## M19.S01 — Source Hardening Baseline
- [x] M19.S01.T001 — Production config guards
- [x] M19.S01.T002 — Restricted CORS/request timeout
- [x] M19.S01.T003 — Docker production topology
- [x] M19.S01.T004 — Redis authentication
- [x] M19.S01.T005 — Migration advisory lock
- [x] M19.S01.T006 — CI compile/import/migration/test/type-check/build coverage

## M19.S02 — Production Readiness
- [ ] M19.S02.T001 — Production-like penetration/security verification
- [ ] M19.S02.T002 — Tenant/company isolation verification
- [ ] M19.S02.T003 — Session-lifecycle remediation from M02
- [!] M19.S02.T004 — Production provider-secret deployment verification
- [D] M19.S02.T005 — Staging/live DB migration rehearsal pending environment
- [ ] M19.S02.T006 — Residual repository anomaly/dead-code cleanup

---

# M20 — Master Production Scheduling

**Status: READY / PARTIAL existing capability**
**Depends on:** M08, M09, M15; M00 complete.

## M20.S01 — MPS Domain Reconciliation
- [ ] M20.S01.T001 — Map existing MPS models/APIs/UI/services to enterprise requirements
- [ ] M20.S01.T002 — Preserve existing planning-board/capacity/campaign/what-if capabilities
- [ ] M20.S01.T003 — Identify exact missing state/data invariants
- [ ] M20.S01.T004 — Define MPS acceptance dataset and regression suite

## M20.S02 — Demand & Supply Coupling
- [ ] M20.S02.T001 — Consolidate demand inputs: sales orders/forecast/safety stock
- [ ] M20.S02.T002 — Couple MPS demand to available/on-order inventory
- [ ] M20.S02.T003 — Couple MPS to BOM/material feasibility
- [ ] M20.S02.T004 — Expose shortage/constraint reasons per planned line

## M20.S03 — Capacity & Campaign Planning
- [ ] M20.S03.T001 — Validate work-center/machine capacity calculations
- [ ] M20.S03.T002 — Harden campaign grouping/sequencing
- [ ] M20.S03.T003 — Validate changeover/CIP effects where data exists
- [ ] M20.S03.T004 — Persist capacity overload diagnostics

## M20.S04 — Approval, Release & Scenarios
- [ ] M20.S04.T001 — Harden draft→approve→release semantics
- [ ] M20.S04.T002 — Enforce permissions/audit trail on approval/release
- [ ] M20.S04.T003 — Persist what-if scenario assumptions/results
- [ ] M20.S04.T004 — Compare scenarios using service/cost/capacity KPIs

## M20.S05 — MPS Verification
- [ ] M20.S05.T001 — Backend MPS regression tests
- [ ] M20.S05.T002 — Frontend planning-board/capacity/campaign/what-if tests
- [ ] M20.S05.T003 — Cross-module MPS→MRP/production verification
- [ ] M20.S05.T004 — Close M20 with evidence and tracker update

---

# M21 — Advanced BOM / Fluid-to-Unit

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M09, M20.

## M21.S01 — Conversion Model
- [ ] M21.S01.T001 — Define bulk-fluid→pack conversion profile model
- [ ] M21.S01.T002 — Support density/UOM conversion rules
- [ ] M21.S01.T003 — Support package component quantities by SKU/size
- [ ] M21.S01.T004 — Version/effective-date conversion profiles

## M21.S02 — Yield & Loss
- [ ] M21.S02.T001 — Model expected process yield
- [ ] M21.S02.T002 — Model filling/packaging loss and spillage
- [ ] M21.S02.T003 — Separate standard vs actual yield/loss
- [ ] M21.S02.T004 — Feed variances into costing/reporting

## M21.S03 — Advanced BOM Structures
- [ ] M21.S03.T001 — Nested/intermediate BOM support verification
- [ ] M21.S03.T002 — Multi-output/co-product/by-product semantics
- [ ] M21.S03.T003 — Alternate/substitute component governance
- [ ] M21.S03.T004 — BOM explosion integrity tests

## M21.S04 — UI/API/Import
- [ ] M21.S04.T001 — Advanced BOM/conversion API contracts
- [ ] M21.S04.T002 — Conversion-profile UI
- [ ] M21.S04.T003 — CSV import/export support
- [ ] M21.S04.T004 — Permissions/audit/history

## M21.S05 — Verification
- [ ] M21.S05.T001 — Unit/conversion/yield tests
- [ ] M21.S05.T002 — MPS/MRP integration tests
- [ ] M21.S05.T003 — Costing integration tests
- [ ] M21.S05.T004 — Close M21

---

# M22 — Production Order / Work Order

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M20, M21.

## M22.S01 — Order Lifecycle
- [ ] M22.S01.T001 — Reconcile production-order vs work-order responsibilities
- [ ] M22.S01.T002 — Harden state machine and transition guards
- [ ] M22.S01.T003 — Approval/release/cancel/close semantics
- [ ] M22.S01.T004 — Immutable audit history for critical transitions

## M22.S02 — Execution Structure
- [ ] M22.S02.T001 — Routing/work-center operation sequencing
- [ ] M22.S02.T002 — Split/merge work orders
- [ ] M22.S02.T003 — Partial completion/backorder semantics
- [ ] M22.S02.T004 — Rework/reprocess flows

## M22.S03 — Subcontracting & Dependencies
- [ ] M22.S03.T001 — Subcontract operation linkage
- [ ] M22.S03.T002 — Dependency/predecessor enforcement
- [ ] M22.S03.T003 — Material/QC prerequisites before release
- [ ] M22.S03.T004 — Scheduling linkage to MPS

## M22.S04 — Verification
- [ ] M22.S04.T001 — Lifecycle/state tests
- [ ] M22.S04.T002 — Split/merge/rework tests
- [ ] M22.S04.T003 — Cross-module transaction tests
- [ ] M22.S04.T004 — Close M22

---

# M23 — Shop Floor Execution

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M22, M27 for final quality-gate closure.

## M23.S01 — Operator Workspace
- [ ] M23.S01.T001 — Harden tablet/operator execution workspace
- [ ] M23.S01.T002 — Start/pause/resume/complete operation actions
- [ ] M23.S01.T003 — Operator/shift/machine context capture
- [ ] M23.S01.T004 — Permission and role-specific action gating

## M23.S02 — Runtime Capture
- [ ] M23.S02.T001 — Actual quantity/time capture
- [ ] M23.S02.T002 — Scrap/waste/downtime capture
- [ ] M23.S02.T003 — Material consumption confirmation
- [ ] M23.S02.T004 — In-process QC checkpoints

## M23.S03 — Resilience & UX
- [ ] M23.S03.T001 — Validate responsive shop-floor UX
- [ ] M23.S03.T002 — Decide and document offline requirement
- [ ] M23.S03.T003 — Add safe retry/idempotency for execution actions
- [ ] M23.S03.T004 — Exception/escalation workflow

## M23.S04 — Verification
- [ ] M23.S04.T001 — Shop-floor API tests
- [ ] M23.S04.T002 — Operator UI/E2E tests
- [ ] M23.S04.T003 — Production/QC/inventory integration tests
- [ ] M23.S04.T004 — Close M23

---

# M24 — Material Flow

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M05, M22, M23.

## M24.S01 — Reservation & Staging
- [ ] M24.S01.T001 — Material reservation against released orders
- [ ] M24.S01.T002 — Pick-list generation
- [ ] M24.S01.T003 — Staging area/location semantics
- [ ] M24.S01.T004 — FEFO/lot recommendation enforcement

## M24.S02 — Issue / Consume / Return
- [ ] M24.S02.T001 — Material issue transaction
- [ ] M24.S02.T002 — Actual consumption transaction
- [ ] M24.S02.T003 — Excess material return
- [ ] M24.S02.T004 — Scrap/spillage material accounting

## M24.S03 — WIP & Finished Goods
- [ ] M24.S03.T001 — WIP transfer/location model
- [ ] M24.S03.T002 — Bulk/intermediate transfer
- [ ] M24.S03.T003 — Finished-goods receipt
- [ ] M24.S03.T004 — Packaging material consumption linkage

## M24.S04 — Integrity
- [ ] M24.S04.T001 — Atomic stock/production transactions
- [ ] M24.S04.T002 — Genealogy event creation
- [ ] M24.S04.T003 — Reversal/correction controls
- [ ] M24.S04.T004 — Close M24

---

# M25 — Cross-Border / Landed Cost

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M06, M13, M18.

## M25.S01 — Cross-Border Shipment Lifecycle
- [ ] M25.S01.T001 — Purchase→shipment→container linkage
- [ ] M25.S01.T002 — In-transit inventory ownership/status
- [ ] M25.S01.T003 — Customs/clearance milestone model
- [ ] M25.S01.T004 — Kenya receipt closure

## M25.S02 — Landed Cost Components
- [ ] M25.S02.T001 — Freight/insurance/customs/port/local charges
- [ ] M25.S02.T002 — Allocation methods by value/weight/volume/quantity
- [ ] M25.S02.T003 — Estimated vs actual landed cost
- [ ] M25.S02.T004 — Currency/exchange-rate handling

## M25.S03 — Accounting & Valuation
- [ ] M25.S03.T001 — Inventory valuation posting
- [ ] M25.S03.T002 — Variance/accrual posting
- [ ] M25.S03.T003 — Reconciliation and audit trail
- [ ] M25.S03.T004 — Close M25

---

# M26 — Machine & Operator Intelligence

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M11, M14, M22/M23.

## M26.S01 — Qualification Matrix
- [ ] M26.S01.T001 — Machine/operator qualification model
- [ ] M26.S01.T002 — Skill/certification expiry
- [ ] M26.S01.T003 — Enforce qualification on assignment/execution
- [ ] M26.S01.T004 — Supervisor override with audit reason

## M26.S02 — Performance Intelligence
- [ ] M26.S02.T001 — Operator productivity KPIs
- [ ] M26.S02.T002 — Machine runtime/performance KPIs
- [ ] M26.S02.T003 — Labor/machine cost attribution
- [ ] M26.S02.T004 — Shift/team comparisons

## M26.S03 — Anomaly & Feedback
- [ ] M26.S03.T001 — Detect performance anomalies
- [ ] M26.S03.T002 — Correlate downtime/quality/waste with operator/machine
- [ ] M26.S03.T003 — Feed insights to maintenance/training/planning
- [ ] M26.S03.T004 — Close M26

---

# M27 — Quality Gates

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M10; integrates with M06/M22/M23/M24/M33.

## M27.S01 — Gate Definition Engine
- [ ] M27.S01.T001 — Configurable gate types/triggers
- [ ] M27.S01.T002 — Required tests/specification linkage
- [ ] M27.S01.T003 — Gate severity/mandatory/waiver rules
- [ ] M27.S01.T004 — Version/effective-date governance

## M27.S02 — Transaction Enforcement
- [ ] M27.S02.T001 — Receiving gate
- [ ] M27.S02.T002 — Production release/in-process gate
- [ ] M27.S02.T003 — Finished-goods release gate
- [ ] M27.S02.T004 — Dispatch gate

## M27.S03 — Exceptions
- [ ] M27.S03.T001 — Hold/quarantine enforcement
- [ ] M27.S03.T002 — Deviation/waiver approval
- [ ] M27.S03.T003 — NCR/CAPA escalation linkage
- [ ] M27.S03.T004 — Gate audit history

## M27.S04 — Verification
- [ ] M27.S04.T001 — Gate-engine unit tests
- [ ] M27.S04.T002 — Cross-module blocking tests
- [ ] M27.S04.T003 — UI/E2E acceptance
- [ ] M27.S04.T004 — Close M27

---

# M28 — Full Traceability

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M21, M24, M27, M33.

## M28.S01 — Genealogy Model
- [ ] M28.S01.T001 — Raw-material lot→batch genealogy
- [ ] M28.S01.T002 — Batch→packaged SKU lot genealogy
- [ ] M28.S01.T003 — Packaging component genealogy
- [ ] M28.S01.T004 — Pallet/license-plate hierarchy linkage

## M28.S02 — Forward / Backward Trace
- [ ] M28.S02.T001 — One-click backward trace
- [ ] M28.S02.T002 — One-click forward trace
- [ ] M28.S02.T003 — Supplier/customer/shipment linkage
- [ ] M28.S02.T004 — Trace timeline/export

## M28.S03 — Recall Execution
- [ ] M28.S03.T001 — Recall scope calculation
- [ ] M28.S03.T002 — Stock/customer containment list
- [ ] M28.S03.T003 — Recall workflow/status/communications evidence
- [ ] M28.S03.T004 — Recall effectiveness metrics

## M28.S04 — Verification
- [ ] M28.S04.T001 — Genealogy integrity tests
- [ ] M28.S04.T002 — Mock recall test
- [ ] M28.S04.T003 — Performance test on deep genealogy
- [ ] M28.S04.T004 — Close M28

---

# M29 — Maintenance / OEE Upgrade

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M11, M20/M22, M26.

## M29.S01 — Maintenance Planning Integration
- [ ] M29.S01.T001 — Couple PM windows to production schedule
- [ ] M29.S01.T002 — Capacity impact of maintenance downtime
- [ ] M29.S01.T003 — Maintenance priority/escalation rules
- [ ] M29.S01.T004 — Spare-parts availability prerequisite

## M29.S02 — Calibration
- [ ] M29.S02.T001 — Calibration asset/instrument registry
- [ ] M29.S02.T002 — Calibration schedule/status
- [ ] M29.S02.T003 — Expiry blocking/quality linkage
- [ ] M29.S02.T004 — Calibration certificates/history

## M29.S03 — OEE & Predictive Loop
- [ ] M29.S03.T001 — Standardize availability/performance/quality calculation
- [ ] M29.S03.T002 — Reason-code hierarchy
- [ ] M29.S03.T003 — Predictive risk→maintenance action loop
- [ ] M29.S03.T004 — Verify OEE against production facts

## M29.S04 — Verification
- [ ] M29.S04.T001 — Maintenance scheduling tests
- [ ] M29.S04.T002 — Calibration enforcement tests
- [ ] M29.S04.T003 — OEE reconciliation tests
- [ ] M29.S04.T004 — Close M29

---

# M30 — AI Decision & Simulation

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M15, M16, operational data from M20–M29.

## M30.S01 — Governance
- [ ] M30.S01.T001 — AI decision type/risk tier registry
- [ ] M30.S01.T002 — Human approval policy by risk tier
- [ ] M30.S01.T003 — Confidence/explanation/evidence contract
- [ ] M30.S01.T004 — Provider/model/version provenance

## M30.S02 — Observe → Decide
- [ ] M30.S02.T001 — Standard observation/context payload
- [ ] M30.S02.T002 — Recommendation generation contract
- [ ] M30.S02.T003 — Constraint/policy validation
- [ ] M30.S02.T004 — Alternative recommendations

## M30.S03 — Simulate → Approve → Execute
- [ ] M30.S03.T001 — Scenario simulation contract
- [ ] M30.S03.T002 — KPI impact comparison
- [ ] M30.S03.T003 — Approval workflow
- [ ] M30.S03.T004 — Controlled execution/idempotency/rollback

## M30.S04 — Learn
- [ ] M30.S04.T001 — Outcome tracking
- [ ] M30.S04.T002 — Recommendation acceptance/rejection reasons
- [ ] M30.S04.T003 — Predicted-vs-actual KPI feedback
- [ ] M30.S04.T004 — Audit dashboard

## M30.S05 — Verification
- [ ] M30.S05.T001 — Deterministic fallback tests
- [!] M30.S05.T002 — Live-provider tests with real keys
- [ ] M30.S05.T003 — Safety/approval/rollback tests
- [ ] M30.S05.T004 — Close M30

---

# M31 — API / Event Architecture

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M01, M02, M17.

## M31.S01 — Partner API Governance
- [ ] M31.S01.T001 — API client/application registry
- [ ] M31.S01.T002 — API key/OAuth credential lifecycle
- [ ] M31.S01.T003 — Scope/rate-limit policy
- [ ] M31.S01.T004 — Partner audit/usage analytics

## M31.S02 — Event Contract
- [ ] M31.S02.T001 — Canonical domain event envelope
- [ ] M31.S02.T002 — Event versioning/schema governance
- [ ] M31.S02.T003 — Idempotency/correlation/causation IDs
- [ ] M31.S02.T004 — Transactional event creation/outbox strategy

## M31.S03 — Delivery Engine
- [ ] M31.S03.T001 — Prove always-running dispatcher
- [ ] M31.S03.T002 — Retry/backoff
- [ ] M31.S03.T003 — Dead-letter/replay
- [ ] M31.S03.T004 — Webhook signing/secret rotation

## M31.S04 — Observability & Verification
- [ ] M31.S04.T001 — Delivery metrics/logs/traces
- [ ] M31.S04.T002 — Event/API permission tests
- [ ] M31.S04.T003 — Failure/replay/idempotency tests
- [ ] M31.S04.T004 — Close M31

---

# M32 — Advanced Production Planning

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M20, M21, M22, M29, M31.

## M32.S01 — Constraint Model
- [ ] M32.S01.T001 — Machine/work-center finite capacity
- [ ] M32.S01.T002 — Tank/mixer capacity constraints
- [ ] M32.S01.T003 — Changeover/CIP constraints
- [ ] M32.S01.T004 — Labor/qualification constraints
- [ ] M32.S01.T005 — Utility/QC/material constraints

## M32.S02 — Planning Engine
- [ ] M32.S02.T001 — Finite-capacity scheduling algorithm
- [ ] M32.S02.T002 — Priority/service-level rules
- [ ] M32.S02.T003 — Freeze/slushy/free horizons
- [ ] M32.S02.T004 — Bottleneck identification

## M32.S03 — Scenario Optimization
- [ ] M32.S03.T001 — Alternative schedule generation
- [ ] M32.S03.T002 — Cost/service/OEE/changeover KPI scoring
- [ ] M32.S03.T003 — Planner comparison/approval
- [ ] M32.S03.T004 — Controlled schedule release

## M32.S04 — Verification
- [ ] M32.S04.T001 — Constraint unit tests
- [ ] M32.S04.T002 — Representative factory planning dataset
- [ ] M32.S04.T003 — Schedule KPI validation
- [ ] M32.S04.T004 — Close M32

---

# M33 — Warehouse / Inventory Enterprise Upgrade

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M05, M24, M28, M31.

## M33.S01 — License Plates & GS1
- [ ] M33.S01.T001 — License-plate/pallet/container entity
- [ ] M33.S01.T002 — GS1 barcode identifier linkage
- [ ] M33.S01.T003 — Scan-driven receive/move/pick/ship actions
- [ ] M33.S01.T004 — Parent/child handling-unit hierarchy

## M33.S02 — Allocation & Putaway
- [ ] M33.S02.T001 — Allocation/reservation rules
- [ ] M33.S02.T002 — FEFO-aware allocation
- [ ] M33.S02.T003 — Putaway strategy engine
- [ ] M33.S02.T004 — Quarantine/quality-status restrictions

## M33.S03 — Replenishment & Waves
- [ ] M33.S03.T001 — Min/max/bin replenishment
- [ ] M33.S03.T002 — Production staging replenishment
- [ ] M33.S03.T003 — Wave/batch picking
- [ ] M33.S03.T004 — Pick/pack/dispatch confirmation

## M33.S04 — Inventory Integrity
- [ ] M33.S04.T001 — Cycle-count variance approval
- [ ] M33.S04.T002 — Inventory adjustment governance
- [ ] M33.S04.T003 — Concurrency/idempotency safeguards
- [ ] M33.S04.T004 — Cross-module transaction proof

## M33.S05 — Verification
- [ ] M33.S05.T001 — WMS backend tests
- [ ] M33.S05.T002 — Scan workflow E2E tests
- [ ] M33.S05.T003 — Traceability integration tests
- [ ] M33.S05.T004 — Close M33

---

# M34 — Strategic Procurement Upgrade

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M06, M13, M25, M31.

## M34.S01 — Strategic Sourcing
- [ ] M34.S01.T001 — Tender/sourcing event model
- [ ] M34.S01.T002 — Supplier invitation/bid workflow
- [ ] M34.S01.T003 — Commercial/technical evaluation matrix
- [ ] M34.S01.T004 — Award/split-award approval

## M34.S02 — Contracts & Blanket Procurement
- [ ] M34.S02.T001 — Blanket agreement governance
- [ ] M34.S02.T002 — Price breaks/validity/commitments
- [ ] M34.S02.T003 — Release/call-off orders
- [ ] M34.S02.T004 — Contract consumption tracking

## M34.S03 — Supplier Performance
- [ ] M34.S03.T001 — OTIF/quality/price responsiveness KPIs
- [ ] M34.S03.T002 — Supplier scorecard
- [ ] M34.S03.T003 — Approved/preferred/blocked supplier governance
- [ ] M34.S03.T004 — Corrective-action linkage

## M34.S04 — Match & Cost Chain
- [ ] M34.S04.T001 — Harden PO/receipt/invoice three-way match
- [ ] M34.S04.T002 — Tolerance/exception approval
- [ ] M34.S04.T003 — Landed-cost linkage
- [ ] M34.S04.T004 — Finance posting/reconciliation

## M34.S05 — Verification
- [ ] M34.S05.T001 — Sourcing workflow tests
- [ ] M34.S05.T002 — Supplier scorecard tests
- [ ] M34.S05.T003 — Three-way-match/finance integration tests
- [ ] M34.S05.T004 — Close M34

---

# M35 — QC / QA Enterprise Upgrade

**Status: PLANNED / PARTIAL foundation**
**Depends on:** M10, M27, M28, M29, M31, M33.

## M35.S01 — Specifications & Quality Control Plans
- [ ] M35.S01.T001 — Unified specification master
- [ ] M35.S01.T002 — Product/material/process specification versions
- [ ] M35.S01.T003 — Quality Control Plan model
- [ ] M35.S01.T004 — Effective-date/change-control governance

## M35.S02 — Sampling / AQL / SPC
- [ ] M35.S02.T001 — Sampling-plan engine
- [ ] M35.S02.T002 — AQL rules
- [ ] M35.S02.T003 — SPC control-chart data model/calculations
- [ ] M35.S02.T004 — Out-of-control escalation

## M35.S03 — NCR / CAPA / Deviation
- [ ] M35.S03.T001 — NCR lifecycle
- [ ] M35.S03.T002 — CAPA root-cause/action/effectiveness lifecycle
- [ ] M35.S03.T003 — Deviation/concession workflow
- [ ] M35.S03.T004 — Quality cost/risk linkage

## M35.S04 — Laboratory & Release Evidence
- [ ] M35.S04.T001 — COA generation/approval
- [ ] M35.S04.T002 — Retain-sample registry
- [ ] M35.S04.T003 — Test-method/equipment linkage
- [ ] M35.S04.T004 — Calibration dependency enforcement

## M35.S05 — QA Governance
- [ ] M35.S05.T001 — Internal/supplier audit lifecycle
- [ ] M35.S05.T002 — Change-control workflow
- [ ] M35.S05.T003 — Training/qualification dependency enforcement
- [ ] M35.S05.T004 — Complaint/recall/CAPA integration

## M35.S06 — Verification & Program Closure
- [ ] M35.S06.T001 — QC/QA backend regression suite
- [ ] M35.S06.T002 — Quality workflow UI/E2E suite
- [ ] M35.S06.T003 — Receive→produce→release→dispatch quality-gate E2E
- [ ] M35.S06.T004 — Traceability/recall mock exercise
- [ ] M35.S06.T005 — Final M01–M35 cross-module regression
- [ ] M35.S06.T006 — Final security/deployment readiness review
- [ ] M35.S06.T007 — Close M35 and produce final project acceptance state

---

# Cross-Milestone Dependency Spine

`M01/M02/M03/M04 → M05/M06/M07/M08/M09/M10/M11/M12/M13/M14/M15/M16/M17/M18/M19 → M20 → M21 → M22 → M23 → M24 → M25/M26/M27 → M28/M29 → M30/M31 → M32 → M33/M34 → M35`

Parallel work is allowed where dependencies are satisfied, but dependency integrity takes precedence over milestone number.

# Persistent External / Runtime Gates

These are not reasons to fabricate completion and do not erase source implementation:

- [!] Live KRA/eTIMS credentials and production acceptance
- [!] Live Safaricom Daraja/M-Pesa credentials and production acceptance
- [!] Live bank connector credentials/provider acceptance
- [!] Live AI-provider acceptance where a real external model is required
- [!] Physical printer/device acceptance where hardware is required
- [D] Local staging/live-like DB rehearsal until an execution environment is available

# Historical Task Preservation

All pre-migration task evidence, including TASK-001…TASK-027, MANUAL, HELP, PUSH, LOCAL-STAGING and DATA-CLEANUP families, remains preserved in `TASKS_HISTORY.md`. Their accepted historical Done states are not silently downgraded by this roadmap. New milestone tasks describe remaining enterprise work and verification, not a denial of prior completed work.

# Definition of Done for M20–M35

A milestone is DONE only when its planned scope is implemented or explicitly superseded/deferred with rationale; backend/frontend/schema/API changes are mutually consistent; migrations are safe; RBAC/audit requirements are preserved; required tests/checks pass; no live-provider result is invented; and `TASKS.md` records the final evidence/state.
