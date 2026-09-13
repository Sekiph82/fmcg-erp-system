# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

The previous canonical tracker has been preserved without reinterpretation as `TASKS_HISTORY.md`. Any task marked Done in that historical tracker is accepted as Done for migration purposes. M00 does not reopen completed historical work merely to re-audit it. M00 exists to reconcile the current repository, historical task state, and the planned M20-M35 enterprise enhancements so this ledger can become an accurate current roadmap before new enhancement implementation begins.

`PLANS.md` remains architecture/strategy reference only and is not a competing task tracker.

---

## Project Status

- **Current Milestone:** M00 — Governance & Repository Baseline
- **Current Sprint:** M00.S01 — Canonical Tracker Migration & Baseline Reconciliation
- **Current Task:** M00.S01.T003 — Build repository/current-plan comparison framework
- **Current Task Status:** IN_PROGRESS
- **Next Task/Action:** Complete M00 source-of-truth inventory, then execute module-by-module baseline comparison against M01-M35.
- **Required Actor:** BUILDER / AUDITOR
- **Tracking Repository:** Sekiph82/fmcg-erp-system
- **Tracking Branch:** main
- **Enhancement Gate:** M20-M35 implementation is locked until M00 reconciliation and full strict pre-enhancement audit are complete.

## Status Legend

- `[x]` DONE — accepted complete, including Done states migrated from `TASKS_HISTORY.md`
- `[~]` IN_PROGRESS — active work
- `[ ]` PLANNED — planned but not started
- `[!]` BLOCKED — waiting on dependency, credential, decision, external system, or owner action
- `[-]` SUPERSEDED — retained for history but replaced by a later task
- `[A]` AUDIT_REQUIRED — implementation state must be determined by M00 before scheduling new work
- `[P]` PARTIAL — implementation exists but remaining scope is known

## Canonical Tracking Rules

1. `TASKS.md` is the only active project-status ledger.
2. `TASKS_HISTORY.md` is immutable historical/reference evidence. It is not a second current tracker.
3. Existing historical tasks are not deleted. Historical task IDs must remain traceable when migrated into milestone/sprint/task structure.
4. If `TASKS_HISTORY.md` says a task is Done, migration accepts it as Done.
5. Manual Tasks, Help Tasks, Local Staging Tasks, Data Cleanup Tasks, blocked credential tasks, and other historical task families remain in scope and must be mapped, not discarded.
6. M00 must compare actual repository implementation with the proposed M20-M35 enhancement scopes before those enhancement milestones are treated as missing work.
7. M00 may classify planned enhancement scope as `ALREADY_DONE`, `PARTIAL`, `MISSING`, `SUPERSEDED`, or `NOT_APPLICABLE`.
8. After M00 reconciliation, this file must be rewritten to reflect the discovered current state, dependencies, and remaining work.
9. No M20-M35 implementation work may begin until the M00 strict pre-enhancement audit gate is closed and its P0/P1 findings are triaged.
10. Every meaningful implementation, audit, remediation, manual dependency change, or acceptance decision must update this file in the same GitHub workstream.
11. Builder claims do not silently convert an active task to Done when explicit audit or owner acceptance is required by that task.
12. Do not create a competing TODO/STATUS/PROGRESS tracker.

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

M00 is the mandatory truth-reconciliation milestone. It must establish what already exists before new enterprise enhancement work is scheduled. Its job is not to invalidate historical Done tasks. Its job is to prevent duplicate implementation and convert the roadmap into an evidence-based current plan.

## M00.S01 — Canonical Tracker Migration & Baseline Reconciliation

- [x] **M00.S01.T001 — Preserve previous canonical tracker as TASKS_HISTORY.md**
  - Preserve the exact previous tracker blob as historical evidence.
  - Do not rewrite historical Done/Pending/Blocked claims during migration.

- [x] **M00.S01.T002 — Establish new root TASKS.md as the canonical H!veAI ledger**
  - Use milestone → sprint → task hierarchy.
  - Preserve historical IDs through migration metadata when individual tasks are remapped.

