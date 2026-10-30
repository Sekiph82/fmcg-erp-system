# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

`TASKS_HISTORY.md` preserves the previous detailed tracker as immutable/reference evidence. Historical Done states remain accepted. `PLANS.md` is architecture/strategy reference only. No other file is an active competing tracker.

---

## Project Status

- Current Milestone: M31 — API / Event Architecture
- Current Sprint: M31.S03 — Delivery Engine
- Current Task: M31.S03.T003 — Dead-letter/replay
- Current Task Status: COMPLETE
- Next Task/Action: M31.S03.T004 — Webhook signing/secret rotation
- Required Actor: CODEX
- Tracking Repository: Sekiph82/fmcg-erp-system
- Tracking Branch: main
- M00 Gate: COMPLETE

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
9. The owner authorizes the active Codex task runner as the tracker writer for this project. Update `TASKS.md` only for explicit current-task claims, accepted transitions, and matching owner answers; the dashboard and independent reviewer are read-only. Keep `TASKS_HISTORY.md` immutable.
10. Builder logs are evidence claims, not acceptance by themselves.
11. `main` is the only authorized branch. Builders must not create, restore, push, or work on legacy `hiveai*` branches unless ChatGPT explicitly authorizes a temporary branch.

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
- [x] M01.S02.T005 — Complete production document binary storage/upload pipeline
  Evidence: [CODEX_LOG_V01.md](coordination/sessions/M01.S02.T005/CODEX_LOG_V01.md). Added persistent local file storage, bounded/type-checked upload, SHA-256, fail-closed optional malware scanning, scan-gated download/approval, race-safe lifecycle transitions, and frontend upload/download flow. Focused PostgreSQL disposable-database route test passed 16/16; unit tests 18/18; frontend type-check and both Compose configuration checks passed. See [GAP-012 document audit](docs/planning/GAP-012_DOCUMENT_KNOWLEDGE_AUDIT.md) and [implementation notes](docs/planning/GAP-012_DOCUMENT_KNOWLEDGE_IMPLEMENTATION_NOTES.md).

## M01.S03 — Runtime Reliability
- [x] M01.S03.T001 — Prove always-running background/event dispatch ownership
  Evidence: [source audit log](coordination/sessions/M01.S03.T001/CODEX_LOG_V01.md); verified no resident worker/scheduler in dev/prod compose, FastAPI lifespan, or dependencies, and found dispatch only on manual API paths. Independent read-only review found no remaining finding. This closes the ownership proof only; no dispatcher, runtime delivery, database durability, or production operation is claimed.
- [x] M01.S03.T002 — Validate migration ownership on live-like database
- [D] M01.S03.T003 — Execute LOCAL-STAGING-001 when deployment environment is available
- [x] M01.S03.T004 — Establish operational backup/restore rehearsal evidence
  Evidence: [M01.S03.T002 verification log](coordination/sessions/M01.S03.T002/CODEX_LOG_V01.md); a fresh disposable PostgreSQL 16.6 database upgraded from empty to the single Alembic head 20261029_0025. All 645 current ORM tables were present; selected PK/FK/index checks matched; task container cleanup and all seven evidence SHA-256 hashes were independently verified. `alembic check` FAILED, proposing removals of 15 migration-owned legacy tables and 187 indexes absent from current ORM metadata; no destructive changes were applied. Independent read-only review found no remaining findings. This proves fresh local migration behavior only, not production acceptance.

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
- [x] M02.S03.T001 — Implement/verify refresh-token rotation lifecycle
  Evidence: [T001 closeout](coordination/milestones/M02/evidence/v01/t001-local-20261023/CLOSEOUT.md)
- [x] M02.S03.T002 — Implement inactivity/session-expiry policy
  Evidence: [T002 closeout](coordination/milestones/M02/evidence/v01/t002-local-20261023/CLOSEOUT.md)
- [x] M02.S03.T003 — Prove user-wide issued-session revocation
  Evidence: [T003 closeout](coordination/milestones/M02/evidence/v01/t003-local-20261023/CLOSEOUT.md)
- [x] M02.S03.T004 — Enforce privileged-role 2FA policy
  Evidence: [T004 closeout](coordination/milestones/M02/evidence/v01/t004-local-20261023/CLOSEOUT.md)
- [x] M02.S03.T005 — Verify CSRF and tenant/company isolation in production-like runtime
  Evidence: [T005 closeout](coordination/milestones/M02/evidence/v01/t005-local-20261023/CLOSEOUT.md)

---

# M03 — Master Data

**Status: PARTIAL**

## M03.S01 — Shared Master Framework
- [x] M03.S01.T001 — Company/organizational master foundation
- [x] M03.S01.T002 — Custom fields/values/validation/layout framework
- [x] M03.S01.T003 — Bulk import framework
- [x] M03.S01.T004 — Audit and permission infrastructure

## M03.S02 — Governance Upgrade
- [x] M03.S02.T001 — Standardize duplicate detection across masters
  Evidence: [T001 closeout](coordination/milestones/M03/evidence/v01/t001-local-20261023/CLOSEOUT.md)
- [x] M03.S02.T002 — Standardize merge/deactivation semantics
  Evidence: [T002 correction log V02](coordination/sessions/M03.S02.T002/CLAUDE_LOG_V02.md); disposable PostgreSQL migration and 27 focused tests passed; independent read-only review found no remaining T002 defect at `8c8c58e`.
- [x] M03.S02.T003 — Standardize version/effective-date governance
  Evidence: [T003 implementation log V01](coordination/sessions/M03.S02.T003/CODEX_LOG_V01.md); fresh PostgreSQL migration upgrade/downgrade/re-upgrade and 10 focused tests passed; MPS recipe-selection regressions 2/2 passed; independent read-only review findings corrected.
