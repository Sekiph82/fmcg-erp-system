# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

The previous canonical tracker is preserved without reinterpretation as `TASKS_HISTORY.md`. Any task marked Done in that historical tracker is accepted as Done for migration purposes. Historical details, evidence, test output, file lists, audit notes, and commit references remain available there and are referenced from this ledger by Historical Task ID.

`PLANS.md` remains architecture/strategy reference only and is not a competing task tracker.

---

## Project Status

- **Current Milestone:** M00 — Governance & Repository Baseline
- **Current Sprint:** M00.S03 — Existing-System Audit M01-M19
- **Current Task:** M00.S03.T002 — Audit M02 Authentication / RBAC
- **Current Task Status:** READY
- **Next Task/Action:** Audit M02 Authentication / RBAC against backend/frontend/current tests and classify completeness without reopening accepted historical Done work.
- **Required Actor:** AUDITOR
- **Tracking Repository:** Sekiph82/fmcg-erp-system
- **Tracking Branch:** main
- **Enhancement Gate:** M20-M35 implementation is locked until M00 reconciliation and the strict pre-enhancement audit are complete.

## Status Legend

- `[x]` DONE — accepted complete, including Done states migrated from `TASKS_HISTORY.md`
- `[~]` IN_PROGRESS — active work
- `[ ]` PLANNED — planned but not started
- `[!]` BLOCKED — waiting on dependency, credential, external system, decision, or owner action
- `[-]` SUPERSEDED — preserved history replaced by later work
- `[A]` AUDIT_REQUIRED — current implementation must be determined by M00
- `[P]` PARTIAL — implementation exists but known scope remains
- `[D]` DEFERRED — deliberately postponed, not technically blocked

## Reconciliation Classification

M00 uses these classifications when comparing M01-M35 with the repository:

- `ALREADY_DONE`
- `PARTIAL`
- `MISSING`
- `SUPERSEDED`
- `NOT_APPLICABLE`

No M20-M35 capability may be assumed missing merely because it appears in the enhancement roadmap.

## Canonical Tracking Rules

1. `TASKS.md` is the only active project-status ledger.
2. `TASKS_HISTORY.md` is immutable historical/reference evidence, not a competing current tracker.
3. Existing historical tasks are never deleted. Their historical IDs remain traceable here.
4. If `TASKS_HISTORY.md` says Done, migration accepts Done.
5. Manual, Help, Push/Checkpoint, Local Staging, Data Cleanup, blocked credential/vendor, and nested task families must be preserved.
6. M00 compares actual repository implementation, historical task state, `PLANS.md`, and M01-M35 before defining remaining work.
7. M20-M35 are provisional enhancement scopes until M00.S04 reconciliation.
8. M00.S05 is the strict audit gate before new enhancement implementation.
9. P0/P1 findings from M00.S05 must be triaged before M00 can close.
10. Every meaningful task/audit/remediation/acceptance state change updates this file.
11. Do not create another TODO/STATUS/PROGRESS tracker.
12. Detailed historical evidence stays in `TASKS_HISTORY.md`; this file carries current state, mapping, dependencies, and actionable roadmap.

---

# Milestone Map

## Existing-System / Baseline Milestones

- **M00** Governance & Repository Baseline
- **M01** Platform / Infrastructure
- **M02** Authentication / RBAC
- **M03** Master Data
- **M04** Product / Material / Supplier Master
- **M05** Warehouse & Inventory
- **M06** Procurement
- **M07** Sales / Distributor Operations
- **M08** Production Core
- **M09** Recipes / BOM
- **M10** Quality
- **M11** Maintenance
- **M12** Utilities
- **M13** Finance / Costing
- **M14** HR / Operator / Shift
- **M15** Reporting / Analytics
- **M16** AI
- **M17** Integrations
- **M18** Kenya Localization
- **M19** Security / Deployment / Hardening

## Enterprise Enhancement Milestones — Provisional Until M00 Reconciliation

