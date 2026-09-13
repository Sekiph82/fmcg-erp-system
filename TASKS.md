# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

The previous canonical tracker is preserved without reinterpretation as `TASKS_HISTORY.md`. Any task marked Done in that historical tracker is accepted as Done for migration purposes. Historical details, evidence, test output, file lists, audit notes, and commit references remain available there and are referenced from this ledger by Historical Task ID.

`PLANS.md` remains architecture/strategy reference only and is not a competing task tracker.

---

## Project Status

- **Current Milestone:** M00 — Governance & Repository Baseline
- **Current Sprint:** M00.S03 — Existing-System Audit M01-M19
- **Current Task:** M00.S03.T001 — Audit M01 Platform / Infrastructure
- **Current Task Status:** READY
- **Next Task/Action:** Audit M01 Platform / Infrastructure against current repository evidence, classify capability completeness, then continue sequentially through M19 before M20-M35 reconciliation.
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
  Historical Task ID: `TASK-010`  
  Historical status: Done. Generated `graphify-out/` artifacts removed from Git tracking and ignored while external architecture maps were retained.

- [x] **M00.S01.H002 — Full ERP Reference Manual PDF generation script**  
  Historical Task ID: `TASK-018`  
  Historical status: Done. Full-reference PDF generator exists and is usable.

- [x] **M00.S01.H003 — Manual asset audit**  
  Historical Task ID: `MANUAL-001`  
  Historical status: Done. Manuals, PDFs and screenshot assets audited; changed modules identified.

- [x] **M00.S01.H004 — Capture refreshed screenshots for changed modules**  
  Historical Task ID: `MANUAL-002`  
  Historical status: Done. 17/17 targeted routes captured with existing assets preserved.

- [x] **M00.S01.H005 — Rewrite changed module manuals**  
  Historical Task ID: `MANUAL-003`  
  Historical status: Done. eTIMS, inventory/WMS, QC/OEE, AI, security/admin and related reference sections updated.

- [x] **M00.S01.H006 — Update technical/admin manuals**  
  Historical Task ID: `MANUAL-004`  
  Historical status: Done. Administration manual updated for eTIMS simulation, management users, PyJWT, GS1 auth and advisory-lock behavior.

- [x] **M00.S01.H007 — Validate links, screenshots and markdown**  
  Historical Task ID: `MANUAL-005`  
  Historical status: Done.

- [x] **M00.S01.H008 — Regenerate affected PDF bundles**  
  Historical Task ID: `MANUAL-006`  
  Historical status: Done. Full Reference, Kenya Go-Live, Manufacturing and Supply Chain bundles regenerated locally.

## M00.S02 — Repository Capability Inventory

- [x] **M00.S02.T001 — Backend architecture and module inventory**
  - Evidence inspected: `backend/`, `backend/app/`, `backend/app/main.py`, `backend/app/core/`, `backend/app/core/module_registry.py`, `backend/app/models/`, `backend/app/services/`, `backend/app/api/v1/endpoints/`, `backend/app/db/`, and `backend/alembic/versions/`.
  - Backend framework: FastAPI application with centralized API router and dynamic module/endpoint registration through `module_registry.py`.
  - Main application layers identified: `api`, `core`, `crud`, `db`, `models`, `prompts`, `schemas`, `services`.
  - Runtime infrastructure identified: CORS, GZip, security headers, input sanitization, request timeout handling, request IDs, logging/error tracking, request metrics, `/live`, `/ready`, `/health`, and `/metrics` endpoints.
  - Persistence architecture: asynchronous SQLAlchemy sessions + PostgreSQL-oriented Alembic migrations. `main.py` explicitly disables automatic table creation and requires Alembic for schema changes.
  - Seed layers identified: authorization/admin/roles (`seed.py`), structural finance (`seed_finance.py`), production demo (`seed_production.py`), inventory demo (`seed_inventory.py`), standalone utilities (`seed_utilities.py`).
  - Module registry confirms substantial existing domain coverage including Users/Roles, Inventory, Production, Advanced Planning, NPD, Advanced BOM/Formula, Recipes, Procurement, Sales, CRM, Finance, HR, Kenya Payroll, Quality, Consumer Complaints, GS1, Maintenance, Utilities, Report Builder, Notifications, Documents, Knowledge Base, E-Sign, AI, Shelf-Life/FEFO, IoT/Machine Streaming, and Company/Branches.
  - Permission architecture supports standard and scoped variants including company/branch/warehouse/factory/line/department/region/category scope.
  - Alembic history already contains enterprise migrations for accounting core/operational posting/access scopes, APS planning, WMS depth reconciliation and procurement governance.
  - Preliminary conclusion: this is already a broad enterprise ERP backend, not a thin prototype; M20-M35 require capability-by-capability reconciliation.
  - Inventory-only anomaly for later M19 audit: unusual root backend file `backend/=2.9.0`; classify before any cleanup.
  - No source code modified; no historical Done state reopened.