- [x] M03.S02.T004 — Define master-data stewardship workflow
  Evidence: [T004 implementation log V01](coordination/sessions/M03.S02.T004/CODEX_LOG_V01.md); 38 focused tests passed (4 database-gated skips), disposable PostgreSQL migration and atomic audit/rollback test passed, frontend type-check and targeted ESLint passed, and final independent read-only review reported no remaining blocker. Implementation commit: `c317a03bd1f3fd933f0eb3a4e34952f71d0620f3`.
- [x] M03.S02.T005 — Validate referential integrity across master domains
  Evidence: [T005 implementation log V01](coordination/sessions/M03.S02.T005/CODEX_LOG_V01.md); disposable PostgreSQL 18.6 migration upgrade and focused integration tests passed (2/2); Python compile, single Alembic head, and diff checks passed; independent read-only review found no remaining blocker. Implementation commit: `bd959937cdc953e44a9c8c8cae0c5cb9526004e3`.

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
- [x] M05.S03.T001 — Validate reservation/allocation consistency
  Evidence: [M05.S03.T001 verification log](coordination/sessions/M05.S03.T001/CODEX_LOG_V01.md); fresh PostgreSQL 16.6 migration to head 20261029_0025; 9 task-specific integrity tests passed; a combined run with related sales access/delegation tests reported 18 passed, including real lock-wait, competing allocation, stale stock/line refresh, cancellation release, partial dispatch, and no duplicate stock movement. Independent read-only review found no remaining findings; exact task container/tmpfs cleanup verified. No production acceptance claimed.
- [x] M05.S03.T002 — Validate transaction integrity across production/procurement/sales
  Evidence: [M05.S03.T002 verification log](coordination/sessions/M05.S03.T002/CODEX_LOG_V01.md); fresh PostgreSQL 16.6 at single migration head 20261029_0025; 7 task-specific transaction tests and 23 related procurement/production/sales regressions passed. Late-failure rollback, repeated-post guards, cross-module stock/source links, actor attribution, and unchanged finance journal/batch counts verified with synthetic data. Independent read-only review found no remaining material findings; exact disposable-container cleanup verified. No production acceptance claimed.
- [x] M05.S03.T003 — Validate negative-stock/concurrency safeguards
  Evidence: [M05.S03.T003 verification log](coordination/sessions/M05.S03.T003/CODEX_LOG_V01.md); fresh PostgreSQL 16.6 at single migration head 20261029_0025; 5 focused negative-stock/concurrency tests and 23 related procurement/production/sales regressions passed. Real PostgreSQL lock waits verified that duplicate GRN posts and duplicate production completions are serialized; limited shared material could not be over-consumed. Independent read-only review found no remaining material issues; exact disposable-container cleanup verified. No production acceptance claimed.

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
- [x] M06.S03.T001 — Verify three-way-match transaction chain
  Evidence: [M06.S03.T001 execution log](coordination/sessions/M06.S03.T001/CODEX_LOG_V01.md); fresh PostgreSQL 16.6 at single Alembic head 20261029_0025; 5 focused three-way-match tests and 12 procurement/accounting regressions passed. Tests verified draft GRN hold, posted PO/GRN/stock and match linkage, cumulative zero-remaining overbilling, cross-supplier rejection, rerun idempotency and late-failure rollback. Independent read-only review found no remaining material issues; exact disposable-container cleanup verified. No AP/GRNI/GL or production acceptance claimed.
- [x] M06.S03.T002 — Verify landed-cost accounting integration
  Evidence: [M06.S03.T002 execution log](coordination/sessions/M06.S03.T002/CODEX_LOG_V01.md); current-main source matched the accepted M13 landed-cost implementation with no intervening landed-cost changes. Fresh PostgreSQL 16.6 at single Alembic head 20261029_0025; existing landed-cost acceptance suite passed 12/12 and GAP-002 posting-helper regressions passed 6/6. Independent read-only review found no material mismatch; exact disposable-container cleanup verified. No supplier-invoice/AP/GRNI, live-provider or production acceptance claimed.
- [x] M06.S03.T003 — Verify supplier performance data completeness
  Evidence: [M06.S03.T003 execution log](coordination/sessions/M06.S03.T003/CODEX_LOG_V01.md); corrected supplier master/dashboard performance rollup to one rounded historical average. Fresh PostgreSQL 16.6 database at `20261029_0025 (head)`; 9 focused completeness/regression tests passed, including the 79.165 → 79.17 rounding case. Independent read-only review found no remaining material issue; task container removed and absence verified. No owner-data, unified ESG/food-safety scorecard, or production acceptance claimed.

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
- [x] M07.S03.T001 — Verify order-to-cash accounting closure
  Evidence: [M07.S03.T001 execution log](coordination/sessions/M07.S03.T001/CODEX_LOG_V01.md); configured invoice/tax and cash/bank/M-Pesa GL posting, shared payment APIs, account consistency, transactional failure guards, and cent-consistent invoice rounding. Fresh PostgreSQL 16.6 synthetic database at migration head 20261029_0025; 17 focused order-to-cash/GAP-001/GAP-002 tests passed, exact disposable container removed and absence verified, independent read-only re-review confirmed fixes. Code commit 77cc488a943f6ef75712cc8b3495e170dbce9587 pushed to origin/main with [skip ci]. No live COA/provider/tax or production acceptance claimed.
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
- [x] M08.S03.T001 — Harden state-transition invariants
- [x] M08.S03.T002 — Verify production/inventory transaction atomicity
- [x] M08.S03.T003 — Verify production/QC/finance closure
  Evidence: [CODEX implementation log](coordination/sessions/M08.S03.T003/CODEX_LOG_V01.md); production completion now preserves explicit source-lot genealogy, creates and quarantines traceable finished-goods QC, blocks unsafe QC acceptance/release, and costing rollup is protected against incomplete orders and concurrent duplicate rollups with finance RBAC. Disposable PostgreSQL 16 at Alembic head 20261029_0025: 26 T003 tests and 5 T002 production/inventory regressions passed; focused local regressions 27 passed/7 disposable-DB gated skips, Python compilation and diff checks passed, and task container cleanup was verified. No live factory acceptance, GL posting, or central inventory valuation policy is claimed. Independent read-only findings were addressed; this log is implementer evidence, not an independent audit verdict.

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
- [x] M09.S02.T004 — Standardize effective-date/version governance
  Completed opaque nonblank version/revision and inclusive, open-ended date-window governance across API, clone, BOM creation UI, and PostgreSQL; see [implementation evidence](coordination/sessions/M09.S02.T004/CODEX_LOG_V01.md), [GAP-021 audit](docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_AUDIT.md), [GAP-021 implementation notes](docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_IMPLEMENTATION_NOTES.md), and the M20 recipe/effectivity audit referenced by [M03.S02.T003 evidence](coordination/sessions/M03.S02.T003/CODEX_LOG_V01.md).

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
- [x] M10.S02.T004 — Harden hold/release transaction enforcement
  Evidence: [CODEX implementation log](coordination/sessions/M10.S02.T004/CODEX_LOG_V01.md); hold/release creation and mutation serialize on a locked unique per-lot status row; existing broad and warehouse-scoped quality permissions are enforced across all warehouses holding the lot. Five permission tests and two disposable PostgreSQL concurrency/rollback tests passed; independent read-only review found no actionable issue.

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
- [x] M13.S03.T001 — Verify landed-cost posting chain
  Evidence: [implementation log](coordination/sessions/M13.S03.T001/CODEX_LOG_V01.md); disposable PostgreSQL 16.6 integration tests passed 12/12, existing posting-helper regressions passed 6/6, compilation and diff checks passed, isolated container removed, and independent read-only review found no remaining findings. Implementation commit: 64dcc82eaf70c3b50649830937f2433cd57c9845. No production or live-provider acceptance is claimed.
  Baseline: landed-cost allocation exists; the finance/inventory audit identifies stock-value and GL posting linkage as remaining verification gaps. See `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`.