- [~] **M00.S01.T003 — Build repository/current-plan comparison framework**
  - Compare repository implementation, `TASKS_HISTORY.md`, `PLANS.md`, and M01-M35 scope.
  - Required classification per capability: `ALREADY_DONE`, `PARTIAL`, `MISSING`, `SUPERSEDED`, `NOT_APPLICABLE`.
  - Never assume M20-M35 are entirely new.

- [ ] **M00.S01.T004 — Inventory all historical task families**
  - Import all current numbered tasks visible in the historical tracker, including TASK-001 through TASK-027 and nested/subtasks.
  - Import Manual Tasks.
  - Import Help Tasks.
  - Import Local Staging Tasks.
  - Import Data Cleanup Tasks.
  - Import blocked credential/vendor/manual dependency tasks.
  - Preserve historical task title, status, priority, evidence, tests, result, limitations, and Git references where available.

- [ ] **M00.S01.T005 — Map historical tasks to M01-M19 without deleting or reopening Done work**
  - Add `Historical Task ID` field to migrated cards.
  - Keep ambiguous items in an explicit migration queue until M00 classification closes.

## M00.S02 — Repository Capability Inventory

- [ ] **M00.S02.T001 — Backend architecture and module inventory**
- [ ] **M00.S02.T002 — Frontend routes/pages/components inventory**
- [ ] **M00.S02.T003 — Database models/migrations/schema inventory**
- [ ] **M00.S02.T004 — API/router/service inventory**
- [ ] **M00.S02.T005 — Background jobs, queues, schedulers, websocket/event mechanisms inventory**
- [ ] **M00.S02.T006 — CSV/import/export/reporting infrastructure inventory**
- [ ] **M00.S02.T007 — Integration provider/capability inventory**
- [ ] **M00.S02.T008 — Tests, CI, Docker, deployment and environment inventory**
- [ ] **M00.S02.T009 — Documentation/reference inventory**

## M00.S03 — Existing-System Module Audit M01-M19

Each task must record what exists, what is partial, what is missing, and the related historical tasks. Do not reclassify accepted historical Done items merely because a stricter future standard exists; instead create explicit upgrade/remediation scope where required.

- [ ] **M00.S03.T001 — Audit M01 Platform / Infrastructure**
- [ ] **M00.S03.T002 — Audit M02 Authentication / RBAC**
- [ ] **M00.S03.T003 — Audit M03 Master Data**
- [ ] **M00.S03.T004 — Audit M04 Product / Material / Supplier Master**
- [ ] **M00.S03.T005 — Audit M05 Warehouse & Inventory**
- [ ] **M00.S03.T006 — Audit M06 Procurement**
- [ ] **M00.S03.T007 — Audit M07 Sales / Distributor Operations**
- [ ] **M00.S03.T008 — Audit M08 Production Core**
- [ ] **M00.S03.T009 — Audit M09 Recipes / BOM**
- [ ] **M00.S03.T010 — Audit M10 Quality**
- [ ] **M00.S03.T011 — Audit M11 Maintenance**
- [ ] **M00.S03.T012 — Audit M12 Utilities**
- [ ] **M00.S03.T013 — Audit M13 Finance / Costing**
- [ ] **M00.S03.T014 — Audit M14 HR / Operator / Shift**
- [ ] **M00.S03.T015 — Audit M15 Reporting / Analytics**
- [ ] **M00.S03.T016 — Audit M16 AI**
- [ ] **M00.S03.T017 — Audit M17 Integrations**
- [ ] **M00.S03.T018 — Audit M18 Kenya Localization**
- [ ] **M00.S03.T019 — Audit M19 Security / Deployment / Hardening**

## M00.S04 — M20-M35 Existing-vs-Planned Cross-Comparison

For every enhancement milestone, compare the detailed intended capability against the current codebase. Every sub-capability must receive one of the required classifications and evidence links/file paths.