- [x] **M00.S02.T002 — Frontend routes/pages/components inventory**
  - Frontend uses Next.js App Router structure under `frontend/src/app`, with shared `components`, `context`, `hooks`, `lib`, and `middleware.ts` layers.
  - Shared shell/security/navigation layer includes `DashboardShell`, `Sidebar`, `CommandPalette`, `NotificationBell`, `ProtectedRoute`, `PermissionGuard`, `ErrorBoundary`, and reusable domain/UI component families.
  - `nav-config.tsx` defines the consolidated workspace information architecture: 33 workspaces grouped into 9 clusters; child functions are tabs/workspace functions rather than uncontrolled sidebar sprawl.
  - Middleware preserves standalone operational pages while redirecting legacy routes to consolidated workspace/tab destinations.
  - `AuthContext` and permission guards provide frontend permission-aware behavior; shared Axios `apiClient` centralizes API access.
  - Existing visible workspace/tab capabilities include Inventory Cycle Count, Shelf Life/FEFO, Lot Traceability, Serial/Batch, Stock Movements; WMS Picking/Putaway/Bin Replenishment; Procurement Subcontracting/Landed Cost/Supplier Portal/AI Suggestions; Production Execution/Machine Operators/Material Flow/OEE/Batch-Lots; Planning MRP/MPS/Kanban/Capacity Board/Simulation; BOM Formula Versions/Substitutes/BOM Compare/Conversion Profiles; Quality QMS/HACCP/Allergen/Complaints/CAPA/COA.
  - This frontend evidence materially overlaps M20-M35 and must be validated against working APIs during S04, not treated as proof of completion by itself.

- [x] **M00.S02.T003 — Database models/migrations/schema inventory**
  - `backend/app/models/__init__.py` imports a very large domain model registry covering core ERP, scoped RBAC, webhook/event models, inventory/WMS, procurement, production, finance, quality, maintenance, logistics, tax, integration/plugin, document/e-sign, AI, MRP, BOM, shop floor, execution, planning, MPS, machine/operator, traceability/recall, subcontracting, invoice matching, landed cost, FEFO/shelf-life, GS1 and many other families.
  - Direct M20-M35 overlap exists at model-family level: `MPSPlan/MPSLine/MPSCampaign/MPSCapacitySlot/MPSWhatIfScenario`, `PlanningScenario/ResourceCalendar/OperationQueue/CapacityLoadSnapshot/ChangeoverMatrix/PlanningSimulation`, `ProdExecOrder/ExecWorkOrder/ExecOrderMaterial/BatchGenealogy`, `Machine/OperatorProfile/MachineRuntimeLog/LaborTimeLog/MachinePerformanceSnapshot/DowntimeIntelligence`, `TraceEvent/LotGenealogyLink/RecallHeader`, `LandedCostHeader/LandedCostAllocationLine`, `FEFOAuditLog`, Shop Floor session/activity/handover records, and advanced quality/QMS models.
  - Alembic is the schema source of change truth. Existing migration history includes APS planning, WMS reconciliation, procurement governance, accounting/posting/access scope and other enterprise additions.
  - Inventory only: schema/model presence is recorded here; constraints, migration ownership, orphan/drift, index quality and referential integrity remain for M00.S05 strict audit.

- [x] **M00.S02.T004 — API/router/service inventory**
  - Central API registration is backed by a very large endpoint directory and domain service layer.
  - Endpoint modules exist for major baseline and enhancement domains including `mps`, `mrp`, `planning`, `production_execution`, `shop_floor`, `material_flow`, `machine_operator`, `traceability`, `landed_cost`, `procurement_suggestion`, `subcontracting`, `supplier_portal`, `invoice_match`, `qms`, `quality`, `wms`, `shelf_life`, `cycle_count`, `serial_tracking`, `webhooks`, `iot`, `integrations`, `bulk_import`, `report_builder`, finance, HR, maintenance, utilities, sales and many others.
  - Services are split by domain rather than concentrated in one monolith; examples include planning/MRP/MPS engines, WMS/inventory, BOM costing/scaling/compliance, finance posting/costing, AI provider/runtime, maintenance, utilities, integration/webhook and procurement services.
  - Presence of endpoint+service pairs strongly suggests many M20-M35 features have executable backend surfaces; S03/S04 must test semantics and completeness rather than infer completion from file names.