- [!] M13.S03.T002 — Validate live bank integration when credentials exist
- [!] M13.S03.T003 — Validate live eTIMS posting when credentials exist
- [x] M13.S03.T004 — Rehearse period close/reconciliation on staging/live-like DB
  Evidence: [CODEX log](coordination/sessions/M13.S03.T004/CODEX_LOG_V01.md); exact-HEAD disposable PostgreSQL 16.6 rehearsal passed 5/5, migration head applied, period-close/posting/permission/concurrency assertions passed, container removed, independent review found no remaining issue. No live provider or production acceptance claimed.

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
- [x] M19.S02.T001 — Production-like penetration/security verification
  Evidence: [CODEX log](coordination/sessions/M19.S02.T001/CODEX_LOG_V01.md)
- [x] M19.S02.T002 — Tenant/company isolation verification
  Evidence: [CODEX log](coordination/sessions/M19.S02.T002/CODEX_LOG_V01.md)
- [x] M19.S02.T003 — Session-lifecycle remediation from M02
  Evidence: [CODEX log](coordination/sessions/M19.S02.T003/CODEX_LOG_V01.md)
- [!] M19.S02.T004 — Production provider-secret deployment verification
- [D] M19.S02.T005 — Staging/live DB migration rehearsal pending environment
- [x] M19.S02.T006 — Residual repository anomaly/dead-code cleanup
  Evidence: [CODEX log](coordination/sessions/M19.S02.T006/CODEX_LOG_V01.md)

---

# M20 — Master Production Scheduling

**Status: IN_PROGRESS / PARTIAL existing capability**
**Depends on:** M08, M09, M15; M00 complete.
**Acceptance: OPEN / PARTIAL — see `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V05.md`; the owner authorized explicitly synthetic virtual-factory assumptions for demo/integration acceptance, and those fixtures are implemented. Independent re-audit and the remaining technical/evidence gates are still pending.**

## M20.S01 — MPS Domain Reconciliation
- [x] M20.S01.T001 — Map existing MPS models/APIs/UI/services to enterprise requirements
- [x] M20.S01.T002 — Preserve existing planning-board/capacity/campaign/what-if capabilities
- [x] M20.S01.T003 — Identify exact missing state/data invariants
- [x] M20.S01.T004 — Define MPS acceptance dataset and regression suite

## M20.S02 — Demand & Supply Coupling
- [x] M20.S02.T001 — Consolidate demand inputs: sales orders/forecast/safety stock
- [x] M20.S02.T002 — Couple MPS demand to available/on-order inventory
- [x] M20.S02.T003 — Couple MPS to BOM/material feasibility
- [x] M20.S02.T004 — Expose shortage/constraint reasons per planned line

## M20.S03 — Capacity & Campaign Planning
- [x] M20.S03.T001 — Validate work-center/machine capacity calculations
- [x] M20.S03.T002 — Harden campaign grouping/sequencing
- [x] M20.S03.T003 — Validate changeover/CIP effects where data exists
- [x] M20.S03.T004 — Persist capacity overload diagnostics

## M20.S04 — Approval, Release & Scenarios
- [x] M20.S04.T001 — Harden draft→approve→release semantics
- [x] M20.S04.T002 — Enforce permissions/audit trail on approval/release
- [x] M20.S04.T003 — Persist what-if scenario assumptions/results
- [x] M20.S04.T004 — Compare scenarios using service/cost/capacity KPIs

## M20.S05 — MPS Verification
- [x] M20.S05.T001 — Backend MPS regression tests
- [x] M20.S05.T002 — Frontend planning-board/capacity/campaign/what-if tests
- [x] M20.S05.T003 — Cross-module MPS→MRP/production verification
- [x] M20.S05.T004 — Close M20 with evidence and tracker update

---

# M21 — Advanced BOM / Fluid-to-Unit

**Status: IMPLEMENTATION TASKS COMPLETE / MILESTONE CLOSURE GATED BY M20**
**Depends on:** M09, M20.

## M21.S01 — Conversion Model
- [x] M21.S01.T001 — Define bulk-fluid→pack conversion profile model
  Evidence: [CODEX log](coordination/sessions/M21.S01.T001/CODEX_LOG_V01.md)