- [ ] **M00.S04.T001 — Reconcile M20 Master Production Scheduling with existing planning/MRP implementation**
- [ ] **M00.S04.T002 — Reconcile M21 Advanced BOM / Fluid-to-Unit with existing recipe/BOM implementation**
- [ ] **M00.S04.T003 — Reconcile M22 Production Order / Work Order with existing production models/workflows**
- [ ] **M00.S04.T004 — Reconcile M23 Shop Floor Execution with existing execution/operator interfaces**
- [ ] **M00.S04.T005 — Reconcile M24 Material Flow with existing inventory/production movement logic**
- [ ] **M00.S04.T006 — Reconcile M25 Cross-Border / Landed Cost with existing procurement/inventory/finance logic**
- [ ] **M00.S04.T007 — Reconcile M26 Machine & Operator Intelligence with existing machine/HR/production metrics**
- [ ] **M00.S04.T008 — Reconcile M27 Quality Gates with existing QC blocking/release flows**
- [ ] **M00.S04.T009 — Reconcile M28 Full Traceability with existing batch/lot/genealogy implementation**
- [ ] **M00.S04.T010 — Reconcile M29 Maintenance / OEE Upgrade with existing maintenance/OEE features**
- [ ] **M00.S04.T011 — Reconcile M30 AI Decision & Simulation with existing AI prediction/recommendation/scenario features**
- [ ] **M00.S04.T012 — Reconcile M31 API / Event Architecture with existing REST/websocket/event/integration architecture**
- [ ] **M00.S04.T013 — Reconcile M32 Advanced Production Planning with existing shift/day/week/month/machine/order/section planning**
- [ ] **M00.S04.T014 — Reconcile M33 Warehouse / Inventory Enterprise Upgrade with existing warehouse/inventory implementation**
- [ ] **M00.S04.T015 — Reconcile M34 Strategic Procurement Upgrade with existing purchasing/supplier/RFQ implementation**
- [ ] **M00.S04.T016 — Reconcile M35 QC / QA Enterprise Upgrade with existing quality/spec/NCR/CAPA/QA implementation**

## M00.S05 — Strict Pre-Enhancement Full System Audit

This is the mandatory strict audit requested before project enhancement begins. Unlike historical migration, this audit is intentionally strict and forward-looking.

- [ ] **M00.S05.T001 — Full backend architecture audit**
- [ ] **M00.S05.T002 — Full frontend architecture audit**
- [ ] **M00.S05.T003 — Database/schema/migration integrity audit**
- [ ] **M00.S05.T004 — API contracts/routes/service boundary audit**
- [ ] **M00.S05.T005 — Authentication/RBAC/security authorization audit**
- [ ] **M00.S05.T006 — Master-data integrity audit**
- [ ] **M00.S05.T007 — Warehouse/inventory transaction integrity audit**
- [ ] **M00.S05.T008 — Procurement workflow audit**
- [ ] **M00.S05.T009 — Sales/distributor/order-to-cash audit**
- [ ] **M00.S05.T010 — Production/BOM/planning/execution audit**
- [ ] **M00.S05.T011 — QC/QA/traceability audit**
- [ ] **M00.S05.T012 — Maintenance/utilities/asset integration audit**
- [ ] **M00.S05.T013 — Finance/costing/accounting audit**
- [ ] **M00.S05.T014 — HR/operator/shift/payroll integration audit**
- [ ] **M00.S05.T015 — AI grounding/safety/explainability/execution audit**
- [ ] **M00.S05.T016 — External integrations and provider readiness audit**
- [ ] **M00.S05.T017 — Kenya localization/eTIMS/M-Pesa/statutory readiness audit**
- [ ] **M00.S05.T018 — Cross-module data-flow and referential-integrity audit**
- [ ] **M00.S05.T019 — Import/export/CSV/data-cleanup audit**
- [ ] **M00.S05.T020 — Performance/scalability/background-job audit**
- [ ] **M00.S05.T021 — Deployment/Docker/CI/observability audit**
- [ ] **M00.S05.T022 — Full tests/build/runtime verification**
- [ ] **M00.S05.T023 — Consolidated P0/P1/P2/P3 findings register**

## M00.S06 — Canonical Roadmap Regeneration