- [x] **M00.S02.T005 — Jobs/queues/schedulers/websocket/event mechanisms inventory**
  - A persistent webhook/event engine exists with event definitions, event log, subscriptions, delivery attempts, payload filtering/transforms, outbound Bearer/Basic/HMAC authentication, HTTP delivery, exponential retry, dead-letter status and replay/process functions.
  - Standard events include generic record/status/approval/payment/inventory/shipment/login events plus sales-order, PO, invoice, production-order, quality-inspection and 2FA events.
  - The webhook service explicitly describes pending/retry delivery processors as being called by a background endpoint or cron.
  - Repository searches during this inventory did not surface an always-running Celery/APScheduler/WebSocket worker architecture. Treat automatic dispatch/scheduling as `AUDIT_REQUIRED`, not absent by fiat; M31 and M00.S05.T020 must verify runtime invocation paths.

- [x] **M00.S02.T006 — CSV/import/export/reporting infrastructure inventory**
  - Central `bulk_import.py` router implements a reusable import lifecycle: CSV template download, validate-only, full import, filtered import history and downloadable error CSV.
  - Adapter architecture includes products, materials, suppliers, warehouses, employees, initial inventory stock, recipes and recipe/BOM items, plus extensive utilities import support.
  - Import framework uses module permissions, Pydantic validation, unique/business keys, relation resolution and persisted `ImportHistory`.
  - Reporting/analytics infrastructure includes `report_builder`, analytics/dashboard endpoints and multiple module report surfaces.
  - Because CSV/template usability is important to this project, M00.S05.T019 must explicitly test actual template downloads, parsing, validation, relation resolution, duplicate handling, error CSV and round-trip behavior rather than assuming correctness from implementation presence.

- [x] **M00.S02.T007 — Integration provider/capability inventory**
  - Central `integration_capabilities.py` distinguishes live/sandbox/simulated/stub states and guards production execution.
  - M-Pesa Daraja: sandbox-ready/simulation-capable; live production requires credentials and validation.
  - WhatsApp: sandbox-ready with DB-stored credentials; live validation still external-account dependent.
  - eTIMS: sandbox-ready connector architecture, production disabled pending provider/KRA decisions and validation.
  - AI providers: provider abstraction exists and can become live when configured; historical live-key blocker remains.
  - Webhooks: implemented but production execution/runtime delivery path requires audit.
  - IoT, CRM sync, e-commerce sync and GraphQL API remain stub-only in capability registry.
  - Barcode physical printing remains stub-only despite label generation capability; bank API is simulated-only; marketing sync also remains stub-only.
  - Historical external blockers therefore remain broadly consistent with current source evidence and must be revalidated in M17/M18 audits.

- [x] **M00.S02.T008 — Tests/CI/Docker/deployment/environment inventory**
  - GitHub Actions CI has backend, frontend and Docker configuration jobs.
  - Backend CI provisions PostgreSQL 16 + Redis 7, installs dependencies, runs `pip-audit`, compile/import checks, test DB bootstrap+migrations, verifies exactly one Alembic head and runs full `pytest`.
  - Frontend CI runs `npm ci`, critical-level dependency audit, type-check and production build.
  - Docker CI validates both development and production compose configuration.
  - Backend test suite contains focused security, attack simulation, eTIMS, forecasting and GAP/module tests, including APS planning, WMS and procurement maturity tests. Frontend has substantial Playwright E2E coverage for auth, shell, critical workflows, action-card health and module/manual screenshot workflows.
  - Development compose runs PostgreSQL, Redis, backend and frontend with health checks and mounted source. Production compose keeps DB/Redis unexposed to host, enables Redis AUTH, configures backend pool sizing and resource reservations/limits.
  - This is inventory evidence only. Latest CI status, complete test pass rate, migration runtime and deployment readiness will be re-run/verified during M00.S05.T022/T021.

- [x] **M00.S02.T009 — Documentation/reference inventory**
  - `PLANS.md` remains strategic architecture reference and explicitly prioritizes data integrity, modularity, incremental implementation and not rewriting working modules.
  - `docs/` contains repository reviews, health/performance/security/QA/deployment evidence, action-card and route audits, project inventory and other engineering references.
  - `docs/planning/` contains the ERP roadmap/status matrix plus GAP audit/schema/implementation-note families, providing historical design evidence that must be cross-checked against current source rather than accepted blindly.
  - `docs/user-manual/` contains manual audits, screenshot/PDF pipelines, in-app-help reports/plans and full-reference/module manual assets.
  - Documentation is rich but may contain stale historical assertions. Current repository source + tests + migrations take precedence during S03/S04/S05; docs are supporting evidence, not implementation truth.

## M00.S03 — Existing-System Audit M01-M19