- **M20** Master Production Scheduling
- **M21** Advanced BOM / Fluid-to-Unit
- **M22** Production Order / Work Order
- **M23** Shop Floor Execution
- **M24** Material Flow
- **M25** Cross-Border / Landed Cost
- **M26** Machine & Operator Intelligence
- **M27** Quality Gates
- **M28** Full Traceability
- **M29** Maintenance / OEE Upgrade
- **M30** AI Decision & Simulation
- **M31** API / Event Architecture
- **M32** Advanced Production Planning
- **M33** Warehouse / Inventory Enterprise Upgrade
- **M34** Strategic Procurement Upgrade
- **M35** QC / QA Enterprise Upgrade

---

# M00 — Governance & Repository Baseline

**Status:** IN_PROGRESS

M00 is the mandatory truth-reconciliation milestone. It preserves historical accepted state, inventories the real codebase, identifies capabilities that already satisfy later enhancement prompts, performs the strict pre-enhancement audit, and regenerates this roadmap from evidence.

## M00.S01 — Canonical Tracker Migration & Historical Reclassification

- [x] **M00.S01.T001 — Preserve previous canonical tracker as `TASKS_HISTORY.md`**
- [x] **M00.S01.T002 — Establish new root `TASKS.md` as canonical H!veAI ledger**
- [x] **M00.S01.T003 — Establish repository/current-plan comparison framework**
- [x] **M00.S01.T004 — Inventory and migrate TASK-001 through TASK-027 including nested sub-tasks**
- [x] **M00.S01.T005 — Migrate Manual, Help, Push, Local Staging, Data Cleanup, blocked/manual-dependency task families**

### M00 Historical Governance / Documentation Tasks

- [x] **M00.S01.H001 — Repository Graphify output cleanup**  
  Historical Task ID: `TASK-010` · Historical status: Done.
- [x] **M00.S01.H002 — Full ERP Reference Manual PDF generation script**  
  Historical Task ID: `TASK-018` · Historical status: Done.
- [x] **M00.S01.H003 — Manual asset audit** · Historical Task ID: `MANUAL-001` · Done.
- [x] **M00.S01.H004 — Capture refreshed screenshots** · Historical Task ID: `MANUAL-002` · Done.
- [x] **M00.S01.H005 — Rewrite changed module manuals** · Historical Task ID: `MANUAL-003` · Done.
- [x] **M00.S01.H006 — Update technical/admin manuals** · Historical Task ID: `MANUAL-004` · Done.
- [x] **M00.S01.H007 — Validate links/screenshots/markdown** · Historical Task ID: `MANUAL-005` · Done.
- [x] **M00.S01.H008 — Regenerate affected PDF bundles** · Historical Task ID: `MANUAL-006` · Done.

## M00.S02 — Repository Capability Inventory

- [x] **M00.S02.T001 — Backend architecture and module inventory**
  - FastAPI + centralized API router + dynamic module registry.
  - Layers: API/core/CRUD/DB/models/prompts/schemas/services.
  - Async SQLAlchemy + Alembic; automatic table creation disabled.
  - Health/readiness/metrics/security/input/request middleware exists.
  - Broad enterprise module registry and scoped permission architecture exists.
  - Seed layers include auth/admin, structural finance, production, inventory and utilities.
  - Enterprise migrations include accounting, APS planning, WMS reconciliation and procurement governance.
  - Anomaly for M19 audit: classify `backend/=2.9.0` before cleanup.

- [x] **M00.S02.T002 — Frontend routes/pages/components inventory**
  - Next.js App Router with shared shell/navigation/auth/context/hooks/lib architecture.
  - 33 consolidated workspaces in 9 cluster groups; legacy routes redirect to workspace/tab destinations while standalone operational pages are preserved.
  - Shared permission-aware API/client/auth patterns exist.
  - Existing UI surfaces already expose substantial M20-M35 capabilities including MPS/MRP/capacity/simulation, production execution, machine operators, material flow, landed cost, supplier portal, conversion profiles, CAPA/COA and enterprise inventory functions.

- [x] **M00.S02.T003 — Database models/migrations/schema inventory**
  - Large model registry covers baseline ERP plus MPS, APS planning, execution/shop floor, machine/operator intelligence, traceability/recall, landed cost, FEFO/shelf-life, quality/QMS and other enhancement domains.
  - Schema presence is inventory evidence only; drift, ownership, constraints, indexes and referential integrity remain strict-audit work.

