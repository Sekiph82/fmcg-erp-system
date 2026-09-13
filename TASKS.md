# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

The previous canonical tracker is preserved without reinterpretation as `TASKS_HISTORY.md`. Any task marked Done in that historical tracker is accepted as Done for migration purposes. Historical details, evidence, test output, file lists, audit notes, and commit references remain available there and are referenced from this ledger by Historical Task ID.

`PLANS.md` remains architecture/strategy reference only and is not a competing task tracker.

---

## Project Status

- **Current Milestone:** M00 — Governance & Repository Baseline
- **Current Sprint:** M00.S03 — Existing-System Audit M01-M19
- **Current Task:** M00.S03.T003 — Audit M03 Master Data
- **Current Task Status:** READY
- **Next Task/Action:** Audit M03 Master Data against current models, APIs, UI, imports, governance/versioning and tests; classify completeness without implementing enhancement work.
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
5. Manual, Help, Push, Local Staging, Data Cleanup, blocked credential/vendor, and nested task families must be preserved.
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

- [x] **M00.S01.H001 — Repository Graphify output cleanup** · Historical Task ID: `TASK-010` · Done.
- [x] **M00.S01.H002 — Full ERP Reference Manual PDF generation script** · Historical Task ID: `TASK-018` · Done.
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

- [x] **M00.S03.T002 — Audit M02 Authentication / RBAC**
  - **Classification: PARTIAL.** Authentication and authorization are substantially implemented with strong enterprise controls, but session lifecycle and production verification have bounded gaps.
  - **ALREADY_DONE — authentication:** cookie-based JWT authentication; bcrypt password hashing; JWT expiry and JTI; HttpOnly auth cookie; production guard requires secure cookie; active-user validation; explicit logout token revocation; audit events for login success/failure/logout; username + IP brute-force lockout with Redis support and in-memory fallback.
  - **ALREADY_DONE — password controls:** password policy validates minimum length, uppercase/lowercase/digit, optional special character, common-password blocklist and username equality; policy is enforced on user creation, admin password reset and self-service password change; production configuration requires special characters.
  - **ALREADY_DONE — 2FA:** TOTP, email OTP and SMS OTP setup/login paths; pending/setup session tokens; expiry/attempt limits; recovery codes; recovery-code regeneration/use; password-protected disable flow; audit events; production configuration rejects development OTP delivery mode and requires SMTP when email 2FA is enabled.
  - **ALREADY_DONE — RBAC model:** normalized `Role`, `Permission`, role-permission association and user-role relationships; permission codes use `module.action`; active role/permission filtering; superuser bypass; role CRUD/activation/deactivation; permission assignment; user role assignment; changes are audit logged.
  - **ALREADY_DONE — row/scope authorization:** generic `AccessScope` supports user- or role-owned scopes with DB ownership constraint, uniqueness/indexes and per-action flags for view/create/edit/delete/approve/post/release/cancel/export/import/transfer/adjust/receive/dispatch. Scope types include company, branch, warehouse, factory, production line, department, region/team, categories, quality lab, cost center, project, machine and utility area. Backend helpers implement all-vs-own-scope permissions, user override semantics, record-scope resolution and locked-status mutation guards.
  - **ALREADY_DONE — frontend authorization:** `AuthContext` bootstraps `/auth/me`, stores no access JWT in normal browser state, supports 2FA redirect/completion, module and permission checks, scoped action checks, record scope resolution and first-allowed-route routing. This mirrors the backend scope vocabulary closely enough to provide UI gating while backend remains authoritative.
  - **ALREADY_DONE — security tests/evidence:** repository security report records 150/150 controlled security tests passing at the time of the report, including brute force, token replay after logout, password-policy and superuser/permission checks. Current CI also runs the backend test suite, but M00 audit did not execute tests itself.
  - **PARTIAL — session lifecycle:** `SESSION_INACTIVITY_TIMEOUT_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS` are configured but no repository usage was found during this audit. No implemented refresh-token rotation flow was established. Access JWT lifetime remains 8 hours by default. Treat inactivity timeout/refresh rotation as unimplemented until strict audit proves otherwise.
  - **PARTIAL — global user revocation:** token blocklist has a `revoke_all_for_user()` helper, but `get_current_user()` only checks the presented token's blocklist entry; this audit did not establish enforcement of a user-level revocation marker for all already-issued sessions. Per-token logout revocation is implemented.
  - **PARTIAL — production verification:** historical security report explicitly leaves live-DB checks for portal tenant isolation, supplier portal scoping and related cross-account isolation. Admin/finance mandatory-2FA policy is listed as a production retest item rather than proven enforced globally.
  - **PARTIAL — CSRF/session hardening:** normal auth relies on SameSite HttpOnly cookies and backend authorization. No dedicated CSRF token/double-submit mechanism was established during this audit. This is not declared exploitable here, but must be assessed in M00.S05.T005 against actual deployment/origin policy.
  - **Audit conclusion:** M02 is not missing and should not be rebuilt. Remaining work is hardening/verification: refresh/inactivity lifecycle, user-wide session revocation semantics, mandatory privileged-role 2FA policy if required, live tenant/scope isolation tests and CSRF posture verification.
  - **No remediation implemented during M02 audit.** Existing authentication/RBAC code remains untouched.

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
- [ ] M00.S05.T017 — CSV/template/import/export/report audit
- [ ] M00.S05.T018 — Jobs/queues/events/retry/DLQ/idempotency audit
- [ ] M00.S05.T019 — Tests/CI/deployment/observability audit
- [ ] M00.S05.T020 — P0/P1/P2/P3 finding register and remediation plan

---

# Baseline Historical Capability Map — M01-M19

Historical Done state is preserved. M00.S03 determines current completeness and maps remaining work without rewriting history.