- [ ] M00.S03.T001 — Audit M01 Platform / Infrastructure
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

## M01.S01 — Platform UX and Enterprise Support Services

- [x] **M01.S01.T001 — Login page POVU logo size**  
  Historical Task ID: `TASK-001` · Historical Status: Done · Type: UI  
  Result: login logo enlarged and verified by type-check/build.

- [P] **M01.S01.T002 — Document Management / Knowledge Base / E-Sign hardening**  
  Historical Task ID: `TASK-027` · Historical Status: In Progress  
  Completed: KB/e-sign permission guards, frontend permission wrappers, focused security tests.  
  Remaining: `GAP-012F` service-layer extraction is deferred; live migration ownership verification needs Docker/dev DB; file-upload pipeline is blocked on storage-adapter decision.

- [x] **M01.S01.T003 — Contextual question-mark help popovers**  
  Historical Task ID: `HELP-001` · Historical Status: Done  
  Result: reusable `PageHelpTooltip`, centralized help registry and topic wiring across operational pages.

- [x] **M01.S01.T004 — Recapture screenshots and manual notes after help popovers**  
  Historical Task ID: `HELP-002` · Historical Status: Done.

---

# M02 — Authentication / RBAC

## M02.S01 — Identity, Credentials and 2FA

- [x] **M02.S01.T001 — E2E/admin credentials audit + management-user environment strategy**  
  Historical Task ID: `TASK-007` · Historical Status: Done  
  Result: environment-driven management-user seed, production validation, first-login password-change behavior and hardening tests.

- [!] **M02.S01.T002 — SMTP + email OTP live end-to-end verification**  
  Historical Task ID: `TASK-012` · Historical Status: Blocked  
  Existing code: SMTP sender and production fail-fast guard implemented; OTP tests pass.  
  Blocker: real SMTP credentials and live staging test.

---

# M03 — Master Data

**Historical direct-task mapping:** none dedicated. Existing implementation must be classified during M00.S03.T003. Production/inventory seed history proves master-data models for products, materials and warehouses exist, but M03 completeness is not assumed.

- [A] M03.S00.T001 — Reconcile existing master-data capabilities during M00 audit

---

# M04 — Product / Material / Supplier Master

## M04.S01 — Product Identification / GS1 Data Completeness

- [!] **M04.S01.T001 — GS1 GTIN coverage / product master completeness**  
  Historical Task ID: `TASK-019` · Historical Status: Pending / external dependency  
  Blocker: GS1 company prefix and SKU→GTIN assignments. Primarily a master-data activity; optional product-page shortcut may be added later.

- [A] M04.S00.T002 — Audit material and supplier-master completeness under M00.S03.T004

---

# M05 — Warehouse & Inventory

## M05.S01 — Inventory Real-Data Foundation

- [x] **M05.S01.T001 — Inventory/Stock real data Phase I1-I7**  
  Historical Task ID: `TASK-016` · Historical Status: TASK-016.1 through TASK-016.7 Done  
  Included historical batches:
  - [x] `TASK-016.1` lots, stock balances, stock movements and FIFO cost layers
  - [x] `TASK-016.2` WMS warehouse zones and storage locations
  - [x] `TASK-016.3` trace events / lot genealogy
  - [x] `TASK-016.4` cycle-count plans
  - [x] `TASK-016.5` shelf-life profiles and alerts
  - [x] `TASK-016.6` demand forecasts and forecast lines
  - [x] `TASK-016.7` MRP run/results/suggestions/exceptions
  Historical live DB idempotency and regression checks are preserved in `TASKS_HISTORY.md`.

- [A] M05.S02.T001 — Audit transactional warehouse/inventory completeness during M00.S03.T005

---

# M06 — Procurement

Historical health-audit work changed procurement endpoint safeguards, and procurement suggestion services already exist, but no dedicated top-level historical procurement feature task establishes full module completeness.

- [A] M06.S00.T001 — Audit procurement baseline, RFQ/supplier/approval/replenishment functionality during M00.S03.T006

---

# M07 — Sales / Distributor Operations

Historical M-Pesa and eTIMS work intersects sales, but they are mapped primarily under M18. Sales/distributor baseline remains an audit target.

- [A] M07.S00.T001 — Audit Sales / Distributor Operations during M00.S03.T007

---

# M08 — Production Core

## M08.S01 — Production Real-Data Foundation

- [x] **M08.S01.T001 — Production module real data Phase P1-P11**  
  Historical Task ID: `TASK-015` · Historical Status: Done for implemented seed scope  
  Included:
  - [x] `TASK-015.1` FMCG production seed: work centers, routings/steps, recipes, production plans/orders, work orders, batch lots
  - [x] `TASK-015.1A` live DB idempotency validation
  - [x] `TASK-015.2` OEE, QC inspection, waste and downtime records
  Existing historical evidence proves significant production-domain implementation and is a key input to M22, M23, M26, M29 and M32 reconciliation.