- [x] **M00.S02.T004 — API/router/service inventory**
  - Dedicated endpoints/services exist for MPS, MRP, planning, production execution, shop floor, material flow, machine/operator, traceability, landed cost, procurement suggestions, subcontracting, supplier portal, invoice matching, QMS, WMS, shelf life and many more domains.
  - Presence is not completion proof; S03/S04 validate semantics and workflow completeness.

- [x] **M00.S02.T005 — Jobs/queues/schedulers/websocket/event mechanisms inventory**
  - Persistent webhook/event engine has event log, subscriptions, delivery attempts, transforms, auth, exponential retry, dead-letter and replay/process functions.
  - Automatic dispatch worker/scheduler invocation path remains audit-required; no always-running Celery/APScheduler/WebSocket worker was established during inventory.

- [x] **M00.S02.T006 — CSV/import/export/reporting infrastructure inventory**
  - Central bulk import lifecycle supports CSV template download, validate-only, full import, import history and error CSV.
  - Adapter architecture covers products/materials/suppliers/warehouses/employees/inventory/recipes/BOM items and utilities.
  - Report-builder/analytics/dashboard infrastructure exists.
  - Strict audit must actually execute template/download/validation/import/error paths.

- [x] **M00.S02.T007 — Integration provider/capability inventory**
  - Central capability registry distinguishes production/sandbox/simulated/stub states.
  - M-Pesa, WhatsApp, eTIMS, AI and webhooks have substantive implementations with external/live blockers.
  - IoT, CRM, e-commerce and GraphQL remain stub-only; bank API simulated-only; physical printer execution remains stub-only.

- [x] **M00.S02.T008 — Tests/CI/Docker/deployment/environment inventory**
  - GitHub Actions runs backend dependency audit/compile/import/migrations/single-head/pytest; frontend dependency audit/type-check/build; dev/prod Docker config validation.
  - Backend focused module/GAP/security tests and frontend Playwright E2E suites exist.
  - Dev/prod compose define Postgres/Redis/backend/frontend health checks; prod keeps DB/Redis unexposed and enables Redis AUTH.

- [x] **M00.S02.T009 — Documentation/reference inventory**
  - Strategic `PLANS.md`, engineering audits/reviews, detailed GAP audit/design/implementation notes, deployment/QA docs and extensive screenshot/manual/PDF pipelines exist.
  - Documentation is supporting evidence only; current source/tests/migrations take precedence.

## M00.S03 — Existing-System Audit M01-M19

- [x] **M00.S03.T001 — Audit M01 Platform / Infrastructure**
  - **Classification: PARTIAL.** Core platform architecture is substantially implemented and production-oriented, but bounded platform gaps remain.
  - **ALREADY_DONE evidence:** FastAPI modular registry/router architecture; async DB/Alembic discipline; dev/prod Docker topology; CI pipeline; health/readiness/metrics; centralized configuration with strong production guards; Next.js workspace/shell architecture; centralized API client/auth context; generic approval workflow; custom-field/value/validation/form-layout/workflow-rule subsystem; chatter/activity timeline with comments/attachments/SLA; report/import infrastructure; contextual in-app help.
  - Generic approval engine accepts arbitrary ERP module/object references, supports amount/currency, multi-step approval actions and overdue escalation.
  - Custom Fields subsystem supports definitions, values, validation, layout ordering and workflow rules, with associated service layer.
  - Chatter subsystem supports paginated activities/timeline, comments, attachments, SLA views and AI recommendation helpers.
  - **PARTIAL evidence:** Document/KB/e-sign hardening historical task remains partial because binary file-storage adapter/upload pipeline is not resolved and migration ownership still needs live-DB verification; generic event delivery engine exists but always-running scheduler/worker invocation is not yet proven; local staging environment remains deliberately deferred.
  - Plugin/module-lifecycle concepts appear historically in architecture/model references but were not sufficiently proven during this audit to claim a complete dependency-aware plugin marketplace/lifecycle. Revisit in strict architecture audit rather than creating new implementation now.
  - **No remediation implemented during M01 audit.** Existing working platform code remains untouched. Partial items stay as bounded existing tasks/audit targets rather than reopening completed infrastructure.