- [x] M21.S01.T002 — Support density/UOM conversion rules
  Evidence: [CODEX log](coordination/sessions/M21.S01.T002/CODEX_LOG_V01.md); disposable PostgreSQL suite passed 18 tests through migration `20261028_0017`; NaN/±infinity density rejected with HTTP 422 and covered by tests.
- [x] M21.S01.T003 — Support package component quantities by SKU/size
  Evidence: [CODEX log](coordination/sessions/M21.S01.T003/CODEX_LOG_V01.md); disposable PostgreSQL suite passed 8 tests through migration `20261028_0017`, including SKU-matched packaging BOM lines and configured CARTON→PCS scaling.
- [x] M21.S01.T004 — Version/effective-date conversion profiles
  Evidence: [CODEX log](coordination/sessions/M21.S01.T004/CODEX_LOG_V01.md); migration `20261028_0018` passed on a disposable PostgreSQL 16 database; 10 database tests and 31 focused unit tests passed; frontend type-check and Python compilation passed; independent review found no blocker.

## M21.S02 — Yield & Loss
- [x] M21.S02.T001 — Model expected process yield
  Evidence: [CODEX log](coordination/sessions/M21.S02.T001/CODEX_LOG_V01.md); expected output/input percentage is optional and nullable; migration `20261028_0019` passed in the disposable PostgreSQL run; 6 focused tests, frontend type-check, Python compilation, and independent review passed. No default yield was fabricated.
- [x] M21.S02.T002 — Model filling/packaging loss and spillage
  Evidence: [CODEX log](coordination/sessions/M21.S02.T002/CODEX_LOG_V01.md); separate filling, packaging-reject, and spillage categories persist through migration `20261028_0020`; 8 disposable PostgreSQL tests and 7 focused unit tests passed; frontend type-check and independent review passed.
- [x] M21.S02.T003 — Separate standard vs actual yield/loss
  Evidence: [CODEX log](coordination/sessions/M21.S02.T003/CODEX_LOG_V01.md); recipe-item standards are snapshotted by material/UOM, variance is exposed in API/UI, migration 20261028_0021 passed in disposable PostgreSQL, 9 focused Python tests and frontend type-check passed, and independent review found no blocker.
- [x] M21.S02.T004 — Feed variances into costing/reporting
  Evidence: [CODEX log](coordination/sessions/M21.S02.T004/CODEX_LOG_V01.md); order and product yield-loss cost exposure is reported separately from finalized cost and total variance, 8 focused Python tests, frontend type-check, Python compilation, and independent review passed.

## M21.S03 — Advanced BOM Structures
- [x] M21.S03.T001 — Nested/intermediate BOM support verification
  Evidence: [CODEX log](coordination/sessions/M21.S03.T001/CODEX_LOG_V01.md); nested BOM recursion now fails closed on missing/incompatible/cyclic/over-depth/invalid-quantity structures, repeated intermediate BOMs aggregate correctly, 40 focused tests passed and the disposable PostgreSQL runner passed 10 tests; independent review found no remaining blocker.
- [x] M21.S03.T002 — Multi-output/co-product/by-product semantics
  Evidence: [CODEX log](coordination/sessions/M21.S03.T002/CODEX_LOG_V01.md); co-/by-product quantities now appear as separate output lines, with no cost credits; synthetic PostgreSQL integration, focused unit test, frontend type-check, and independent review passed.
- [x] M21.S03.T003 — Alternate/substitute component governance
  Evidence: [CODEX log](coordination/sessions/M21.S03.T003/CODEX_LOG_V01.md); real per-role planner/quality approvals, independent approvers, emergency and shortage rules, direct-BOM binding, master/UOM checks, and quantity/policy freshness enforcement implemented. Python compilation, 13 focused backend tests, frontend type-check, disposable PostgreSQL integration, diff check, and independent review passed.
- [x] M21.S03.T004 — BOM explosion integrity tests
  Evidence: [CODEX log](coordination/sessions/M21.S03.T004/CODEX_LOG_V01.md); leaf aggregation now preserves item/component identity and UOM, fails closed when a leaf has no identity; focused backend regression 43 passed/1 database-dependent skipped, Python compilation, frontend type-check, diff check and independent review passed.

## M21.S04 — UI/API/Import
- [x] M21.S04.T001 — Advanced BOM/conversion API contracts
  Evidence: [CODEX log](coordination/sessions/M21.S04.T001/CODEX_LOG_V01.md); backend/frontend conversion-profile request/response and package-components contracts aligned, positive finite source quantity enforced, DB-precision validation, 50 backend tests passed/2 disposable-DB tests skipped, frontend type-check, OpenAPI generation and independent review passed.
- [x] M21.S04.T002 — Conversion-profile UI
  Evidence: [CODEX log](coordination/sessions/M21.S04.T002/CODEX_LOG_V01.md); conversion profile product/BOM selectors, bounded form validation, and explicit target-SKU packaging calculation added; frontend type-check and diff check passed; independent review found and the UI fixed stale result display on input changes.
- [x] M21.S04.T003 — CSV import/export support
  Evidence: [CODEX log](coordination/sessions/M21.S04.T003/CODEX_LOG_V01.md); conversion profiles use the existing validate-before-import CSV flow and expose active-profile export; product/BOM relation validation, duplicate protection, and spreadsheet formula escaping added; frontend type-check, Python compilation, module wiring/template checks, diff check, and independent review passed.
- [x] M21.S04.T004 — Permissions/audit/history
  Evidence: [CODEX log](coordination/sessions/M21.S04.T004/CODEX_LOG_V01.md); conversion-profile creation writes an actor-attributed audit event transactionally, selected-profile history uses the existing audit endpoint and `audit.view` permission, and audit IP comes from a validated socket peer; frontend type-check, Python compilation, diff check, and independent review passed.