- [A] M08.S02.T001 — Audit production lifecycle and execution completeness during M00.S03.T008

---

# M09 — Recipes / BOM

Historical production work confirms `Recipe`, `RecipeItem`, `AdvancedBOM`, `AdvancedBOMLine` and `BOMYieldConfig` model families existed at the time of TASK-015 audit. Full functional completeness is not assumed.

- [A] M09.S00.T001 — Audit current Recipe/BOM implementation during M00.S03.T009

---

# M10 — Quality

TASK-015 seeded `AdvQCInspection` records and the repository contains QMS/quality surfaces. Full QC/QA scope will be established by M00.

- [A] M10.S00.T001 — Audit current quality/QMS implementation during M00.S03.T010

---

# M11 — Maintenance

Historical completed GAP summary records Predictive Maintenance as implemented at module level, but M11 receives no completeness claim until source audit.

- [A] M11.S00.T001 — Audit Maintenance baseline during M00.S03.T011

---

# M12 — Utilities

## M12.S01 — Utility Factory Data Foundation

- [x] **M12.S01.T001 — Utilities module real factory seed data foundation**  
  Historical Task ID: `TASK-009` · Historical Status: Done  
  Existing data includes electricity, compressor, boiler/gas, water/soft-water, solar, wastewater, chemicals, alarms/anomalies and utility-cost allocations.

- [A] M12.S02.T001 — Audit utility module functional completeness and cross-module integration

---

# M13 — Finance / Costing

## M13.S01 — Production / Utility Cost Allocation

- [P] **M13.S01.T001 — Finance cost allocation engine Phase F4-F6**  
  Historical Task ID: `TASK-017` · Historical Status: Partial  
  Completed:
  - [x] `TASK-017.1` finance seed / accounting structural data
  - [x] `TASK-017.2` utility bill posting idempotency and related finance integration work
  Remaining:
  - [!] `TASK-017.3` utility allocation GL journal mapping, blocked on accountant debit/credit/account aggregation decisions
  - [!] `TASK-017.4` product profitability API/report, blocked on revenue-definition decision
  - [!] `TASK-017.5` profitability frontend, dependent on TASK-017.4

- [A] M13.S02.T001 — Audit accounting/costing completeness during M00.S03.T013

---

# M14 — HR / Operator / Shift

Historical health/performance work touched HR services and the production domain includes shift/labor structures, but no full-module completion claim is imported.

- [A] M14.S00.T001 — Audit HR/operator/shift baseline during M00.S03.T014

---

# M15 — Reporting / Analytics

Historical manuals and dashboard/report infrastructure exist, but current report/analytics capability needs source audit.

- [A] M15.S00.T001 — Audit reporting/analytics baseline during M00.S03.T015

---

# M16 — AI

## M16.S01 — AI Runtime and Forecasting

- [!] **M16.S01.T001 — Enable AI live mode**  
  Historical Task ID: `TASK-002` · Historical Status: Blocked  
  Backend provider abstraction supports Anthropic/OpenAI/Gemini/Mock; blocker is a real provider API key and live configuration.

- [x] **M16.S01.T002 — Demand forecasting upgrade using local Holt-Winters**  
  Historical Task ID: `TASK-025` · Historical Status: Done  
  `ForecastModelType.PROPHET` path uses local statsmodels Holt-Winters with fallback; historical forecast tests pass. No external API is required.

- [A] M16.S02.T001 — Audit remaining prediction/recommendation/optimization/agent capability during M00.S03.T016

---

# M17 — Integrations

## M17.S01 — External Provider Integrations

- [!] **M17.S01.T001 — WhatsApp production configuration/live validation**  
  Historical Task ID: `TASK-004` · Historical Status: Blocked  
  Live-send code exists; blocker is Meta Business/WABA credentials and real validation.

- [!] **M17.S01.T002 — CRM real integration**  
  Historical Task ID: `TASK-020` · Historical Status: Pending  
  Blocker: CRM vendor selection and credentials.

- [!] **M17.S01.T003 — E-commerce real integration**  
  Historical Task ID: `TASK-021` · Historical Status: Pending  
  Blocker: commerce platform selection and credentials.

- [!] **M17.S01.T004 — IoT/Machine MQTT/streaming integration**  
  Historical Task ID: `TASK-022` · Historical Status: Pending  
  Module/permissions skeleton exists historically; real bridge blocked on hardware, broker and topic/schema decisions.