- [ ] M00.S03.T002 — Audit M02 Authentication / RBAC
- [ ] M00.S03.T003 — Audit M03 Master Data
- [ ] M00.S03.T004 — Audit M04 Product / Material / Supplier Master
- [ ] M00.S03.T005 — Audit M05 Warehouse & Inventory
- [ ] M00.S03.T006 — Audit M06 Procurement
- [ ] M00.S03.T007 — Audit M07 Sales / Distributor Operations
- [ ] M00.S03.T008 — Audit M08 Production Core
- [ ] M00.S03.T009 — Audit M09 Recipes / BOM
- [ ] M00.S03.T010 — Audit M10 Quality
- [ ] M00.S03.T011 — Audit M11 Maintenance
- [ ] M00.S03.T012 — Audit M12 Utilities
- [ ] M00.S03.T013 — Audit M13 Finance / Costing
- [ ] M00.S03.T014 — Audit M14 HR / Operator / Shift
- [ ] M00.S03.T015 — Audit M15 Reporting / Analytics
- [ ] M00.S03.T016 — Audit M16 AI
- [ ] M00.S03.T017 — Audit M17 Integrations
- [ ] M00.S03.T018 — Audit M18 Kenya Localization
- [ ] M00.S03.T019 — Audit M19 Security / Deployment / Hardening

## M00.S04 — M20-M35 Existing-vs-Planned Reconciliation

Every capability receives `ALREADY_DONE`, `PARTIAL`, `MISSING`, `SUPERSEDED`, or `NOT_APPLICABLE` with source evidence.

- [ ] M00.S04.T001 — Reconcile M20 Master Production Scheduling
- [ ] M00.S04.T002 — Reconcile M21 Advanced BOM / Fluid-to-Unit
- [ ] M00.S04.T003 — Reconcile M22 Production Order / Work Order
- [ ] M00.S04.T004 — Reconcile M23 Shop Floor Execution
- [ ] M00.S04.T005 — Reconcile M24 Material Flow
- [ ] M00.S04.T006 — Reconcile M25 Cross-Border / Landed Cost
- [ ] M00.S04.T007 — Reconcile M26 Machine & Operator Intelligence
- [ ] M00.S04.T008 — Reconcile M27 Quality Gates
- [ ] M00.S04.T009 — Reconcile M28 Full Traceability
- [ ] M00.S04.T010 — Reconcile M29 Maintenance / OEE Upgrade
- [ ] M00.S04.T011 — Reconcile M30 AI Decision & Simulation
- [ ] M00.S04.T012 — Reconcile M31 API / Event Architecture
- [ ] M00.S04.T013 — Reconcile M32 Advanced Production Planning
- [ ] M00.S04.T014 — Reconcile M33 Warehouse / Inventory Enterprise Upgrade
- [ ] M00.S04.T015 — Reconcile M34 Strategic Procurement Upgrade
- [ ] M00.S04.T016 — Reconcile M35 QC / QA Enterprise Upgrade

## M00.S05 — Strict Pre-Enhancement Full System Audit

- [ ] M00.S05.T001 — Full backend architecture audit
- [ ] M00.S05.T002 — Full frontend architecture audit
- [ ] M00.S05.T003 — Database/schema/migration integrity audit
- [ ] M00.S05.T004 — API contracts/routes/service-boundary audit
- [ ] M00.S05.T005 — Authentication/RBAC/security audit
- [ ] M00.S05.T006 — Master-data integrity audit
- [ ] M00.S05.T007 — Warehouse/inventory transaction-integrity audit
- [ ] M00.S05.T008 — Procurement workflow audit
- [ ] M00.S05.T009 — Sales/distributor/order-to-cash audit
- [ ] M00.S05.T010 — Production/BOM/planning/execution audit
- [ ] M00.S05.T011 — QC/QA/traceability audit
- [ ] M00.S05.T012 — Maintenance/utilities/asset integration audit
- [ ] M00.S05.T013 — Finance/costing/accounting audit
- [ ] M00.S05.T014 — HR/operator/shift/payroll integration audit
- [ ] M00.S05.T015 — AI grounding/safety/explainability/execution audit
- [ ] M00.S05.T016 — External integrations/provider-readiness audit
- [ ] M00.S05.T017 — Kenya localization/eTIMS/M-Pesa/statutory-readiness audit
- [ ] M00.S05.T018 — Cross-module data-flow/referential-integrity audit
- [ ] M00.S05.T019 — Import/export/CSV/data-cleanup audit
- [ ] M00.S05.T020 — Performance/scalability/background-job audit
- [ ] M00.S05.T021 — Deployment/Docker/CI/observability audit
- [ ] M00.S05.T022 — Full tests/build/runtime verification
- [ ] M00.S05.T023 — Consolidated P0/P1/P2/P3 findings register