- [ ] **M00.S06.T001 — Merge historical task migration results into M01-M19**
- [ ] **M00.S06.T002 — Mark M20-M35 sub-capabilities already implemented as ALREADY_DONE**
- [ ] **M00.S06.T003 — Convert partial M20-M35 capabilities into bounded remediation/upgrade tasks**
- [ ] **M00.S06.T004 — Remove duplicate planned work by marking it SUPERSEDED_BY_EXISTING_IMPLEMENTATION, never by deleting history**
- [ ] **M00.S06.T005 — Add newly discovered missing work from strict audit**
- [ ] **M00.S06.T006 — Recalculate milestone/sprint dependency graph**
- [ ] **M00.S06.T007 — Set current milestone/sprint/task from evidence-based priority**
- [ ] **M00.S06.T008 — Update milestone progress summary from reconciled task states**
- [ ] **M00.S06.T009 — Owner review of regenerated canonical roadmap**
- [ ] **M00.S06.T010 — Close M00 gate and authorize first post-audit implementation milestone**

### M00 Exit Criteria

M00 may close only when:
1. historical task families are represented in this ledger;
2. M01-M19 current implementation is classified;
3. every M20-M35 capability has been compared against actual implementation;
4. strict full-system audit is complete;
5. P0/P1 findings are triaged into tasks;
6. this `TASKS.md` has been regenerated from those findings;
7. the owner accepts the resulting roadmap.

---

# M01-M19 — Existing-System Milestone Containers

These milestone containers are intentionally not declared empty. Their detailed task cards will be populated during M00 migration from `TASKS_HISTORY.md` and repository evidence. Historical Done states are preserved.

## M01 — Platform / Infrastructure
- [A] M01.S00.T001 — M00 migration/reconciliation placeholder for existing platform/infrastructure tasks

## M02 — Authentication / RBAC
- [A] M02.S00.T001 — M00 migration/reconciliation placeholder for existing authentication/RBAC tasks

## M03 — Master Data
- [A] M03.S00.T001 — M00 migration/reconciliation placeholder for existing master-data tasks

## M04 — Product / Material / Supplier Master
- [A] M04.S00.T001 — M00 migration/reconciliation placeholder for product/material/supplier tasks

## M05 — Warehouse & Inventory
- [A] M05.S00.T001 — M00 migration/reconciliation placeholder for existing warehouse/inventory tasks

## M06 — Procurement
- [A] M06.S00.T001 — M00 migration/reconciliation placeholder for existing procurement tasks

## M07 — Sales / Distributor Operations
- [A] M07.S00.T001 — M00 migration/reconciliation placeholder for sales/distributor tasks

## M08 — Production Core
- [A] M08.S00.T001 — M00 migration/reconciliation placeholder for existing production tasks

## M09 — Recipes / BOM
- [A] M09.S00.T001 — M00 migration/reconciliation placeholder for recipe/BOM tasks

## M10 — Quality
- [A] M10.S00.T001 — M00 migration/reconciliation placeholder for existing quality tasks

## M11 — Maintenance
- [A] M11.S00.T001 — M00 migration/reconciliation placeholder for maintenance tasks

## M12 — Utilities
- [A] M12.S00.T001 — M00 migration/reconciliation placeholder for utilities tasks

## M13 — Finance / Costing
- [A] M13.S00.T001 — M00 migration/reconciliation placeholder for finance/costing tasks

## M14 — HR / Operator / Shift
- [A] M14.S00.T001 — M00 migration/reconciliation placeholder for HR/operator/shift tasks

## M15 — Reporting / Analytics
- [A] M15.S00.T001 — M00 migration/reconciliation placeholder for reporting/analytics tasks

## M16 — AI
- [A] M16.S00.T001 — M00 migration/reconciliation placeholder for existing AI tasks

## M17 — Integrations
- [A] M17.S00.T001 — M00 migration/reconciliation placeholder for integration tasks

## M18 — Kenya Localization
- [A] M18.S00.T001 — M00 migration/reconciliation placeholder for eTIMS, M-Pesa and Kenya-localization tasks