## M21.S05 — Verification
- [x] M21.S05.T001 — Unit/conversion/yield tests
  Evidence: [CODEX log](coordination/sessions/M21.S05.T001/CODEX_LOG_V01.md); 62 focused unit tests passed, six disposable PostgreSQL migration/integration suites passed (17, 7, 6, 8, 10, 10), and 27 supplemental API/yield-cost tests passed; task container cleanup and independent review verified.
- [x] M21.S05.T002 — MPS/MRP integration tests
  Evidence: [CODEX log](coordination/sessions/M21.S05.T002/CODEX_LOG_V01.md); disposable PostgreSQL integration passed after migration to head, proving completed MRP result → linked MPS quantity → approved BOM with 10% process loss and G-to-KG conversion → 0.1556 KG material-short diagnostic; container cleanup and independent read-only review passed.
- [x] M21.S05.T003 — Costing integration tests
  Evidence: [CODEX log](coordination/sessions/M21.S05.T003/CODEX_LOG_V01.md); fresh task-owned PostgreSQL integration passed through real compute/finalize/report queries, exposed 10 KES yield-loss cost variance separately from unchanged 0 total cost, and passed cleanup and independent read-only review.
- [!] M21.S05.T004 — Close M21
  Blocked: M20 local acceptance is PASS under the owner-approved synthetic virtual-factory assumptions, but the M20 milestone remains BLOCKED_EVIDENCE while remote CI is `DEFERRED_CI_QUOTA` through 2026-10-30; M21 depends on M20 closure. No real factory or employee data is required. See [M20 strict re-audit V06](coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md) and [closure assessment](coordination/sessions/M21.S05.T004/CODEX_LOG_V01.md).

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

**Status: DONE — defined synthetic cross-border and landed-cost software scope complete; live customs/KRA, legal, provider, and production acceptance remain outside scope.**
**Depends on:** M06, M13, M18.

## M25.S01 — Cross-Border Shipment Lifecycle
- [x] M25.S01.T001 — Purchase→shipment→container linkage
  Evidence: `coordination/sessions/M25.S01.T001/CODEX_LOG_V01.md`; disposable PostgreSQL V03 and mocked frontend checks passed, with earlier corrected failures and scope limits recorded.
- [x] M25.S01.T002 — In-transit inventory ownership/status
  Evidence: `coordination/sessions/M25.S01.T002/CODEX_LOG_V01.md`; migration 0035, task-owned disposable PostgreSQL V04 (1 passed), mocked frontend V04 (2 passed), targeted type-check/ESLint, and independent read-only review. Incoterm is not used to infer title; real legal ownership is not claimed.
- [x] M25.S01.T003 — Customs/clearance milestone model
  Evidence: `coordination/sessions/M25.S01.T003/CODEX_LOG_V01.md`; migration 0036, synthetic disposable PostgreSQL V03 (1 passed), mocked Playwright V02 (2 passed), targeted type-check/ESLint/compile checks, and independent read-only review. No KRA integration or verified legal/customs claims.
- [x] M25.S01.T004 — Kenya receipt closure
  Evidence: Revision 0037; disposable PostgreSQL integration 1 passed; mocked Chromium Playwright 2 passed; frontend type-check and targeted ESLint passed; backend compileall and diff check passed; independent read-only review passed. Synthetic records only; no live KRA, physical delivery, or complete-PO receipt claim.

## M25.S02 — Landed Cost Components
- [x] M25.S02.T001 — Freight/insurance/customs/port/local charges
  Evidence: Canonical LandedCostType enforced for new line inputs; 16 category/compatibility tests passed; targeted compileall and diff check passed; independent read-only review passed. Historical custom labels remain readable. Synthetic/software records only; no real freight/customs invoices or accounting posting claim.
- [x] M25.S02.T002 — Allocation methods by value/weight/volume/quantity
  Evidence: Allocation bases VALUE/QUANTITY/WEIGHT/VOLUME plus equal split; accepted volume input and guarded migration 20261029_0038; disposable PostgreSQL migration rehearsal and 19 tests passed; frontend type-check and targeted ESLint passed; compileall and independent read-only review passed. Synthetic data only; no financial posting claim. Evidence: coordination/sessions/M25.S02.T002/CODEX_LOG_V01.md
- [x] M25.S02.T003 — Estimated vs actual landed cost
  Evidence: Revision 20261029_0039; disposable PostgreSQL migration/service checks 4 passed; focused M25.S02 tests 37 passed and 1 skipped (T003 DB check separately passed); frontend type-check, targeted ESLint, compileall, diff check, and independent read-only review passed. Synthetic data only; posted actuals are variance-only, no new GL posting claim. Evidence: coordination/sessions/M25.S02.T003/CODEX_LOG_V01.md
- [x] M25.S02.T004 — Currency/exchange-rate handling
  Evidence: Revision 20261029_0040; disposable PostgreSQL migration/adoption/service/guard checks 8 passed; focused landed-cost/M13 tests 45 passed and 13 skipped (DB case separate); frontend type-check and targeted ESLint, Python compileall, diff check, and independent read-only review passed. Synthetic data only; no live FX provider or new GL posting claim. Evidence: coordination/sessions/M25.S02.T004/CODEX_LOG_V01.md

## M25.S03 — Accounting & Valuation
- [x] M25.S03.T001 — Inventory valuation posting
  Evidence: Implemented atomic GRN stock and inventory valuation posting with configured FIFO, WEIGHTED_AVG, or STANDARD cost; added finance permission, safe legacy handling, balanced posting links, and four-decimal reconciliation. Disposable PostgreSQL: M25 16 passed; related M05/M06 suites 7+5+5 passed; 7 helper tests passed, 11 M13 DB cases skipped behind their separate database gate; frontend type-check/targeted ESLint and Python compile passed; independent final review found no blockers. Evidence: coordination/sessions/M25.S03.T001/CODEX_LOG_V01.md.