## M00.S06 — Canonical Roadmap Regeneration

- [ ] M00.S06.T001 — Merge M01-M19 audit results into current task state
- [ ] M00.S06.T002 — Mark M20-M35 capabilities already implemented as ALREADY_DONE
- [ ] M00.S06.T003 — Convert partial capabilities into bounded upgrade/remediation tasks
- [ ] M00.S06.T004 — Mark duplicate future work SUPERSEDED without deleting history
- [ ] M00.S06.T005 — Add missing work discovered by strict audit
- [ ] M00.S06.T006 — Recalculate dependencies and milestone ordering
- [ ] M00.S06.T007 — Recalculate milestone progress from reconciled states
- [ ] M00.S06.T008 — Set evidence-based current milestone/sprint/task
- [ ] M00.S06.T009 — Owner review of regenerated roadmap
- [ ] M00.S06.T010 — Close M00 gate and authorize first post-audit implementation

### M00 Exit Criteria

M00 closes only after historical mapping, M01-M19 audit, M20-M35 comparison, strict full audit, P0/P1 triage, canonical roadmap regeneration and owner acceptance.

---

# M01 — Platform / Infrastructure

**M00 audit classification: PARTIAL.** The foundational platform is mature and should not be rewritten. Remaining work is bounded to existing document-storage/migration-verification, runtime scheduler/worker verification and deferred staging/lifecycle questions.

## M01.S01 — Platform UX and Enterprise Support Services

- [x] **M01.S01.T001 — Login page POVU logo size** · Historical Task ID: `TASK-001` · Done.
- [P] **M01.S01.T002 — Document Management / Knowledge Base / E-Sign hardening** · Historical Task ID: `TASK-027`  
  Completed permission hardening/tests; remaining service extraction is deferred, migration ownership needs live DB, binary storage pipeline needs adapter decision.
- [x] **M01.S01.T003 — Contextual question-mark help popovers** · Historical Task ID: `HELP-001` · Done.
- [x] **M01.S01.T004 — Recapture screenshots/manual notes after help popovers** · Historical Task ID: `HELP-002` · Done.
- [P] **M01.S02.T001 — Platform runtime/event execution verification**  
  Webhook/event persistence/retry/dead-letter exists; strict audit must verify the production scheduler/worker/invocation mechanism rather than introduce a duplicate queue system.
- [D] **M01.S02.T002 — Local staging platform** · Historical Task ID: `LOCAL-STAGING-001`  
  Deferred; reconsider after strict deployment audit.

---

# M02 — Authentication / RBAC

## M02.S01 — Identity, Credentials and 2FA

- [x] **M02.S01.T001 — E2E/admin credentials audit + management-user environment strategy** · Historical Task ID: `TASK-007` · Done.
- [!] **M02.S01.T002 — SMTP + email OTP live end-to-end verification** · Historical Task ID: `TASK-012` · Blocked on real SMTP credentials/live staging test.

---

# M03 — Master Data

- [A] M03.S00.T001 — Reconcile existing master-data capabilities during M00 audit

---

# M04 — Product / Material / Supplier Master

- [!] **M04.S01.T001 — GS1 GTIN coverage / product master completeness** · Historical Task ID: `TASK-019` · Blocked on GS1 prefix/GTIN assignments.
- [A] M04.S00.T002 — Audit material and supplier-master completeness under M00.S03.T004

---

# M05 — Warehouse & Inventory

- [x] **M05.S01.T001 — Inventory/Stock real data Phase I1-I7** · Historical Task ID: `TASK-016` · Done for historical seed scope: lots/stocks/movements/cost layers, WMS zones/locations, trace events, cycle count, shelf life, forecasts and MRP.
- [A] M05.S02.T001 — Audit transactional warehouse/inventory completeness during M00.S03.T005