## M19 — Security / Deployment / Hardening
- [A] M19.S00.T001 — M00 migration/reconciliation placeholder for security/deployment/hardening tasks

---

# M20-M35 — Provisional Enterprise Enhancement Backlog

**Global status:** AUDIT_REQUIRED / IMPLEMENTATION_LOCKED_BY_M00

The scope below is a planning baseline, not a claim that the capability is absent. M00.S04 must compare each milestone against the actual repository before implementation tasks are activated.

## M20 — Master Production Scheduling
- [A] M20.S00.T001 — Reconcile demand aggregation, forecast, confirmed sales, safety stock, incoming supply, net requirements, production suggestions, procurement suggestions, priority logic, capacity awareness and MPS UI.

## M21 — Advanced BOM / Fluid-to-Unit
- [A] M21.S00.T001 — Reconcile multi-level BOM, formulation BOM, packaging BOM, bulk-to-unit conversion, dynamic scaling, yield/loss, alternatives, by-products, versions and recursive explosion.

## M22 — Production Order / Work Order
- [A] M22.S00.T001 — Reconcile production-order lifecycle, routing-generated work orders, split/merge, partial completion, rework, material linkage, time/cost capture and execution status.

## M23 — Shop Floor Execution
- [A] M23.S00.T001 — Reconcile operator terminal, start/pause/resume/finish, real-time quantities, scrap, downtime, shift/team handover, supervisor controls and QC triggers.

## M24 — Material Flow
- [A] M24.S00.T001 — Reconcile one/two/three-step manufacturing flows, staging, WIP, bulk/intermediate/tank handling, packaging issue, returns, scrap and quality-state-aware movements.

## M25 — Cross-Border / Landed Cost
- [A] M25.S00.T001 — Reconcile import shipments, in-transit stock, customs/freight/insurance/handling costs, allocation methods, partial receipts, valuation adjustments and milestone tracking.

## M26 — Machine & Operator Intelligence
- [A] M26.S00.T001 — Reconcile machine master, operator/team assignment, runtime, labor time, productivity, energy assumptions, machine/labor cost contributions and analytics.

## M27 — Quality Gates
- [A] M27.S00.T001 — Reconcile incoming/in-process/final quality gates, measured checks, blocking logic, quarantine/hold/release state transitions and escalation.

## M28 — Full Traceability
- [A] M28.S00.T001 — Reconcile forward/backward genealogy, supplier lot → intermediate → FG → customer trace, split/merge/rework relationships and recall simulation.

## M29 — Maintenance / OEE Upgrade
- [A] M29.S00.T001 — Reconcile equipment master, preventive/corrective maintenance, downtime linkage, MTBF, MTTR, OEE, maintenance scheduling and production-planning awareness.

## M30 — AI Decision & Simulation
- [A] M30.S00.T001 — Reconcile scenario simulation, cost/time/quality impact, recommendations, confidence/explanations, accepted/rejected feedback and predicted-vs-actual learning.

## M31 — API / Event Architecture
- [A] M31.S00.T001 — Reconcile REST/headless API, external integration scopes, events, alerts, webhooks, subscriptions, audit/event history, auth/rate-limit/idempotency readiness.

## M32 — Advanced Production Planning
- [A] M32.S00.T001 — Reconcile planning by shift/day/week/month, machine/line/work-center/section/order/product/campaign, finite/infinite capacity, changeovers/CIP, constraints and scenario planning.

## M33 — Warehouse / Inventory Enterprise Upgrade
- [A] M33.S00.T001 — Reconcile warehouse hierarchy, zones/bins, stock states, reservations, allocation/FIFO/FEFO, pick/pack/stage, replenishment, cycle count, traceability, in-transit and barcode/mobile readiness.

## M34 — Strategic Procurement Upgrade
- [A] M34.S00.T001 — Reconcile purchase requests, RFQ/tender, supplier quotations, comparison matrix, purchase orders, blanket/rate contracts, vendor-item master, supplier scorecards, imports, subcontracting and approvals.