- [!] **M17.S01.T005 — Bank API / Kenyan bank sync**  
  Historical Task ID: `TASK-023` · Historical Status: Pending  
  Blocker: bank selection, agreement and API credentials.

- [!] **M17.S01.T006 — Label printer SDK integration (ZPL/EPL/TSPL)**  
  Historical Task ID: `TASK-024` · Historical Status: Pending  
  Blocker: printer model and connectivity decision.

- [A] M17.S02.T001 — Audit all integration capabilities and simulation/live boundaries

---

# M18 — Kenya Localization

## M18.S01 — M-Pesa

- [!] **M18.S01.T001 — Wire M-Pesa production credentials**  
  Historical Task ID: `TASK-003` · Historical Status: Blocked  
  Daraja service and delegation from sales/moto paths were implemented historically; blocker is Safaricom credentials and live test.

## M18.S02 — KRA eTIMS

- [P] **M18.S02.T001 — eTIMS live integration**  
  Historical Task ID: `TASK-005` · Historical Status: Partial / blocked live provider  
  Completed historical sub-scope:
  - [x] `TASK-005.1A` provider config/submission models and migration scope
  - [x] `TASK-005.1B` provider-neutral connector/stub architecture
  - [x] `TASK-005.1C` fiscalization workflow endpoints
  - [x] `TASK-005.1F.1` frontend shared types/API client
  - [x] `TASK-005.1F.2` global eTIMS monitoring UI
  - [x] `TASK-005.1F.3` invoice-detail eTIMS card
  - [x] `TASK-005.1F.4` UX hardening/loading isolation
  - [x] `TASK-005.1F.5` navigation correction
  Remaining:
  - [!] `TASK-005.1D` finance posting gate, blocked on accountant fiscalization policy decision
  - [!] `TASK-005.1E` live provider adapter, blocked on provider selection, KRA credentials and official provider/API specification

- [A] M18.S03.T001 — Audit broader Kenya statutory/localization coverage during M00.S03.T018

---

# M19 — Security / Deployment / Hardening

## M19.S01 — Security Hardening

- [x] **M19.S01.T001 — GS1 route authorization guards**  
  Historical Task ID: `TASK-006` · Historical Status: Done.

- [x] **M19.S01.T002 — ERP health audit and finding remediation**  
  Historical Task ID: `TASK-008` · Historical Status: Done  
  Planned batches completed; historical result reached 0 HIGH findings with accepted/documented MEDIUM backlog.

- [x] **M19.S01.T003 — Redis AUTH for production**  
  Historical Task ID: `TASK-011` · Historical Status: Done.

- [x] **M19.S01.T004 — python-jose → PyJWT migration**  
  Historical Task ID: `TASK-014` · Historical Status: Done. All migration/verification batches closed.

## M19.S02 — QA / Runtime / Deployment

- [x] **M19.S02.T001 — Playwright smoke rerun after recovery changes**  
  Historical Task ID: `TASK-013` · Historical Status: Done · Result: 56/56 pass.

- [x] **M19.S02.T002 — Multi-replica migration safety**  
  Historical Task ID: `TASK-026` · Historical Status: Done  
  PostgreSQL Alembic online migrations use advisory locking; contract tests historically passed.

- [x] **M19.S02.T003 — GitHub push and deployment-readiness checkpoint**  
  Historical Task ID: `PUSH-001` · Historical Status: Done.

- [D] **M19.S02.T004 — Local Docker Compose staging environment**  
  Historical Task ID: `LOCAL-STAGING-001` · Historical Status: Deferred / not started  
  Planned scope: staging compose stack, staging env, migrations, frontend/backend verification and hardening tests. Must be reconsidered after M00 audit rather than blindly resumed.

- [x] **M19.S02.T005 — Demo seed-data audit and gate verification**  
  Historical Task ID: `DATA-CLEANUP-001` · Historical Status: Done  
  Result: demo business data confirmed gated; finance structural seed moved outside demo gate because it is required for GL operation.

- [A] M19.S03.T001 — Strict current security/deployment/hardening audit under M00.S03/M00.S05

---

# M20-M35 — Provisional Enhancement Scope Pending M00 Reconciliation

These are NOT automatically new implementation milestones. Repository inventory now proves that many have models, APIs, services and frontend surfaces already. M00.S04 must decompose every intended prompt capability and classify it before work is created.

# M20 — Master Production Scheduling

**Status:** AUDIT_REQUIRED

Preliminary existing evidence:
- Demand Forecast and MRP structures exist historically.
- Current model registry includes `MPSPlan`, `MPSLine`, `MPSCampaign`, `MPSCapacitySlot`, `MPSWhatIfScenario`, `MPSAIRecommendation`.
- Dedicated `mps` endpoint exists and Planning workspace exposes MPS.