---

# M06 — Procurement

- [A] M06.S00.T001 — Audit procurement baseline, RFQ/supplier/approval/replenishment functionality during M00.S03.T006

---

# M07 — Sales / Distributor Operations

- [A] M07.S00.T001 — Audit Sales / Distributor Operations during M00.S03.T007

---

# M08 — Production Core

- [x] **M08.S01.T001 — Production module real data Phase P1-P11** · Historical Task ID: `TASK-015` · Done for historical seed scope including work centers/routings, plans/orders/work orders/batches and OEE/QC/waste/downtime seed.
- [A] M08.S02.T001 — Audit production lifecycle and execution completeness during M00.S03.T008

---

# M09 — Recipes / BOM

- [A] M09.S00.T001 — Audit current Recipe/BOM implementation during M00.S03.T009

---

# M10 — Quality

- [A] M10.S00.T001 — Audit current quality/QMS implementation during M00.S03.T010

---

# M11 — Maintenance

- [A] M11.S00.T001 — Audit Maintenance baseline during M00.S03.T011

---

# M12 — Utilities

- [x] **M12.S01.T001 — Utilities module real factory seed data foundation** · Historical Task ID: `TASK-009` · Done.
- [A] M12.S02.T001 — Audit utility module functional completeness/cross-module integration

---

# M13 — Finance / Costing

- [P] **M13.S01.T001 — Finance cost allocation engine Phase F4-F6** · Historical Task ID: `TASK-017`  
  Completed historical finance seed/posting work; remaining GL allocation mapping, profitability definition/API and dependent frontend remain bounded/blocked.
- [A] M13.S02.T001 — Audit accounting/costing completeness during M00.S03.T013

---

# M14 — HR / Operator / Shift

- [A] M14.S00.T001 — Audit HR/operator/shift baseline during M00.S03.T014

---

# M15 — Reporting / Analytics

- [A] M15.S00.T001 — Audit reporting/analytics baseline during M00.S03.T015

---

# M16 — AI

- [!] **M16.S01.T001 — Enable AI live mode** · Historical Task ID: `TASK-002` · Blocked on provider key/live configuration.
- [x] **M16.S01.T002 — Demand forecasting upgrade using local Holt-Winters** · Historical Task ID: `TASK-025` · Done.
- [A] M16.S02.T001 — Audit remaining prediction/recommendation/optimization/agent capability during M00.S03.T016

---

# M17 — Integrations

- [!] **M17.S01.T001 — WhatsApp production validation** · Historical Task ID: `TASK-004` · Blocked on Meta credentials/live test.
- [!] **M17.S01.T002 — CRM real integration** · `TASK-020` · Blocked on vendor/credentials.
- [!] **M17.S01.T003 — E-commerce real integration** · `TASK-021` · Blocked on platform/credentials.
- [!] **M17.S01.T004 — IoT/Machine MQTT integration** · `TASK-022` · Blocked on hardware/broker/schema.
- [!] **M17.S01.T005 — Bank API sync** · `TASK-023` · Blocked on bank agreement/credentials.
- [!] **M17.S01.T006 — Label printer SDK integration** · `TASK-024` · Blocked on printer/connectivity.
- [A] M17.S02.T001 — Audit all integration capabilities/simulation-live boundaries

---

# M18 — Kenya Localization

- [!] **M18.S01.T001 — Wire M-Pesa production credentials** · Historical Task ID: `TASK-003` · Daraja/delegation implemented historically; blocked on credentials/live test.
- [P] **M18.S02.T001 — eTIMS live integration** · Historical Task ID: `TASK-005`  
  Provider config/models/connector/workflow/frontend monitoring/invoice card/UX/nav historical scope complete; finance posting policy and live provider remain blocked.
- [A] M18.S03.T001 — Audit broader Kenya statutory/localization coverage

---

# M19 — Security / Deployment / Hardening