- **M01 Platform / Infrastructure** — PARTIAL after M00.S03.T001.
- **M02 Authentication / RBAC** — PARTIAL after M00.S03.T002; strong auth/RBAC/scope/2FA controls exist, with bounded session-lifecycle and production-verification gaps.
- **M03 Master Data** — Audit required.
- **M04 Product / Material / Supplier Master** — Audit required.
- **M05 Warehouse & Inventory** — Audit required.
- **M06 Procurement** — Audit required.
- **M07 Sales / Distributor Operations** — Audit required.
- **M08 Production Core** — Audit required.
- **M09 Recipes / BOM** — Audit required.
- **M10 Quality** — Audit required.
- **M11 Maintenance** — Audit required.
- **M12 Utilities** — Audit required.
- **M13 Finance / Costing** — Audit required.
- **M14 HR / Operator / Shift** — Audit required.
- **M15 Reporting / Analytics** — Audit required.
- **M16 AI** — Audit required.
- **M17 Integrations** — Audit required.
- **M18 Kenya Localization** — Audit required.
- **M19 Security / Deployment / Hardening** — Audit required.

---

# M20-M35 Enhancement Roadmap — Provisional Until Reconciliation

These milestones remain intentionally compact here. M00.S04 will rewrite each into only the capabilities that are actually missing or partial after source-level comparison.

- **M20 Master Production Scheduling:** demand/forecast-driven MPS, replenishment/procurement suggestions, safety stock, capacity/material checks, scenario comparison, approval/release.
- **M21 Advanced BOM / Fluid-to-Unit:** bulk-to-pack conversion, nested/multi-output BOM, yield/loss/spillage, packaging hierarchy, version/effective-date governance.
- **M22 Production Order / Work Order:** routing, operations, work centers, dependencies, split/merge/backorder/rework/subcontracting and execution state.
- **M23 Shop Floor Execution:** operator/tablet execution, start/pause/finish, quantities/scrap/downtime, instructions/SOP, QC gates, time/labor capture, offline/mobile where justified.
- **M24 Material Flow:** staging/WIP/issue/consumption/return/FG receipt, tank-line-packaging flow, pick lists, reservations, 1/2/3-step production and genealogy linkage.
- **M25 Cross-Border / Landed Cost:** in-transit ownership/warehouses, shipment/customs/freight/insurance, landed-cost allocation and valuation/accounting integration.
- **M26 Machine & Operator Intelligence:** runtime/operator logs, efficiency, downtime reasons, energy/labor cost, qualifications, line/shift KPIs and anomaly signals.
- **M27 Quality Gates:** configurable incoming/in-process/final/logistics gates, mandatory hold/release/block semantics, sampling/evidence/spec integration.
- **M28 Full Traceability:** lot genealogy, forward/backward trace, recall simulation/execution, packaging/pallet hierarchy and complaint-to-recall linkage.
- **M29 Maintenance / OEE Upgrade:** equipment lifecycle, PM, MTBF/MTTR, downtime/OEE, calibration, predictive signals, work orders and production scheduling integration.
- **M30 AI Decision & Simulation:** observe/analyze/decide/simulate/approve/execute/learn, confidence/explanations, risk-tier autonomy, rollback and outcome tracking.
- **M31 API / Event Architecture:** headless partner API, scoped credentials/OAuth/API keys, webhooks/events/outbox/retry/DLQ/idempotency, integration observability.
- **M32 Advanced Production Planning:** shift/day/week/month/campaign/resource/order/section planning, finite capacity, changeover/CIP/tank/utility/QC/material constraints, freeze horizons, scenarios and planning KPIs.
- **M33 Warehouse / Inventory Enterprise Upgrade:** hierarchy/bins/zones, stock states, FEFO, reservation/allocation, putaway/replenishment/waves, barcode/GS1/license plates, cycle count, cross-border/WIP/QC integration.
- **M34 Strategic Procurement Upgrade:** PR/RFQ/quotation comparison/PO/receipt/bill/landed cost, blanket/tender/split awards, supplier pricing/scorecards, import/subcontracting, approvals, portal and analytics.
- **M35 QC / QA Enterprise Upgrade:** specs/QCP/templates, incoming/in-process/final/logistics checks, holds/releases, NCR/CAPA/deviation, supplier quality, sampling/AQL/SPC, COA/retain samples, complaints/audits/change control/training dependencies.

---

# Preserved Historical Deferred / Blocked Work

These are not erased by the new roadmap.

- [D] **Historical TASK-012 — Local staging environment setup**
  - Deferred intentionally; existing compose/configuration retained.
- [P] **Historical TASK-019 — Document Management, Knowledge Base & E-Sign hardening**
  - Existing UI/API/service work retained.
  - Binary file storage adapter/upload pipeline and migration ownership/live-DB verification remain outstanding.
- [!] **Historical TASK-020 — Integration credentials / provider enablement**
  - External credentials/provider choices remain manual blockers where applicable.
- [P] **Historical TASK-021 — Push / checkpoint / staging verification family**
  - Preserve existing branch/push/checkpoint status from history; do not reinterpret as feature incompleteness.
- [P] **Historical TASK-022 — Data cleanup / local production-data normalization family**
  - Preserve local/manual nature; do not silently run destructive cleanup.

---

# H!veAI Current State

- **Current Phase:** M00 — Governance & Repository Baseline
- **In Progress:** Existing-system audit M01-M19
- **Completed in Last Run:** M00.S03.T002 — M02 Authentication / RBAC audit, classified PARTIAL with strong existing controls and bounded session/production-verification gaps
- **Next Immediate Task:** M00.S03.T003 — Audit M03 Master Data
- **Blockers:** No blocker for repository audit. External credentials/provider choices and local/live environment verification remain deferred to their mapped tasks.