- [A] M20.S00.T001 — Compare MPS prompt against existing MPS/MRP/forecast/services/UI and classify sub-capabilities

# M21 — Advanced BOM / Fluid-to-Unit

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- `AdvancedBOM`, `AdvancedBOMLine`, substitute/yield structures and conversion profiles exist.
- BOM workspace visibly exposes Formula Versions, Substitutes, BOM Compare and Conversion Profiles.
- Bulk import supports recipe/BOM items.

- [A] M21.S00.T001 — Compare multi-level BOM, bulk-to-unit, yield/loss, packaging, substitution and versioning scope against existing code

# M22 — Production Order / Work Order

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- ProductionOrder, WorkOrder, WorkCenter, Routing, RoutingStep, ProductionPlan and BatchLot structures exist and were historically DB-seeded/validated.
- Production/execution endpoints and UI surfaces exist.

- [A] M22.S00.T001 — Determine which planned production/work-order capabilities are ALREADY_DONE vs PARTIAL/MISSING

# M23 — Shop Floor Execution

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Shop Floor models include SFSession, WOActivityLog, SFDowntimeLog, ShiftHandover, SupervisorOverride and AI recommendations.
- Dedicated `shop_floor` endpoint and Production Execution frontend surface exist.

- [A] M23.S00.T001 — Reconcile operator/shop-floor execution prompt with current backend and UI

# M24 — Material Flow

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Production/inventory material movement structures exist.
- Dedicated `material_flow` endpoint and Production workspace Material Flow surface exist.
- Historical seed did not fully exercise all accounting-linked MaterialConsumption/FinishedGoodsReceipt paths.

- [A] M24.S00.T001 — Audit staged issue/consume/return/WIP/bulk-to-pack material-flow behavior

# M25 — Cross-Border / Landed Cost

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Dedicated landed-cost models and `landed_cost` API exist.
- Procurement workspace exposes Landed Cost.
- Logistics models include InternationalShipment, ShipmentContainer, customs documents/clearance and arrival notification.

- [A] M25.S00.T001 — Audit current import/in-transit/customs/freight/insurance/allocation/posting behavior against planned cross-border engine

# M26 — Machine & Operator Intelligence

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Current models include Machine, OperatorProfile, teams/members, skills/certifications, assignments/history, MachineRuntimeLog, LaborTimeLog, MachinePerformanceSnapshot, DowntimeIntelligence, SupervisorReview and AI recommendations.
- Dedicated `machine_operator` endpoint and Machine Operators frontend surface exist.
- IoT live bridge remains stub-only in integration registry.

- [A] M26.S00.T001 — Compare machine/operator intelligence prompt with current machine, labor, OEE, shift, costing and IoT structures

# M27 — Quality Gates

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Quality models include inspections/results, templates, sampling, HACCP/CCP, corrective actions, deviation/release status, lot quality and QMS AI recommendations.
- `quality` and `qms` endpoints and Quality workspace surfaces exist.

- [A] M27.S00.T001 — Determine whether operational QC blocking/release gates already exist and where gaps remain

# M28 — Full Traceability

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- TraceEvent/TraceEventLine, LotGenealogyLink and recall header/scope/action/customer-impact/return models exist.
- BatchGenealogy exists in Production Execution.
- Dedicated `traceability` endpoint and inventory traceability UI exist.

- [A] M28.S00.T001 — Compare forward/backward trace, genealogy, recall and customer-impact scope against current implementation

# M29 — Maintenance / OEE Upgrade

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Maintenance assets/PM/work orders/breakdowns/spares exist.
- OEE/downtime/waste production structures and seeded records exist.
- Historical GAP work records Predictive Maintenance at module level.

- [A] M29.S00.T001 — Reconcile preventive/corrective maintenance, MTBF/MTTR/OEE/calibration/predictive scope

# M30 — AI Decision & Simulation

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- AI provider/runtime, production predictions/anomalies/suggestions/model metrics, planning simulations, MPS what-if scenarios and AI recommendations across modules exist.
- AI live external-provider mode is still blocked on credentials.

- [A] M30.S00.T001 — Audit prediction/anomaly/recommendation/scenario/decision/simulation architecture before enhancement work

# M31 — API / Event Architecture

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Broad REST APIs and shared API client exist.
- Persistent webhook/event engine has subscriptions, delivery attempts, HMAC/Bearer/Basic auth, retry/dead-letter and replay logic.
- Runtime scheduling/worker path for automated dispatch remains audit-required.
- Integration registry marks GraphQL API as stub-only.

- [A] M31.S00.T001 — Audit REST/OpenAPI, webhook/event bus, idempotency, retry, background delivery, external API security and GraphQL need