- [x] M25.S03.T002 — Variance/accrual posting
  Evidence: Implemented separate idempotent landed-cost actual variance posting with FIFO remaining-stock/consumed-cost split, configured accrual clearing and expense entries, immutable original journal, finance permission, guarded 20261029_0041 migration, and UI state/action. Fresh task-owned disposable PostgreSQL migration to 0041 head and 8 integration tests passed; related regressions 11 passed/17 skipped; frontend type-check/targeted ESLint, Python compileall/Ruff, diff-check, and independent read-only review passed. Synthetic data only; no AP/tax or invoice authenticity claim. Evidence: coordination/sessions/M25.S03.T002/CODEX_LOG_V01.md.
- [x] M25.S03.T003 — Reconciliation and audit trail
  Evidence: Added finance.view-protected read-only reconciliation API and landed-cost audit timeline/UI covering source GRN identity, allocation totals, event/batch/journal linkage and balances, inventory adjustments, saved-rate actual variances, exceptions, pending states, and actor/timestamp evidence. Disposable PostgreSQL migration to 20261029_0041: 8 passed; frontend type-check/targeted ESLint, backend py_compile, git diff --check passed; independent read-only review found no blockers. Synthetic data only. Evidence: coordination/sessions/M25.S03.T003/CODEX_LOG_V01.md.
- [x] M25.S03.T004 — Close M25
  Evidence: [M25 closure log](coordination/sessions/M25.S03.T004/CODEX_LOG_V01.md); all 12 M25 task logs are present and the defined synthetic software scope has bounded integration, migration, API/UI, regression, audit, and independent-review evidence. No live customs/KRA, legal title, physical delivery, supplier-invoice/AP/tax/payment, live-provider, real-factory, or production acceptance is claimed. Next dependency-ready task selected: M31.S01.T001 based on completed M01/M02 baselines and M17.S01 foundations; M17 live-provider gates remain open.

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

**Status: DONE — M27 quality-gate scope complete; broader HACCP/GAP-017 work remains open.**
**Depends on:** M10; integrates with M06/M22/M23/M24/M33.

## M27.S01 — Gate Definition Engine
- [x] M27.S01.T001 — Configurable gate types/triggers
  Evidence: [CODEX implementation log](coordination/sessions/M27.S01.T001/CODEX_LOG_V01.md); configurable quality gate type/trigger catalog, API, migration, and dedicated permission are implemented. Focused contract/database checks passed 12/12 on disposable PostgreSQL; independent read-only review found no remaining issue.
- [x] M27.S01.T002 — Required tests/specification linkage
  Evidence: [CODEX implementation log](coordination/sessions/M27.S01.T002/CODEX_LOG_V01.md); linked required QC templates and type-appropriate specifications, protected active-gate integrity across template edits/deletes and concurrent activation, migration applied on disposable PostgreSQL, 29 contract/regression tests and 5 disposable PostgreSQL tests passed; independent read-only review found no remaining issue.
- [x] M27.S01.T003 — Gate severity/mandatory/waiver rules
  Evidence: [CODEX implementation log](coordination/sessions/M27.S01.T003/CODEX_LOG_V01.md); added configurable severity/mandatory/waiver rules with critical-gate and waiver safeguards, DB-enforced migration, 38 contract/regression tests and 6 disposable PostgreSQL tests passed; independent read-only review found no material issue.
- [x] M27.S01.T004 — Version/effective-date governance
  Evidence: [CODEX implementation log](coordination/sessions/M27.S01.T004/CODEX_LOG_V01.md); added sequential gate versions, inclusive as-of date filtering, no-overlap checks, and immutable started versions with one-time closure; fresh disposable PostgreSQL migration and 7 DB tests passed, 39 contract/regression tests passed; independent review found no remaining issue.

## M27.S02 — Transaction Enforcement
- [x] M27.S02.T001 — Receiving gate
  Evidence: [CODEX implementation log](coordination/sessions/M27.S02.T001/CODEX_LOG_V01.md); mandatory ON_RECEIPT gates block GRN posting until each accepted line has accepted/passed required incoming QC, backed by template-authoritative results and serialized inspection/configuration changes. Fresh disposable PostgreSQL 16 migration to 20261029_0031 and combined suite passed 47 tests; independent read-only review found no remaining issue.
- [x] M27.S02.T002 — Production release/in-process gate
  Evidence: [CODEX implementation log](coordination/sessions/M27.S02.T002/CODEX_LOG_V01.md); mandatory production-release and in-process gates enforce accepted/passed template inspections before status transitions and before completion side effects. Production inspections derive order scope; in-process inspections must follow actual start. Fresh disposable PostgreSQL 16 migration through 20261029_0031 and production-gate DB test passed; 42 focused/regression tests passed and 12 DB-only tests skipped; independent read-only review found no remaining material issue.
- [x] M27.S02.T003 — Finished-goods release gate
  Evidence: [CODEX implementation log](coordination/sessions/M27.S02.T003/CODEX_LOG_V01.md); mandatory inventory/ON_FINISHED_GOODS_RELEASE gates keep lot stock quarantined until every linked FG QC template is complete and accepted/passed, with traceable receipt/order/lot scope, template-authoritative results, and serialized release. Fresh disposable PostgreSQL 16 migration through 20261029_0031 and DB integration test passed; 48 focused/regression tests passed, 7 DB-only cases skipped; independent read-only review findings were fixed and cleared.
- [x] M27.S02.T004 — Dispatch gate
  Evidence: [CODEX implementation log](coordination/sessions/M27.S02.T004/CODEX_LOG_V01.md); active mandatory sales/ON_DISPATCH quality gates require lot traceability, all linked FG QC templates accepted/passed, and no unresolved mandatory FG inspections before any stock, movement, shipment, or sales-order mutation. Fresh disposable PostgreSQL 16 migration through 20261029_0031 and dispatch DB integration test passed; 54 focused/regression tests passed, 7 DB-only cases skipped; independent read-only review found no material issue.