## M35 — QC / QA Enterprise Upgrade
- [A] M35.S00.T001 — Reconcile specification master, control points/check types, incoming/process/final QA, release/hold/reject, NCR, CAPA, supplier quality, quality reviews, evidence/documents and analytics.

---

# Historical Migration Queue

The exact detailed historical cards remain preserved in `TASKS_HISTORY.md` until M00.S01.T004/T005 maps them into the milestone hierarchy. Nothing in this queue may be dropped merely because it predates the milestone structure.

## Numbered Historical Tasks

- [A] TASK-001 — migrate under appropriate M01-M19 milestone; preserve historical status (known historical status: Done)
- [A] TASK-002 — migrate under appropriate milestone; preserve historical status/blocker and AI credential/manual dependency state
- [A] TASK-003 — migrate under appropriate milestone; preserve historical status/blocker and M-Pesa credential/manual dependency state
- [A] TASK-004 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-005 — migrate from TASKS_HISTORY.md with all nested eTIMS subtasks and status unchanged
- [A] TASK-006 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-007 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-008 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-009 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-010 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-011 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-012 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-013 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-014 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-015 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-016 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-017 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-018 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-019 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-020 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-021 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-022 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-023 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-024 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-025 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-026 — migrate from TASKS_HISTORY.md with status unchanged
- [A] TASK-027 — migrate from TASKS_HISTORY.md with status unchanged

## Additional Historical Task Families

- [A] **MANUAL-TASKS** — migrate every manual/owner-dependent task; keep `Required Actor: HUMAN` where applicable.
- [A] **HELP-TASKS** — migrate all Help Tasks into their owning functional milestone while retaining `Task Type: HELP`.
- [A] **LOCAL-STAGING-TASKS** — migrate all local staging tasks, normally under M01 or M19 according to scope, retaining `Task Type: LOCAL_STAGING`.
- [A] **DATA-CLEANUP-TASKS** — migrate all data cleanup tasks into the affected domain milestone, retaining `Task Type: DATA_CLEANUP`.
- [A] **BLOCKED-CREDENTIAL/PROVIDER-TASKS** — retain all credential, sandbox/provider-selection, accountant/tax-advisor and other external blockers.

---

# Task Card Contract

When M00 migrates or creates a detailed task, use this structure:

```text
### MXX.SYY.TZZZ — Task Title

- Status: PLANNED / READY / IN_PROGRESS / PARTIAL / IMPLEMENTATION_COMPLETE / AWAITING_AUDIT / CHANGES_REQUIRED / AWAITING_OWNER_ACCEPTANCE / DONE / BLOCKED / SUPERSEDED
- Historical Task ID: <if applicable>
- Task Type: BUILD / AUDIT / REMEDIATION / MANUAL / HELP / LOCAL_STAGING / DATA_CLEANUP / INTEGRATION / DOCS
- Priority: P0 / P1 / P2 / P3
- Module:
- Sprint:
- Milestone:
- Required Actor: BUILDER / AUDITOR / HUMAN
- Objective:
- Why it matters:
- Current evidence:
- Dependencies:
- Implementation scope:
- Acceptance criteria:
- Do not touch:
- Risk: LOW / MEDIUM / HIGH / CRITICAL
- Started at:
- Implementation completed at:
- Audited at:
- Accepted at:
- Changed files:
- Created files:
- Deleted files:
- Tests / checks:
- Audit result:
- Owner acceptance:
- Result:
- Known limitations:
- Git commit / branch:
- Notes:
```

---

# Immediate Execution Order

1. Finish M00.S01 historical task-family inventory and migration mapping.
2. Complete M00.S02 repository capability inventory.
3. Complete M00.S03 M01-M19 baseline module audit.
4. Complete M00.S04 M20-M35 existing-vs-planned cross-comparison.
5. Run M00.S05 strict pre-enhancement full system audit.
6. Regenerate this ledger through M00.S06 from evidence.
7. Obtain owner roadmap acceptance.
8. Only then activate the first required implementation/remediation milestone.

Until step 7 is complete, M20-M35 remain planning containers, not implementation instructions.