# M32 — Advanced Production Planning

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Models include PlanningScenario, ResourceCalendar, OperationQueue, CapacityLoadSnapshot, ChangeoverMatrix, PlanningBottleneck, PlanningAIRec and PlanningSimulation.
- Dedicated APS planning migration and `planning` API exist.
- Planning workspace exposes MRP, MPS, Kanban, Capacity Board and Simulation.

- [A] M32.S00.T001 — Compare shift/day/week/month/machine/order/section/campaign/finite-capacity planning prompt to current implementation

# M33 — Warehouse / Inventory Enterprise Upgrade

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- WMS zones/locations, lot/stock/movements/cost layers, cycle counts, FEFO/shelf-life, traceability and serial/batch structures exist.
- WMS, inventory, shelf-life, cycle-count and serial-tracking APIs exist.
- WMS workspace exposes Picking, Putaway and Bin Replenishment.
- Dedicated WMS depth reconciliation migration exists.

- [A] M33.S00.T001 — Compare enterprise warehouse prompt to current WMS/inventory/FEFO/reservation/picking/quarantine/in-transit/valuation features

# M34 — Strategic Procurement Upgrade

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Procurement models and APIs include PR/PO/GRN/import shipments/supplier evaluation/payment plus RFQ/quotation-oriented surfaces, supplier portal, subcontracting, procurement suggestions and invoice matching.
- Procurement workspace exposes Subcontracting, Landed Cost, Supplier Portal and AI Suggestions.
- Dedicated procurement-governance migration exists.

- [A] M34.S00.T001 — Compare RFQ/tender/quotation/PO/contract/supplier-scorecard/import/subcontracting prompt to current procurement implementation

# M35 — QC / QA Enterprise Upgrade

**Status:** AUDIT_REQUIRED

Preliminary evidence:
- Quality/QMS models and endpoints cover QC parameters/inspections/results, templates, sampling, HACCP/CCP, corrective action, deviation/release status, lot quality, allergen validation and QMS AI recommendations.
- Quality workspace exposes QMS/HACCP, Allergen Matrix, Consumer Complaints, CAPA and COA.

- [A] M35.S00.T001 — Compare specification/QCP/check/release/NCR/CAPA/quality-review/supplier-quality prompt against current implementation

---

# Active Blockers / Human Decisions Carried Forward

These are preserved from historical state and will be revalidated during M00, not silently discarded:

- AI live provider API key (`TASK-002`)
- Safaricom Daraja credentials/live validation (`TASK-003`)
- Meta WhatsApp credentials/live validation (`TASK-004`)
- eTIMS accountant GL/fiscalization policy (`TASK-005.1D`)
- eTIMS provider/KRA sandbox credentials/API specification (`TASK-005.1E`)
- SMTP credentials/live OTP test (`TASK-012`)
- Product profitability revenue definition (`TASK-017.4`)
- Utility allocation GL account mapping (`TASK-017.3`)
- GS1 company prefix/GTIN assignments (`TASK-019`)
- CRM vendor/credentials (`TASK-020`)
- E-commerce platform/credentials (`TASK-021`)
- MQTT broker/factory hardware/topic schema (`TASK-022`)
- Bank selection/API agreement/credentials (`TASK-023`)
- Label-printer model/connectivity (`TASK-024`)
- Document file-storage adapter decision (`TASK-027`)
- Live migration ownership verification requires Docker/dev DB (`TASK-027`)

M00 audit may prove some blockers obsolete, superseded, or already resolved. Until then they remain carried-forward state.

---

# Historical Migration Coverage

## Main numbered tasks

`TASK-001` through `TASK-027`: mapped into M00-M19 above. Detailed original cards remain in `TASKS_HISTORY.md`.

## Special task families

- `MANUAL-001` through `MANUAL-006`: mapped under M00 documentation/governance; all historically Done.
- `HELP-001` and `HELP-002`: mapped under M01; both historically Done.
- `PUSH-001`: mapped under M19; historically Done.
- `LOCAL-STAGING-001`: mapped under M19; historically Deferred.
- `DATA-CLEANUP-001`: mapped under M19; historically Done.

Migration rule: nested historical task IDs remain valid evidence references even when their new canonical ID is different.

---

# Next Execution Gate

**Do not implement M20-M35 yet.**

M00.S02 repository capability inventory is complete. The next work is M00.S03.T001, a source-based audit of M01 Platform / Infrastructure, followed sequentially by M02-M19. After M01-M19 classification, M00.S04 will compare every M20-M35 capability against the actual implementation. Only after M00.S05 strict full audit and M00.S06 roadmap regeneration may post-audit implementation begin.