## M27.S03 — Exceptions
- [x] M27.S03.T001 — Hold/quarantine enforcement
  Evidence: [CODEX implementation log](coordination/sessions/M27.S03.T001/CODEX_LOG_V01.md); lot holds now block physical stock across warehouses while preserving reservations, release rechecks mandatory QC/active FG gates, and dispatch rejects held or unreleased lots even without dispatch-gate configuration. Fresh disposable PostgreSQL 16 migration through 20261029_0031 and T001 DB integration passed; dispatch DB regression passed; 36 focused tests passed, 7 DB-only cases skipped; independent read-only review findings were fixed and cleared.
- [x] M27.S03.T002 — Deviation/waiver approval
  Evidence: [CODEX implementation log](coordination/sessions/M27.S03.T002/CODEX_LOG_V01.md); implemented a version- and scope-specific waiver lifecycle with reasoned request, independent quality approval/rejection, 24-hour expiry, revocation, warehouse-scope authorization, and gate-operation serialization. Gate checks accept only an active waiver for missing required-template evidence; critical gates, failed/unresolved inspections, and hold/quarantine controls remain blocking. Deviation resolution/closure now requires documented corrective context and independent quality review. Fresh disposable PostgreSQL 16 migration through 20261029_0032 and waiver integration passed; 72 focused tests passed; independent read-only review cleared all findings.
- [x] M27.S03.T003 — NCR/CAPA escalation linkage
  Evidence: [CODEX implementation log](coordination/sessions/M27.S03.T003/CODEX_LOG_V01.md); HIGH/CRITICAL deviations now receive same-transaction CAPA escalation, while lower-severity deviations can be explicitly linked. Reciprocal one-to-one trigger/pointer, exact scope and severity checks, scoped permissions, and verified-CAPA resolution/closure are enforced. Fresh disposable PostgreSQL 16 at migration head 20261029_0032; task integration 1/1 and focused quality regressions 22 passed (1 DB-gated skip). Independent read-only review found no remaining blocker; task container cleanup verified.
- [x] M27.S03.T004 — Gate audit history
  Evidence: [CODEX implementation log](coordination/sessions/M27.S03.T004/CODEX_LOG_V01.md); receiving, production, finished-goods, and dispatch gate outcomes now persist in an append-only audit table with version/policy snapshots, actor and scope/business linkage, and a scoped read API. Blocked decisions commit independently of rolled-back business transactions; UPDATE, DELETE, and TRUNCATE are rejected by PostgreSQL triggers. Fresh disposable PostgreSQL 16 migration through 20261029_0033 and three task DB tests passed; 47 focused gate and regression tests passed; independent review found no remaining blocker; task container cleanup verified.

## M27.S04 — Verification
- [x] M27.S04.T001 — Gate-engine unit tests
  Evidence: [CODEX implementation log](coordination/sessions/M27.S04.T001/CODEX_LOG_V01.md); added 37 focused unit tests for gate selection, waiver scope, template-type compatibility, policy validation, and inclusive effective windows. Focused suite and compile check passed; independent read-only review found no issue.
- [x] M27.S04.T002 — Cross-module blocking tests
  Evidence: [CODEX implementation log](coordination/sessions/M27.S04.T002/CODEX_LOG_V01.md); synthetic QMS lot hold was verified across Inventory and Sales dispatch on a fresh disposable PostgreSQL 16 database. Migration to `20261029_0033`, integration test 1/1, and 118 focused gate regressions passed; shipment, sales order, stock issue ledger, and reserved stock remained unchanged on block. Independent review cleared the test and runner; task container cleanup verified.
- [x] M27.S04.T003 — UI/E2E acceptance
  Evidence: [CODEX implementation log](coordination/sessions/M27.S04.T003/CODEX_LOG_V01.md); added the Quality Gates UI for definition history, actor-attributed audit outcomes, first and sequential version setup, and required-template linkage with API-aligned view/configuration permissions. Targeted ESLint and frontend type-check passed; mocked Playwright UI/E2E acceptance passed 4/4; independent review found no issue.
- [x] M27.S04.T004 — Close M27
  Evidence: [CODEX closure log](coordination/sessions/M27.S04.T004/CODEX_LOG_V01.md); all M27 definition, enforcement, exception, audit, and verification tasks have linked bounded evidence. Quality Gates scope is closed; HACCP/GAP-017 gaps and live production acceptance remain explicitly outside this closure.

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
- [x] M31.S01.T001 — API client/application registry
  Evidence: Added owner-scoped, integrations.view/edit-protected API application registry and portal UI; credentials remain separate. Task-owned PostgreSQL migration/API suite: 4 passed at 20261029_0042 head, including schema adoption/creation, invalid-shape/default/check rejection, safe downgrade and writer-lock cases; frontend type-check and targeted ESLint, backend py_compile, diff check and independent review passed. Synthetic only. Evidence: coordination/sessions/M31.S01.T001/CODEX_LOG_V01.md.
- [x] M31.S01.T002 — API key/OAuth credential lifecycle
  Evidence: M31.S01.T002 credential lifecycle implemented; disposable PostgreSQL 2 passed, migration/downgrade/adoption checks passed; backend compile, frontend type-check, targeted ESLint, diff check passed; independent read-only review no blockers. Synthetic software scope only; no API-key auth or OAuth token protocol.
- [x] M31.S01.T003 — Scope/rate-limit policy
  Evidence: Scope/rate policy implemented in backend and developer UI; disposable PostgreSQL tests 2 passed on 20261029_0043 (synthetic data, loopback only); backend syntax, frontend TypeScript, targeted ESLint and diff checks passed; independent read-only review no blockers. Values remain metadata until API-key authentication is enabled.
- [x] M31.S01.T004 — Partner audit/usage analytics
  Evidence: Partner lifecycle auditing and owner-scoped usage analytics implemented; T004 disposable PostgreSQL 2 passed (secret-free lifecycle audit, permissions/ownership, synthetic usage summaries, future-date exclusion, IP redaction); T003 scope/rate regression 2 passed; backend compile, frontend TypeScript, targeted ESLint, diff check passed; independent read-only review no blockers. Automatic API-key usage capture remains disabled until API-key authentication exists.