- [x] **M19.S01.T001 — GS1 route authorization guards** · `TASK-006` · Done.
- [x] **M19.S01.T002 — ERP health audit/remediation** · `TASK-008` · Done; historical 0 HIGH with accepted/documented MEDIUM backlog.
- [x] **M19.S01.T003 — Redis AUTH production** · `TASK-011` · Done.
- [x] **M19.S01.T004 — python-jose → PyJWT** · `TASK-014` · Done.
- [x] **M19.S02.T001 — Playwright smoke rerun** · `TASK-013` · Done, historical 56/56.
- [x] **M19.S02.T002 — Multi-replica migration safety** · `TASK-026` · Done.
- [x] **M19.S02.T003 — GitHub push/deployment-readiness checkpoint** · `PUSH-001` · Done.
- [D] **M19.S02.T004 — Local Docker Compose staging** · `LOCAL-STAGING-001` · Deferred.
- [x] **M19.S02.T005 — Demo seed-data gate audit** · `DATA-CLEANUP-001` · Done.
- [A] M19.S03.T001 — Strict current security/deployment/hardening audit

---

# M20-M35 — Provisional Enhancement Scope Pending M00 Reconciliation

These are NOT automatically new implementation milestones. Repository inventory proves many already have models, APIs, services and frontend surfaces. M00.S04 must classify each intended capability before work is created.

# M20 — Master Production Scheduling
**Status:** AUDIT_REQUIRED. Evidence: Demand Forecast/MRP + MPS model family + `mps` API + Planning workspace MPS.
- [A] M20.S00.T001 — Compare full MPS prompt with current MPS/MRP/forecast/service/UI

# M21 — Advanced BOM / Fluid-to-Unit
**Status:** AUDIT_REQUIRED. Evidence: AdvancedBOM/lines/substitutes/yield/conversion profiles, BOM workspace and BOM-item bulk import.
- [A] M21.S00.T001 — Compare multi-level/bulk-to-unit/yield/loss/packaging/substitution/versioning scope

# M22 — Production Order / Work Order
**Status:** AUDIT_REQUIRED. Evidence: ProductionOrder/WorkOrder/WorkCenter/Routing/Plan/Batch + execution APIs/UI.
- [A] M22.S00.T001 — Classify planned production/work-order capabilities

# M23 — Shop Floor Execution
**Status:** AUDIT_REQUIRED. Evidence: SFSession/activity/downtime/handover/supervisor models + `shop_floor` API + execution UI.
- [A] M23.S00.T001 — Reconcile operator/shop-floor execution scope

# M24 — Material Flow
**Status:** AUDIT_REQUIRED. Evidence: material/inventory movement models + `material_flow` API/UI; full accounting-linked consumption/receipt path needs validation.
- [A] M24.S00.T001 — Audit issue/consume/return/WIP/bulk-to-pack behavior

# M25 — Cross-Border / Landed Cost
**Status:** AUDIT_REQUIRED. Evidence: landed-cost models/API/UI + international shipment/container/customs/clearance models.
- [A] M25.S00.T001 — Audit import/in-transit/customs/freight/insurance/allocation/posting behavior

# M26 — Machine & Operator Intelligence
**Status:** AUDIT_REQUIRED. Evidence: machine/operator/team/skill/cert/assignment/runtime/labor/performance/downtime models + API/UI; IoT live bridge stub.
- [A] M26.S00.T001 — Compare machine/operator intelligence scope

# M27 — Quality Gates
**Status:** AUDIT_REQUIRED. Evidence: inspections/results/templates/sampling/HACCP/CCP/corrective action/deviation/release/lot quality + Quality/QMS APIs/UI.
- [A] M27.S00.T001 — Determine operational QC block/release completeness

# M28 — Full Traceability
**Status:** AUDIT_REQUIRED. Evidence: TraceEvent/Line, LotGenealogyLink, recall family, BatchGenealogy, `traceability` API/UI.
- [A] M28.S00.T001 — Compare forward/backward genealogy/recall/customer-impact scope

# M29 — Maintenance / OEE Upgrade
**Status:** AUDIT_REQUIRED. Evidence: maintenance asset/PM/WO/breakdown/spares + OEE/downtime/waste + historical predictive-maintenance GAP.
- [A] M29.S00.T001 — Reconcile maintenance/OEE/calibration/predictive scope