## M31.S02 — Event Contract
- [x] M31.S02.T001 — Canonical domain event envelope
  Evidence: Canonical versionless envelope, legacy normalization/filter-template compatibility, and contract docs implemented. Focused pytest 5 passed; py_compile and git diff --check passed; independent read-only review has no blockers.
- [x] M31.S02.T002 — Event versioning/schema governance
  Evidence: Versioned canonical event envelopes, validated Draft 2020-12 schemas, immutable version snapshots, admin-governed schema changes and API history implemented. Unit tests 17 passed/3 DB-gated skips; disposable PostgreSQL fresh and legacy upgrade/API tests 4 passed; backend compile, Alembic single head, frontend tsc/ESLint and diff checks passed; independent review no blockers.
- [x] M31.S02.T003 — Idempotency/correlation/causation IDs
  Evidence: Implemented event-type-scoped idempotency keys with request fingerprints and atomic PostgreSQL conflict handling; correlation/causation IDs propagate in canonical envelopes and inbound headers. Focused T001/T002/T003 tests: 21 passed; T003 disposable loopback PostgreSQL/API/concurrency suite: 3 passed; py_compile, Alembic single head 20261030_0002, diff check, and independent read-only review passed. See coordination/sessions/M31.S02.T003/CODEX_LOG_V01.md.
- [x] M31.S02.T004 — Transactional event creation/outbox strategy
  Evidence: Added transaction-local stage_event() for event and pending delivery rows plus a committing standalone wrapper; inbound event, delivery, and receive-counter writes commit atomically. Focused M31.S02 regressions/T004 unit tests: 22 passed; T004 disposable PostgreSQL/API transaction suite: 2 passed for commit, rollback, replay and conflict paths; py_compile, Alembic single head 20261030_0002, diff check and independent review passed. See coordination/sessions/M31.S02.T004/CODEX_LOG_V01.md.

## M31.S03 — Delivery Engine
- [x] M31.S03.T001 — Prove always-running dispatcher
  Evidence: Added a lifespan-managed polling dispatcher for pending and due retry deliveries, validated finite settings, and PostgreSQL SKIP LOCKED claims for multi-worker safety; documented shutdown and at-least-once limits. Focused M31.S02 regressions plus new dispatcher tests: 33 passed; py_compile and diff check passed; independent read-only review passed after a P2 finite-interval fix. See coordination/sessions/M31.S03.T001/CODEX_LOG_V01.md.
- [x] M31.S03.T002 — Retry/backoff
  Evidence: Defined max_retries as retries beyond the initial request, with bounded exponential equal jitter (60 seconds to one hour); exhausted attempts clear next_retry_at and zero retries dead-letters the initial failure. Focused dispatcher/outbox/event regression suite: 39 passed; py_compile and diff check passed; independent read-only review passed. See coordination/sessions/M31.S03.T002/CODEX_LOG_V01.md.
- [x] M31.S03.T003 — Dead-letter/replay
  Evidence: Added auditable, repeat-safe dead-letter and bulk replay lineage, superuser gates, and bounded fan-out. Focused T001-T003 suite: 41 passed, 2 skipped; task-owned disposable PostgreSQL tests: 3 passed; migration 20261030_0003 is the only head; py_compile, diff check, and independent read-only review passed. Details: coordination/sessions/M31.S03.T003/CODEX_LOG_V01.md.
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

## Questions for Şekip


## Owner Decisions

- Q-M21-S05-T004-M20-DATA | TASK: M21.S05.T004 | ANSWER: Use realistic, explicitly synthetic virtual-factory assumptions for M20 demo and integration acceptance because no physical factory or employees exist; Codex may create the virtual products, equipment, shifts, CIP, minimum-run, cost and test users. Never present these assumptions as live operating data. The existing independent read-only reviewer plus ChatGPT's strict acceptance review will assess the resulting evidence; no external factory auditor or owner data source is required.
- Q-M21-S03-T002-COSTING-BASIS | TASK: M21.S03.T002 | ANSWER: A) Maliyet toplamlarını değiştirme; co-product ve by-product miktarlarını çıktı olarak izle.
- Q-M21-S03-T003-APPROVAL-GOVERNANCE | TASK: M21.S03.T003 | ANSWER: Gerçek planlamacı/kalite onay akışı kur; EMERGENCY_ONLY için de kural belirle

- Q-M21-S02-T003-YIELD-SOURCE | TASK: M21.S02.T003 | ANSWER: B — recipe-item loss percentages are the standard source.
- Q-M21-S02-T001-YIELD-BASIS | TASK: M21.S02.T001 | ANSWER: B — expected process yield is a percentage of BOM input quantity.

- Q-M21-S02-T001-YIELD-BASIS | TASK: M21.S02.T001 | ANSWER: B — expected process yield is a percentage of BOM input quantity.

- Q-M19-S02-T006-SCOPE | TASK: M19.S02.T006 | ANSWER: T006 kapsamı yalnızca hiçbir yerde kullanılmadığı kanıtlanan kodun temizlenmesidir; sayfa yönlendirmeleri ve performans uyarıları kapsam dışıdır.

- Q-M01-S03-T004-OPS-ACCEPTANCE | TASK: M01.S03.T004 | ANSWER: Şekip Docker Desktop'ı açtı; bu, yerel sentetik ve tek kullanımlık PostgreSQL provası seçeneğinin kabulü olarak uygulandı.
- Q-M03-S02-T004-STEWARD-MODE | TASK: M03.S02.T004 | ANSWER: Uygun yetkiye sahip kullanıcı ana veri değişikliklerini doğrudan yapabilir; değişiklikler denetim kaydına alınmalıdır. Ayrı onay zorunlu değildir.
- Q-M03-S02-T002-MERGE-RULES | TASK: M03.S02.T002 | ANSWER: Evet. Önerilen güvenli birleştirme ve pasifleştirme kuralını kabul ediyorum.