# M30 — AI Decision & Simulation
**Status:** AUDIT_REQUIRED. Evidence: provider/runtime + production predictions/anomalies/suggestions/metrics + planning simulations + MPS what-if + cross-module AI recommendations.
- [A] M30.S00.T001 — Audit prediction/anomaly/recommendation/scenario/decision/simulation architecture

# M31 — API / Event Architecture
**Status:** AUDIT_REQUIRED. Evidence: broad REST, persistent webhook event/subscription/delivery/retry/DLQ/replay; worker path unproven; GraphQL stub-only.
- [A] M31.S00.T001 — Audit API/event/idempotency/retry/worker/security/GraphQL need

# M32 — Advanced Production Planning
**Status:** AUDIT_REQUIRED. Evidence: PlanningScenario/Calendar/Queue/Capacity/Changeover/Bottleneck/AI/Simulation + APS migration + API + MRP/MPS/Kanban/Capacity/Simulation UI.
- [A] M32.S00.T001 — Compare shift/day/week/month/machine/order/section/campaign/finite-capacity planning

# M33 — Warehouse / Inventory Enterprise Upgrade
**Status:** AUDIT_REQUIRED. Evidence: WMS/stock/lot/movement/cost/cycle/FEFO/trace/serial + APIs + Picking/Putaway/Replenishment + WMS migration.
- [A] M33.S00.T001 — Compare enterprise WMS/inventory/FEFO/reservation/picking/quarantine/in-transit/valuation scope

# M34 — Strategic Procurement Upgrade
**Status:** AUDIT_REQUIRED. Evidence: PR/PO/GRN/import/supplier evaluation/payment + procurement/quotation/supplier portal/subcontracting/suggestions/invoice-match + governance migration.
- [A] M34.S00.T001 — Compare RFQ/tender/quotation/PO/contract/scorecard/import/subcontracting scope

# M35 — QC / QA Enterprise Upgrade
**Status:** AUDIT_REQUIRED. Evidence: QC/QMS inspection/template/sampling/HACCP/corrective/deviation/release/lot/allergen models + APIs + CAPA/COA/complaints UI.
- [A] M35.S00.T001 — Compare specification/QCP/check/release/NCR/CAPA/review/supplier-quality scope

---

# Active Blockers / Human Decisions Carried Forward

- AI provider API key (`TASK-002`)
- Safaricom Daraja credentials (`TASK-003`)
- Meta WhatsApp credentials (`TASK-004`)
- eTIMS accountant fiscalization policy (`TASK-005.1D`)
- eTIMS provider/KRA credentials/spec (`TASK-005.1E`)
- SMTP credentials/live OTP (`TASK-012`)
- Utility allocation GL mapping (`TASK-017.3`)
- Product profitability revenue definition (`TASK-017.4`)
- GS1 prefix/GTIN assignments (`TASK-019`)
- CRM vendor/credentials (`TASK-020`)
- E-commerce platform/credentials (`TASK-021`)
- MQTT hardware/broker/topic schema (`TASK-022`)
- Bank API agreement/credentials (`TASK-023`)
- Printer model/connectivity (`TASK-024`)
- Document storage adapter (`TASK-027`)
- Live document/KB/e-sign migration ownership verification needs Docker/dev DB (`TASK-027`)

M00 audit may prove blockers obsolete/superseded/resolved. Until then they remain carried-forward state.

---

# Historical Migration Coverage

- `TASK-001` through `TASK-027`: mapped into M00-M19; detailed original cards remain in `TASKS_HISTORY.md`.
- `MANUAL-001` through `MANUAL-006`: M00 historical documentation tasks; Done.
- `HELP-001/002`: M01; Done.
- `PUSH-001`: M19; Done.
- `LOCAL-STAGING-001`: M01/M19 platform/deployment dependency; Deferred.
- `DATA-CLEANUP-001`: M19; Done.

Nested historical IDs remain valid evidence references even when canonical IDs differ.

---

# Next Execution Gate

**Do not implement M20-M35 yet.**

M00.S02 repository inventory is complete and M01 Platform / Infrastructure has been classified `PARTIAL` without changing source code. Next is M00.S03.T002 Authentication / RBAC, followed sequentially through M19. M00.S04 then reconciles M20-M35. Only after M00.S05 strict full audit and M00.S06 roadmap regeneration may post-audit implementation begin.