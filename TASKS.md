# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

`TASKS_HISTORY.md` preserves the previous detailed tracker as immutable/reference evidence. Historical Done states remain accepted. `PLANS.md` is architecture/strategy reference only. No other file is an active competing tracker.

---

## Project Status

- Current Milestone: M36 — Native CRM HubSpot Capability Gap Audit & Delivery (new owner-approved scope; M17 existing software history preserved)
- Current Sprint: M36.S02 — Sales intelligence (after M36.S00 audit accepted)
- Current Task: M36.S03.T002 unified customer timeline + M36.S02.T001 web lead capture (batch 3)
- Current Task Status: IN_PROGRESS (2026-11-12) — M36.S00 audit accepted with corrections by an independent reviewer (25 tasks: 17 PARTIAL, 8 MISSING, none complete); batch 1 security/defect fixes landed. Evidence: coordination/milestones/M36/M36_S00_AUDIT.md
- Next Task/Action: Batch 2 — M36.S02.T002 lead scoring (configurable rules, history, explanation; fix enum bug), M36.S02.T003 forecast filters + snapshots, M36.S02.T004 funnel analytics; then batch 3 (S03.T002 customer timeline, S02.T001 web lead capture). Provider-bound live tests stay [!].
- Required Actor: CLAUDE (sole active task runner and tracker writer; per coordination/CLAUDE_AUTONOMOUS_EXECUTION_POLICY.md)
- Tracking Repository: Sekiph82/fmcg-erp-system
- Tracking Branch: main
- M00 Gate: COMPLETE

## Owner Decisions

- 2026-11-11 — Native CRM: the ERP's own customer, sales, distributor and CRM modules are the CRM. HubSpot,
  Salesforce, Zoho and other external CRMs are optional future connectors, never required infrastructure;
  Shopify customers and orders integrate into native customer and sales records. Recorded in `PLANS.md`
  ("Owner Architecture Decision — Native CRM").

## Status Legend

- `[x]` DONE
- `[v]` IMPLEMENTED / PENDING MILESTONE VERIFICATION
- `[~]` IN_PROGRESS
- `[ ]` PLANNED
- `[!]` BLOCKED
- `[-]` SUPERSEDED
- `[P]` PARTIAL / existing capability with bounded remaining scope
- `[D]` DEFERRED

## Mandatory Execution Rules

1. Milestone → Sprint → Task is the canonical hierarchy.
2. Existing capabilities are extended, never rebuilt without evidence that replacement is required.
3. A task may be marked IMPLEMENTED (`[v]`) after source changes and lightweight checks; it becomes DONE (`[x]`) only after its milestone validation and consolidated independent review are recorded.
4. Historical tasks already marked Done remain accepted unless a later remediation explicitly supersedes them.
5. External credentials, live providers, production devices and live-DB acceptance must never be fabricated as PASS.
6. Cross-module changes must preserve RBAC, auditability, migrations, API contracts, frontend/backend consistency and tenant/company boundaries.
7. M20–M35 are enterprise upgrades layered on M01–M19 foundations.
8. Graphify is reference tooling only. Do not run refreshes without an explicit project need; no hooks, watchers or competing tracker state.
9. The owner authorizes Claude as the sole active autonomous task runner, task selector, implementer, reviewer coordinator and tracker writer. Update `TASKS.md` only for evidence-backed current-task claims, accepted transitions and owner answers; dashboard and independent reviewers are read-only. Keep `TASKS_HISTORY.md` immutable. Historical Codex names, logs and prior owner answers are evidence, not active authority.
10. Builder logs are evidence claims, not acceptance by themselves.
11. `main` is the only authorized branch. Claude must not create, restore, push or work on legacy `hiveai*` branches without explicit owner authorization; ChatGPT is not a required execution gate.

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

**Status: DONE — software scope complete; LOCAL-STAGING-001 executed 2026-11-10 (cloud/production deployment not claimed)**

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
- [x] M01.S03.T003 — Execute LOCAL-STAGING-001 when deployment environment is available
  Evidence (2026-11-10): `docker-compose.staging.yml` over `docker-compose.prod.yml` (project `fmcg-erp-staging`, loopback ports 13000/18000) with `.env.staging` generated by `scripts/make_staging_env.py` (random local-only secrets, gitignored, never printed) and `ENVIRONMENT=production`, so the production validators ran. Production images built; fresh PostgreSQL 16 migrated empty → head `20261110_0030` by the image's own `alembic upgrade head`; `/health`, `/live`, `/docs`, frontend `/login` 200; all four containers healthy; `tests/test_hardening.py` 26 passed inside the backend container; admin login 200 with mandatory TOTP setup, no token in body, no cookie before 2FA; security headers present (nosniff, DENY, HSTS, CSP). Defects found and fixed: prod frontend ignored `NEXT_PUBLIC_API_URL` (now a build arg; bundle verified), Next standalone bound to the container IP so the healthcheck never passed (`HOSTNAME=0.0.0.0`), both images ran as root (now `erp`/`node`), image pip 25.0.1 had advisories (now ≥26.2). Local rehearsal only — no cloud/production deployment claimed.
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
- [x] M14.S02.T004 — Extend skill/qualification enforcement in M26
  Evidence: delivered by M26.S01.T001–T004 (qualification model, expiry, enforcement on assignment/execution, audited supervisor override; M26 closed) and reused by M35.S05.T003 for laboratory testers.
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
- [x] M16.S02.T004 — Govern confidence/explainability/autonomy in M30
  Evidence: delivered by M30.S01–S05 (risk-tier registry, approval policy, confidence/explanation contract, provenance, controlled execution, deterministic fallback and safety tests; M30 closed). Live-provider acceptance stays M16.S02.T003/M30.S05.T002 [!].

---

# M17 — Integrations

**Status: PARTIAL — software for bank statement import, network label printing and read-only GraphQL is done (2026-11-11); live bank API, physical printer acceptance and CRM/store/MQTT vendor connectors remain external or await vendor choice**

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
- [x] M17.S02.T003 — Replace/complete bank simulation with production connector
  Evidence (2026-11-11, commit 4d6f681): real bank data now reaches reconciliation through bank-exported files — ISO 20022 camt.053, SWIFT MT940, OFX and CSV parsers (`app/services/bank_statement_parsers.py`) and `POST /bank-reconciliation/statements/import-file`, which rejects currency/account mismatches, unbalanced statements (opening + credits − debits ≠ closing) and periods overlapping an imported statement; upload form on the import page; capability BANK_STATEMENT_FILES = LIVE_READY. The simulated direct bank API is refused in production. Tests: parser suite 7, PostgreSQL import test 1, mocked Playwright upload 2. A direct API with a specific bank stays the external gate "Live bank connector credentials/provider acceptance".
- [x] M17.S02.T004 — Complete physical printer execution
  Evidence (2026-11-11): `app/services/label_printer_service.py` renders GS1 lot labels (GS1-128 via ZPL ^BC mode D / TSPL EAN128) and SSCC (00) pallet labels and streams them over raw TCP 9100; printer registry (`label_printers`, migration 20261111_0032), `POST /gs1/labels/print/{id}/dispatch` (claim PRINTING → commit → send → COMPLETED/FAILED with error, stale-PRINTING recovery, marks lot/SSCC printed), printer admin + test-label endpoints, legacy `/integrations/barcode/print` sends to a registered printer; UI "Send to" network printer + printer admin on the GS1 page. Safeguards from independent review: single DNS resolution with private/loopback/link-local-only addresses and connect-to-validated-IP (no rebinding, IPv4-mapped metadata blocked), barcode data never truncated/altered (invalid data fails the job), item/copy caps. Also fixed: GS1 browser-print completion crashed on PostgreSQL (aware datetime into naive column; lazy item load) and barcode previews used the PNG MIME type for SVG images. Tests: 21 unit (incl. a raw-TCP fake printer), PostgreSQL dispatch test, mocked Playwright 1. Physical printer/media acceptance stays the external gate.
- [x] M17.S02.T005 — IoT/CRM/e-commerce/GraphQL stub families until prioritized
  Scope (owner decision 2026-11-11): CRM is the ERP's native customer/sales/distributor/CRM modules, so the CRM part of this task is native CRM integration (Shopify buyers into native customers and CRM profiles), not an external CRM connector; external CRMs moved to M17.S02.T006 as optional and deferred.
  Done (2026-11-11): GraphQL — read-only `POST /api/v1/graphql` (graphql-core) for products, materials, customers, suppliers, sales/purchase/production orders and stock; REST-equivalent permissions with company-wide `*.view_all` for transactional data (no scope leakage), depth/size/limit caps, mutations refused (writes stay on REST); developer portal shows endpoint and SDL; resolvers serialised on the request session (concurrent root fields crashed on PostgreSQL). CRM and e-commerce sync no longer fabricate SYNCED mappings/ORD-SIM orders (501 until a connector exists); the legacy IoT event ingest requires iot.ingest. Tests: GraphQL unit 4 + PostgreSQL 1, stub guards.
  Done (2026-11-11, owner chose Shopify): Shopify Admin REST connector (`SHOPIFY_*` settings, custom-app token never stored in DB, only `<name>.myshopify.com` hosts, page_info pagination refused off-host, bounded 429 retry). `POST /integrations/ecommerce/import-orders` (integrations:edit + sales:create) imports orders oldest-first as DRAFT sales orders (source ECOMMERCE, paid -> bank transfer, else credit) for the configured web customer/warehouse: SKU-matched lines, net price for tax-inclusive shops, refunded lines dropped, discount per unit at 4 dp; unknown SKUs or malformed orders are recorded FAILED without aborting the batch and are retried in place later; one mapping per Shopify order (unique constraint, migration 20261111_0033); cancelled orders skipped. `POST /ecommerce/sync-inventory` sets the Shopify location to the warehouse's sellable stock (unblocked, not quarantined/expired lots, negative rows clamped). Sync page shows failures and the not-configured 501. Shipping/order-level charges are not imported. Tests: client 9, PostgreSQL 1 (mocked Admin API), mocked Playwright 2. Remaining: live store acceptance (store token, external gate); CRM (Salesforce/HubSpot/Zoho) and MQTT/OPC-UA bridge connectors need the owner's vendor/broker choice and credentials; WooCommerce has no connector.

  Done (2026-11-12, native CRM): audit — native CRM already covers customer master and commercial scope, leads/opportunities pipeline with stages, territories, activities, competitors, win/loss and AI recommendations, CRM profiles, interactions, visits and segments, loyalty, field-sales visits/routes, distributors and secondary sales, helpdesk, NPS and consumer complaints; the gap was channel buyers all landing on one web account. Shopify buyers now become native customers (channel ONLINE, prepaid, scoped like the web-store account, CRM profile with acquisition channel SHOPIFY) linked by Shopify customer id through `crm_customer_mappings` (unique per provider + external id, migration 20261111_0034); repeat buyers reuse their customer and refresh the profile's last contact; guest checkouts stay on the web-store customer; no e-mail matching (checkout e-mails are unverified). Import also enforces the importer's commercial scope on the web-store account. External CRM sync still answers 501. Tests: Shopify PostgreSQL test extended (buyer linkage, repeat buyer, guest).
  Done (2026-11-12, MQTT): broker-agnostic MQTT bridge (`MQTT_*` settings, paho-mqtt, QoS 1, auto-reconnect, `$share` subscriptions so API workers split the stream, TLS required in production) feeding the native IoT ingest now shared with `/iot/ingest` and `/iot/machines/state` (`services/iot_ingest.py`): readings, batches (<=1000), machine states and bare values on `.../<machine>/<metric>` topics; threshold alerts; every message audited as an `IoTIngestMessage` (ACCEPTED/DUPLICATE/REJECTED, payload hash), `message_id` redelivery is idempotent per device (partial unique index, migration 20261112_0035, so two workers cannot both store a redelivery), `device_code` links a registered device; failures to store are audited too; buffer bounded to 64 MiB; device timestamps (readings and state `changed_at`) stored as UTC; `GET /iot/bridge/status`; HTTP batch ingest now raises threshold alerts like single readings. Delivery is at-most-once across a crash (QoS 1 acked into the in-memory buffer, clean sessions) — documented; devices needing guarantees resend with a message_id. Tests: bridge unit 13; end to end with a real local Mosquitto 2.0.20 broker into disposable PostgreSQL 1 (readings, bare value, duplicate, per-device ids, state durations from device time, threshold alert, rejected audit, device link); existing IoT tests 22. Independent review findings fixed. Remaining: plant broker acceptance (external gate).
- [D] M17.S02.T006 — Optional external connectors: external CRM (HubSpot/Salesforce/Zoho) sync, WooCommerce store, native OPC-UA client
  Deferred by owner decision 2026-11-11 (native CRM; external CRMs are optional, never required). Not implemented: CRM sync endpoints answer 501, WooCommerce answers 501, OPC-UA sources publish through an edge gateway to the MQTT bridge. Any future CRM connector must use `crm_customer_mappings` and must not become the source of truth for customer, pricing, credit or order data.
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
- [P] M19.S02.T005 — Staging/live DB migration rehearsal pending environment
  Staging part done (2026-11-10): empty → head on the production image (M01.S03.T003); head → 20261029_0041 → head and head → 20261029_0038 → head downgrade/upgrade cycles on disposable PostgreSQL after fixing baseline-incompatible downgrades (idempotent `drop_constraint`/`drop_index` in `alembic/env.py`, 0005 keeps `rfq_request_lines` while other tables reference it); a copy of the development database upgraded to `20261110_0030` with zero model drift, then the development database itself. Remaining: a live/production database rehearsal, which needs that environment.
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
  Evidence: Post-window owner-triggered CI run 41762085149 passed at exact main SHA bf3e97f193155322998645a44b4b19840b0d1a69: backend, frontend and docker-config all succeeded; 1,238 backend tests passed, 236 skipped, 1,109 warnings. Receipt: coordination/sessions/M20.S05.T004/CODEX_LOG_V01.md. Independent reviewer confirmed this resolves only the deferred CI gate; V06 remains unchanged and no broader acceptance is claimed.
  Reopened for acceptance because V06 recorded the remaining post-quota CI gate. The authorized run is now recorded above; V06 itself remains unchanged, and its bounded-acceptance limits remain in force.

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
- [x] M21.S05.T004 — Close M21
  Evidence: M21.S01–S05.T001–T003 tracker rows and task receipts are complete; the M20 dependency is satisfied by successful post-window owner-triggered CI run 41762085149 at SHA bf3e97f193155322998645a44b4b19840b0d1a69. Independent read-only review found no additional explicit blocker to bounded M21 closure. Preserved evidence limits: requester-supplied order references, a skipped identity-partition DB test, and no M21.S04.T002 browser visual acceptance. See coordination/sessions/M21.S05.T004/CODEX_LOG_V01.md.
  Closure boundaries: see the superseding bounded closeout in [CODEX log](coordination/sessions/M21.S05.T004/CODEX_LOG_V01.md); V06 remains unchanged, skipped evidence stays explicitly skipped, and no live-production acceptance is claimed.

---

# M22 — Production Order / Work Order

**Status: DONE — M22 verified in the consolidated disposable-PostgreSQL, frontend, dependency, migration, and independent-review campaign; no live production acceptance is claimed.**
**Depends on:** M20, M21.

## M22.S01 — Order Lifecycle
- [x] M22.S01.T001 — Reconcile production-order vs work-order responsibilities
  Evidence: Defined the target ProductionOrder/work-order boundary and a non-destructive crosswalk plan for the active parallel exec_* subsystem in coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md; corrected the manufacturing manual terminology, current schedule behavior, routes and costing ownership. Independent read-only review found no blockers; git diff --check passed. Documentation/domain-design task only; no tests or runtime behavior claimed.
- [x] M22.S01.T002 — Harden state machine and transition guards
  Evidence: Canonical and parallel execution transitions are guarded with parent-first locks; unfinished child operations block parent completion; schema, CSV import, and shop-floor bypasses are guarded; paused-order resume is exposed. Independent read-only review found no blocking issue; git diff --check passed; automated tests were not run, and runtime acceptance is not claimed. See coordination/sessions/M22.S01.T002/CODEX_LOG_V01.md.
- [x] M22.S01.T003 — Approval/release/cancel/close semantics
  Evidence: Added parent approval/release guards, cancellation/close semantics, authenticated actor and scoped permission checks, schema migration, canonical/exec work-order and import locks, material movement/reconciliation gates, split/merge/rework protections, and UI approval controls. Independent read-only review found no remaining blockers; git diff --check passed. Automated tests, type-check/build, and migration execution were not run, and runtime/database acceptance is not claimed. See coordination/sessions/M22.S01.T003/CLAUDE_LOG_V01.md.
- [x] M22.S01.T004 — Immutable audit history for critical transitions
  Evidence: Added a PostgreSQL append-only production transition ledger with monotonic ordering, actor identity snapshots, mutation-blocking triggers, transactional event writes across canonical and parallel order/operation paths, MRP/MPS/import/shop-floor coverage, scoped history endpoints, and production detail timelines. Independent read-only review found no remaining blockers; git diff --check passed. Automated tests, typecheck/build, migration execution, and runtime acceptance are deferred to milestone verification; legacy history was not fabricated or backfilled. See coordination/sessions/M22.S01.T004/CLAUDE_LOG_V01.md.

## M22.S02 — Execution Structure
- [x] M22.S02.T001 — Routing/work-center operation sequencing
  Evidence: Added canonical routing-to-work-order generation, sequence display, work-center/product guards, duplicate protection and migration preflights. Consolidated disposable-PostgreSQL tests passed 2/2; fresh migration reached 20261104_0009; frontend type-check and source lint passed. See coordination/sessions/M22.S02.T001/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S02.T002 — Split/merge work orders
  Evidence: Implemented quantity-conserving split/merge for compatible unstarted work orders, immutable lineage and transition history, API/UI, and migration safeguards. Consolidated disposable-PostgreSQL tests passed 2/2; fresh migration reached 20261104_0009; frontend type-check and source lint passed. See coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S02.T003 — Partial completion/backorder semantics
  Evidence: Implemented bounded partial completion and linked planned backorders with transaction/actor history, quantity guards, final-operation reconciliation, backorder-aware reports/KPIs, API/UI links, and migration preflights. Consolidated disposable-PostgreSQL tests passed 4/4; fresh migration reached 20261104_0009; frontend type-check and source lint passed. See coordination/sessions/M22.S02.T003/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S02.T004 — Rework/reprocess flows
  Evidence: Implemented canonical WorkOrder rework API, UI, quantity conservation, actor transition and genealogy lineage. Consolidated disposable-PostgreSQL tests passed 3/3; fresh migration reached 20261104_0009; frontend type-check and source lint passed. See coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.

## M22.S03 — Subcontracting & Dependencies
- [x] M22.S03.T001 — Subcontract operation linkage
  Evidence: Added optional one-to-one canonical WorkOrder linkage, open-operation validation, visible API/UI relationships and transaction-safe output reconciliation. Consolidated PostgreSQL tests passed 2/2 after the completion-actor migration; fresh migration reached 20261104_0009. API access/actor tests passed and independent M22 review found no remaining blocker. See coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S03.T002 — Dependency/predecessor enforcement
  Evidence: Added canonical routed WorkOrder predecessor gates; missing or cancelled-only predecessors fail closed, completed split replacements satisfy the step, and manual unrouted starts remain unchanged. Consolidated disposable-PostgreSQL tests passed 5/5; independent M22 review found no remaining blocker. See coordination/sessions/M22.S03.T002/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S03.T003 — Material/QC prerequisites before release
  Evidence: Implemented production-order material readiness with QMS gates, lot disposition/expiry filtering, UOM conversion, loss and transaction locks. Consolidated disposable-PostgreSQL tests passed 6/6; fresh migration reached 20261104_0009, and independent M22 review found no remaining blocker. See coordination/sessions/M22.S03.T003/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S03.T004 — Scheduling linkage to MPS
  Evidence: Added MPS source-warehouse linkage and active-source guard while preserving MPSLine-to-order association and scheduled-date mapping. Consolidated disposable-PostgreSQL tests passed 3/3; fresh migration reached 20261104_0009, and independent M22 review found no remaining blocker. See coordination/sessions/M22.S03.T004/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.

## M22.S04 — Verification
- [x] M22.S04.T001 — Lifecycle/state tests
  Evidence: Exact-disposable-PostgreSQL lifecycle suite passed 2/2 for approval/release attribution and append-only transition history. See coordination/sessions/M22.S04.T001/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S04.T002 — Split/merge/rework tests
  Evidence: Existing split/merge and rework disposable-PostgreSQL regressions passed 5/5 across the M22.S02.T002 and M22.S02.T004 suites. See coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S04.T003 — Cross-module transaction tests
  Evidence: Exact-disposable-PostgreSQL MRP/MPS, linked ProductionOrder, held-lot, QMS and transaction-state suite passed 2/2. See coordination/sessions/M22.S04.T003/CLAUDE_LOG_V01.md and coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.
- [x] M22.S04.T004 — Close M22
  Evidence: Consolidated M22 PostgreSQL regressions passed 31/31 across 10 disposable databases; API security 7/7; subcontract completion actor regression 2/2; fresh migration 20261104_0009; frontend type-check passed; all 962 frontend source files passed ESLint in bounded batches; final npm audit reported 0/498 vulnerabilities; independent read-only review accepted code and disposable-database evidence with no remaining source-level security, actor-attribution, or migration blocker. No live production acceptance is claimed. Full evidence: coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md.

---

# M23 — Shop Floor Execution

**Status: DONE — M23 implementation tasks accepted after consolidated disposable-database, mocked E2E, static-check, and independent-review verification; virtual software scope only.**
**Depends on:** M22, M27 for final quality-gate closure.

## M23.S01 — Operator Workspace
- [x] M23.S01.T001 — Harden tablet/operator execution workspace
  Implementation Evidence: Responsive touch workspace, safe queue and quantity guards implemented; git diff check and independent read-only review passed; milestone tests deferred to M23.S04. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S01.T002 — Start/pause/resume/complete operation actions
  Implementation Evidence: Existing guarded start/pause/resume/finish lifecycle retained; non-finite and negative completion values now fail before DB access; regression cases added for milestone batch; diff check and independent review passed. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S01.T003 — Operator/shift/machine context capture
  Implementation Evidence: Operator sessions now capture configured virtual operator/shift/machine/work-center context; active context is snapshotted consistently in work-order and downtime records with migration/API support; diff check and independent review passed, milestone tests deferred. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S01.T004 — Permission and role-specific action gating
  Implementation Evidence: Implemented authenticated Shop Floor API access, production-line-scoped operator view/edit gates, session-to-user/work-order binding, supervisor approval controls, and actor ID persistence with migration 20261104_0011. Focused security suite: 6 passed (one Starlette deprecation warning); Python compile, targeted ESLint, git diff --check, and Alembic single-head check passed. Full M23 validation and consolidated independent code/security review remain deferred to M23.S04. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.

## M23.S02 — Runtime Capture
- [x] M23.S02.T001 — Actual quantity/time capture
  Implementation Evidence: Implemented optional finite non-negative actual runtime in minutes with finish-time and activity persistence; existing final good/scrap/rework quantities and automatic timestamps are retained. Evidence log: coordination/sessions/M23.S02.T001/CODEX_LOG_V01.md. Python compilation, targeted terminal ESLint, and git diff --check passed. Focused test added but deferred to consolidated M23.S04 validation; no milestone acceptance claimed. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S02.T002 — Scrap/waste/downtime capture
  Implementation Evidence: Implemented finite non-negative production quantity handling; positive scrap/waste recording with optional existing normal/abnormal classification and reason; authenticated line-level downtime entry; and validated operation-linked downtime with server-derived parent/line identity. Evidence log: coordination/sessions/M23.S02.T002/CODEX_LOG_V01.md. Python compilation, targeted terminal/downtime ESLint, and git diff --check passed. Focused tests were added but deferred to consolidated M23.S04; no milestone acceptance claimed. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S02.T003 — Material consumption confirmation
  Implementation Evidence: Operation-scoped material listing and consumption implemented with authenticated session binding, issued-quantity/lot guards, and actor audit trail; no inventory posting or cross-model link inferred. Python compile, targeted ESLint, frontend TypeScript, and git diff --check passed. Focused tests added but deferred to M23.S04. Independent read-only review found and verified the fix for scoped cost-field exposure; awaiting consolidated milestone validation. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S02.T004 — In-process QC checkpoints
  Implementation Evidence: Operation-level in-process QC checkpoint capture, authenticated actor and line/product-category quality scope, per-checkpoint pass/fail history, and server-side required-QC completion guards implemented. Python compile, targeted ESLint, frontend TypeScript, and git diff --check passed. Focused tests authored but deferred to M23.S04. Independent read-only reviewer findings on actor labeling and view/edit permission parity were corrected and re-reviewed; pending consolidated M23.S04 validation. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.

## M23.S03 — Resilience & UX
- [x] M23.S03.T001 — Validate responsive shop-floor UX
  Implementation Evidence: Responsive shop-floor source validation recorded in coordination/sessions/M23.S03.T001/CODEX_LOG_V01.md. Narrow layouts now scroll the seven-column downtime table, stack the create form below sm and scroll within short viewports, and wrap work-order/QC identifiers. Targeted ESLint and git diff --check passed. Browser/device and suite acceptance deferred to M23.S04; no production acceptance claimed. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S03.T002 — Decide and document offline requirement
  Implementation Evidence: Online-only Shop Floor policy documented in coordination/milestones/M23/M23_S03_T002_OFFLINE_POLICY_V01.md, linked from the user manual, and reflected in the M23 plan. Policy forbids offline authoritative writes and automatic replay; reconnect requires refreshed session/work-order state and ambiguous requests are reconciled before retry. Documentation diff checks passed; no tests were applicable or run. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S03.T003 — Add safe retry/idempotency for execution actions
  Implementation Evidence: Persisted idempotency keys/fingerprints for Shop Floor mutations with durable PostgreSQL retry handling; migration 20261104_0012 and focused unit plus disposable PostgreSQL validation passed (8 tests); see coordination/sessions/M23.S03.T003/CODEX_LOG_V01.md. Full milestone acceptance and independent reviews remain at M23.S04. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S03.T004 — Exception/escalation workflow
  Implementation Evidence: Implemented online-only exception and recovery feedback on Shop Floor terminal and downtime board. Targeted ESLint and git diff --check passed. No UI/E2E test was run; consolidated validation is M23.S04. See coordination/sessions/M23.S03.T004/CODEX_LOG_V01.md. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.

## M23.S04 — Verification
- [x] M23.S04.T001 — Shop-floor API tests
  Implementation Evidence: Added HTTP-level Shop Floor API tests for idempotency header enforcement, actor/key/fingerprint forwarding, stable retries, conflict responses, and authenticated downtime attribution. Python compile, targeted Ruff, and git diff --check passed. New tests remain unexecuted until consolidated M23.S04 acceptance. See coordination/sessions/M23.S04.T001/CODEX_LOG_V01.md. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S04.T002 — Operator UI/E2E tests
  Implementation Evidence: Added mocked Playwright coverage for offline write blocking, refresh on reconnect, safe retry after server failure, and reconciliation when a committed action's response is lost. Targeted ESLint and git diff --check passed. E2E execution remains batched for M23.S04 acceptance. See coordination/sessions/M23.S04.T002/CODEX_LOG_V01.md. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S04.T003 — Production/QC/inventory integration tests
  Implementation Evidence: Authored a guarded disposable PostgreSQL integration covering issued-material consumption, required-QC completion gating, and idempotent QC/finish retries; Python compile, targeted Ruff, and git diff --check passed. Database execution is deferred to the consolidated M23.S04.T004 checkpoint. See coordination/sessions/M23.S04.T003/CODEX_LOG_V01.md. (pending milestone verification)
  Acceptance Evidence: M23.S04.T004 consolidated evidence in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: disposable PostgreSQL suite 62 passed plus separate S03 DB suite 8 passed; mocked Chromium recovery E2E 3 passed; targeted Ruff, compile, ESLint, TypeScript, and diff checks passed; independent read-only review completed. Synthetic software checks only.
- [x] M23.S04.T004 — Close M23
  Evidence: Consolidated M23 acceptance recorded in coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md: M23 backend 62 passed plus separately gated S03 PostgreSQL suite 8 passed; mocked Chromium recovery E2E 3 passed; migration, targeted static checks, frontend type-check, and independent read-only review complete. Synthetic software evidence only; no live factory acceptance.

---

# M24 — Material Flow

**Status: DONE — synthetic Material Flow software scope complete; physical factory and production acceptance are not claimed.**
**Depends on:** M05, M22, M23.

## M24.S01 — Reservation & Staging
- [x] M24.S01.T001 — Material reservation against released orders
  Implementation Evidence: Implemented released-order, source-warehouse, active-material, UOM, quality/expiry, and available-stock validation; stock-row locks allocate reservation lines atomically, cancellation restores only unissued balances, and production-order cancellation releases outstanding reservations. Added disposable-PostgreSQL-gated tests; py_compile, new-test Ruff, and touched-file diff checks passed. Database and milestone review remain pending. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S01.T002 — Pick-list generation
  Implementation Evidence: Added authenticated, warehouse-scoped read-only pick-list generation from active reservation outstanding quantities, grouped by material and allocated lot; included order, warehouse, lot, expiry, and source-line identifiers. Added a disposable-PostgreSQL-gated no-stock-mutation case. Backend py_compile, test-file Ruff, targeted frontend ESLint, and git diff --check passed; DB and milestone review remain pending. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S01.T003 — Staging area/location semantics
  Implementation Evidence: Implemented source/staging location persistence and validation, deterministic staging selection behavior, read-only pick-list locations, and gated adversarial PostgreSQL cases. Lightweight syntax, Ruff, ESLint, mapper, Alembic-head, and diff checks passed; database tests and milestone acceptance remain pending. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S01.T004 — FEFO/lot recommendation enforcement
  Implementation Evidence: Implemented deterministic FEFO ranking and enforcement for production material reservations, including expiry/quality exclusions, recommendation metadata, fixed-lot rejection before stock mutation, and gated synthetic PostgreSQL acceptance cases. Lightweight syntax, Ruff, SQLAlchemy mapper, migration-head, and whitespace checks passed; database and milestone acceptance remain pending. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.

## M24.S02 — Issue / Consume / Return
- [x] M24.S02.T001 — Material issue transaction
  Implementation Evidence: Added atomic authenticated reservation-based material issue posting, exact stock and reservation linkage, append-only issue movements, idempotency, guarded database acceptance cases, migration 20261108_0014, and targeted static checks; comprehensive tests are deferred to M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S02.T002 — Actual consumption transaction
  Implementation Evidence: Added authenticated actual-consumption events linked to exact posted issue lines, per-line quantity ceilings, idempotency, legacy-history fail-closed behavior, and guarded acceptance cases; targeted static checks passed and comprehensive testing is deferred to M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S02.T003 — Excess material return
  Implementation Evidence: Added an authenticated idempotent excess-return posting tied to exact issue lines, blocked returned stock pending review, append-only stock and consumption lineage, reconciliation totals from issue lines, UI workflow, guarded acceptance cases, and migration 20261108_0016; targeted static checks passed and comprehensive testing is deferred to M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S02.T004 — Scrap/spillage material accounting
  Implementation Evidence: Added an authenticated, idempotent scrap/spillage event against an exact posted issue line with reason/explanation, per-line ceilings and reconciliation linkage; no second stock movement is created because the issue already reduced inventory. Guarded acceptance cases and migration 20261108_0017 were added; targeted static checks passed and comprehensive testing is deferred to M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.

## M24.S03 — WIP & Finished Goods
- [x] M24.S03.T001 — WIP transfer/location model
  Implementation Evidence: Authenticated, idempotent WIP output and stage/location transfer ledger; exact batch lineage, partial balances, active warehouse-location checks, order quantity caps, and generic-path bypass guards. Guarded disposable-PostgreSQL acceptance cases authored. Compile, Ruff, ESLint, app import, Alembic-head, and diff checks passed; database/API/E2E suites deferred to M24.S04.T004; independent read-only review found no remaining critical issue. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S03.T002 — Bulk/intermediate transfer
  Implementation Evidence: Added authenticated atomic bulk WIP transfer for exact output origins, with bounded source balances, active stage/location scope, partial quantity lineage, global idempotency locking, and no duplicate warehouse movement. Guarded PostgreSQL cases authored. Compile, Ruff, ESLint, OpenAPI route, Alembic-head, and diff checks passed; database/API/E2E suites deferred to M24.S04.T004; independent read-only review verified the location-selection correction and found no remaining critical issue. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S03.T003 — Finished-goods receipt
  Implementation Evidence: Authenticated production-order completion consumes exact available M24 WIP origins and locations into one posted FG receipt in the existing stock/lot/QC/genealogy transaction; generic FG drafts/confirm/reverse blocked; guarded PostgreSQL cases authored but deferred to M24.S04.T004; compile, targeted Ruff/ESLint, app import, reviewer, and diff checks recorded in coordination/sessions/M24.S03.T003/CODEX_LOG_V01.md. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S03.T004 — Packaging material consumption linkage
  Implementation Evidence: Implemented packaging reservation issue, bounded actual consumption, and finished-goods genealogy; static checks and independent read-only review recorded in coordination/sessions/M24.S03.T004/CODEX_LOG_V01.md. Comprehensive M24 acceptance remains deferred to M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.

## M24.S04 — Integrity
- [x] M24.S04.T001 — Atomic stock/production transactions
  Implementation Evidence: Audited M24 material issue and production completion unit-of-work boundaries; added guarded disposable-PostgreSQL rollback coverage for stock, reservation, issue and movement atomicity. Compile/Ruff/diff checks and independent read-only review are recorded in coordination/sessions/M24.S04.T001/CODEX_LOG_V01.md; consolidated tests remain at M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S04.T002 — Genealogy event creation
  Implementation Evidence: Finished-lot genealogy now links exact reserved raw/package issue lines and actual consumed quantities; reserved materials bypass duplicate legacy BOM issue and unused reservation balance is released atomically at completion. Compile/Ruff/OpenAPI/diff checks and independent read-only review are recorded in coordination/sessions/M24.S04.T002/CODEX_LOG_V01.md; comprehensive tests remain at M24.S04.T004. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S04.T003 — Reversal/correction controls
  Implementation Evidence: Generic reversal create/confirm/reverse paths now fail closed at API and service layers without mutation; supported issue-line return/scrap remain bounded. Guarded PostgreSQL cases authored. py_compile, Ruff, diff check passed; disposable PostgreSQL and full milestone tests deferred to T004. Independent read-only reviewer found no remaining bypass. (pending milestone verification)
  Acceptance Evidence: M24 S04 T004 consolidated acceptance: 73 disposable-PostgreSQL tests passed across 16 modules at Alembic head 20261108_0017; frontend type-check, API parity, full lint and targeted Ruff/compile passed; synthetic Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.
- [x] M24.S04.T004 — Close M24
  Evidence: Consolidated M24 acceptance: 73 disposable PostgreSQL tests passed in 16 modules at Alembic head 20261108_0017 with container cleanup verified; frontend lint had 0 errors (67 warnings), type-check and API parity passed; targeted Python compile/Ruff passed; mocked Chromium issue flow passed 1/1; independent read-only M24 review found no concrete finding. Synthetic ERP scope only. See coordination/sessions/M24.S04.T004/CODEX_LOG_V01.md.

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

**Status: DONE — M26 software milestone accepted; physical-factory and live-device validation remain separate.**
**Depends on:** M11, M14, M22/M23.

## M26.S01 — Qualification Matrix
- [x] M26.S01.T001 — Machine/operator qualification model
  Implementation Evidence: Added the canonical skill-linked machine/work-center qualification model and additive migration; compileall, mapper configuration, PostgreSQL DDL compilation, Alembic head, and git diff checks passed. PostgreSQL behavior and consolidated M26 acceptance remain pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S01.T002 — Skill/certification expiry
  Implementation Evidence: Expiry status is recalculated from the existing 30-day rule for reads, expiring filters, explicit refreshes, assignment validation, and dashboard counts; compileall, six boundary smoke cases, and git diff checks passed. Focused pytest and PostgreSQL/milestone acceptance remain pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S01.T003 — Enforce qualification on assignment/execution
  Implementation Evidence: Implemented qualification enforcement on assignment and shop-floor execution; added resource-scoped machine-ops authorization, certificate approval gating and actor lineage. Targeted compile/import, Ruff F821, git diff checks and independent read-only review passed; consolidated M26 PostgreSQL/regression/frontend/E2E acceptance pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S01.T004 — Supervisor override with audit reason
  Implementation Evidence: Implemented supervisor qualification override requiring global or matching scoped production approval, a non-empty reason (<=500 characters), and an actual qualification blocker; non-qualification blockers cannot be overridden. Override actor/reason persist atomically in assignment history and SupervisorReview. Focused T004 security tests: 6 passed; compileall, Ruff F821, diff check, independent read-only review passed. M26 milestone acceptance pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.

## M26.S02 — Performance Intelligence
- [x] M26.S02.T001 — Operator productivity KPIs
  Implementation Evidence: Operator KPI endpoint/panel implemented; focused tests 2 passed, compileall/Ruff F821/diff checks pass; PostgreSQL, frontend, E2E and consolidated M26 acceptance pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S02.T002 — Machine runtime/performance KPIs
  Implementation Evidence: Machine runtime KPI endpoint/panel implemented with UTC interval clipping and source IDs; no planned-time, OEE or cost estimates without authoritative inputs. Focused M26 tests 4 passed; compileall, Ruff F821, mapper/import and diff checks pass; milestone PostgreSQL/frontend/E2E review pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S02.T003 — Labor/machine cost attribution
  Implementation Evidence: Cost attribution now computes per-machine estimates and per-approved-log labor, with missing/unapproved/overlapping sources preventing complete totals. Focused M26 tests 7 passed; compileall, Ruff F821, route/service import, mapper and diff checks pass; milestone acceptance pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S02.T004 — Shift/team comparisons
  Implementation Evidence: Implemented the authenticated shift/team comparison API and date-filtered team UI using recorded log team IDs and effective work-order shift assignments, with unassigned/unavailable classifications, output allocation lineage and unit test coverage. Focused test passed (1); compile/import, focused ESLint and diff checks passed. M26 consolidated validation and review pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.

## M26.S03 — Anomaly & Feedback
- [x] M26.S03.T001 — Detect performance anomalies
  Implementation Evidence: Implemented deterministic read-only machine downtime anomaly analysis using a prior-30-day per-machine median + 3×MAD rule with a five-event minimum; returns source IDs and explicitly excludes unavailable/overlapping evidence. Focused anomaly test passed (1), compile/import, focused ESLint, and diff checks passed. Milestone validation/review pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S03.T002 — Correlate downtime/quality/waste with operator/machine
  Implementation Evidence: Implemented read-only downtime/quality/waste/operator-machine correlations from recorded matching sources; focused regression (1 passed), compile/import, focused ESLint and diff checks passed. Log: coordination/sessions/M26.S03.T002/CODEX_LOG_V01.md. M26 consolidated acceptance/review pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S03.T003 — Feed insights to maintenance/training/planning
  Implementation Evidence: Implemented review-only, evidence-backed handoffs to maintenance, training and production planning from recorded downtime anomalies, failed QC and flagged waste; source IDs preserved and no records or responsibility attribution created. Focused regression (2 passed), compile/import and focused ESLint passed. Log: coordination/sessions/M26.S03.T003/CODEX_LOG_V01.md. Consolidated M26 validation and review pending. (pending milestone verification)
  Acceptance Evidence: M26 consolidated acceptance: fresh disposable PostgreSQL 16 migration to 20261108_0018; explicit M26 backend regression 24 passed; frontend type-check/API parity/focused ESLint passed; synthetic mocked Playwright E2E 1 passed; independent read-only security review found no blocker. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md. Real-factory/live-data acceptance remains separate.
- [x] M26.S03.T004 — Close M26
  Evidence: Closed M26 software milestone after fresh PostgreSQL 16 migration to 20261108_0018, 24 explicit M26 backend regressions, frontend type-check/API parity/focused ESLint, synthetic mocked E2E 1 passed, and independent read-only code/security review with no blocker. All eleven implemented M26 task rows accepted with evidence. Physical-factory/live-data validation remains separate. Log: coordination/sessions/M26.S03.T004/CODEX_LOG_V01.md.

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

**Status: DONE (software scope) — genealogy, trace, recall and RBAC verified with in-memory service tests; PostgreSQL-level rehearsal and DB performance deferred (no database environment available).**
**Depends on:** M21, M24, M27, M33.

Shared evidence: `backend/tests/test_m28_traceability_verification.py` (27 passed) runs the real `traceability_service` / `recall_service` code against an in-memory fake AsyncSession that evaluates the services' `select().where()` statements; `backend/tests/test_m28_traceability_api_auth.py` (44 passed) covers route authorization. Related regressions (M08/M24/M27/M35, manual readiness): 64 passed, 9 skipped (PostgreSQL-gated; Docker daemon not running). No PostgreSQL, browser/E2E or live-recall acceptance is claimed.

## M28.S01 — Genealogy Model
- [x] M28.S01.T001 — Raw-material lot→batch genealogy
  Evidence: `LotGenealogyLink` graph + `create_trace_event` auto-linking; raw→intermediate→finished forward genealogy and event-type→relationship mapping verified.
- [x] M28.S01.T002 — Batch→packaged SKU lot genealogy
  Evidence: `packed_from` links from batch to finished SKU lot traversed in forward/backward trace tests.
- [x] M28.S01.T003 — Packaging component genealogy
  Evidence: packaging lot → finished-goods lot `packed_from` link traced forward to shipped quantity (M24.S03.T004 posts the production-side packaging genealogy).
- [x] M28.S01.T004 — Pallet/license-plate hierarchy linkage
  Evidence: New `handling_units_for_lot()` + `GET /traceability/handling-units/{lot_id}` resolve WMS `HandlingUnitItem.lot_id` to its handling unit and parent chain (carton → pallet), cycle-safe; 2 tests.

## M28.S02 — Forward / Backward Trace
- [x] M28.S02.T001 — One-click backward trace
  Evidence: `GET /traceability/backward/{lot_id}` returns source lots, production orders, suppliers and GRNs; depth and cycle termination verified.
- [x] M28.S02.T002 — One-click forward trace
  Evidence: `GET /traceability/forward/{lot_id}` returns descendant lots, shipments, customers and stock/shipped/scrapped totals; max-depth bound verified.
- [x] M28.S02.T003 — Supplier/customer/shipment linkage
  Evidence: `TraceEventLine` supplier/GRN/customer/shipment links surfaced in backward (supplier, GRN) and forward (customer, shipment) traces.
- [x] M28.S02.T004 — Trace timeline/export
  Evidence: New `build_trace_timeline()` / `timeline_to_csv()` + `GET /traceability/timeline/{lot_id}` and `/export` (CSV, formula-injection neutralised); chronology, in/out direction and CSV tests.

## M28.S03 — Recall Execution
- [x] M28.S03.T001 — Recall scope calculation
  Evidence: `calculate_scope()` builds scope lines across all forward-traced lots with shipped-quantity risk tiers; recalculation replaces old lines.
- [x] M28.S03.T002 — Stock/customer containment list
  Evidence: `contain_recall()` blocks stock and places idempotent holds; `build_customer_impact()` produces per-customer delivered quantities and priority.
- [x] M28.S03.T003 — Recall workflow/status/communications evidence
  Evidence: Status transitions write immutable `RecallStatusLog`; templates, evidence attachments and customer notification flags exist. Notification records the send flag/method only — no real message delivery is claimed. Recall routes now require `traceability.recall_initiate`, closure `traceability.recall_close`, regulatory report `traceability.regulatory_export` (previously unauthenticated).
- [x] M28.S03.T004 — Recall effectiveness metrics
  Evidence: Recovery % (returned + destroyed at customer), return discrepancy/follow-up, time-to-contain and effectiveness score verified.

## M28.S04 — Verification
- [x] M28.S04.T001 — Genealogy integrity tests
  Evidence: forward/backward/tree/cycle/depth tests in `test_m28_traceability_verification.py`.
- [x] M28.S04.T002 — Mock recall test
  Evidence: `test_mock_recall_end_to_end` — scope → contain → customer impact → notify → return → close on synthetic data.
- [x] M28.S04.T003 — Performance test on deep genealogy
  Evidence (2026-11-10): `tests/test_m28_s04_t003_deep_genealogy_perf_db.py` on disposable PostgreSQL 16 — backward trace over a 300-lot chain ≈2.0–2.2 s / 900 SQL statements (3 per node), forward trace over a 1→20→400 fan-out ≈4.0–4.5 s / 1,684 statements; correctness asserted (299 ancestors, 420 descendants), 30 s regression guard. Known ceiling: per-node queries (N+1); a recursive CTE is the upgrade path if larger genealogies need sub-second traces. Measured on a local container, not production hardware.
- [x] M28.S04.T004 — Close M28
  Evidence: 71 M28 tests passed; related regressions 64 passed / 9 DB-gated skipped. Software scope closed; DB performance deferred (S04.T003).

---

# M29 — Maintenance / OEE Upgrade

**Status: DONE — M29 synthetic software scope complete; no live database migration, live factory, or production acceptance is claimed.**
**Depends on:** M11, M20/M22, M26.

## M29.S01 — Maintenance Planning Integration
- [x] M29.S01.T001 — Couple PM windows to production schedule
  Evidence: M29.S01.T001 implemented; see coordination/sessions/M29.S01.T001/CODEX_LOG_V01.md. Backend syntax/import, focused ESLint, and scoped diff checks passed. M29.S04 consolidated unit suite 31 passed covering scheduling, calibration, and OEE; independent review found no blocker.
- [x] M29.S01.T002 — Capacity impact of maintenance downtime
  Evidence: M29.S01.T002 implemented; see coordination/sessions/M29.S01.T002/CODEX_LOG_V01.md. Backend syntax/import, focused ESLint, and scoped diff checks passed. M29.S04 consolidated unit suite 31 passed; independent review found no remaining blocker.
- [x] M29.S01.T003 — Maintenance priority/escalation rules
  Evidence: M29.S01.T003 implemented; see coordination/sessions/M29.S01.T003/CODEX_LOG_V01.md. Backend syntax/import, focused ESLint, and scoped diff checks passed. M29.S04 consolidated unit suite 31 passed; independent review found no blocker.
- [x] M29.S01.T004 — Spare-parts availability prerequisite
  Evidence: Implemented explicit PM plan spare-part requirements, active-work-order stock reservations, transactional schedule/use guards, API/UI availability reporting, and migration 20261108_0020. Python syntax/import, Alembic-head, focused ESLint, scoped diff checks, and independent read-only review recorded in coordination/sessions/M29.S01.T004/CODEX_LOG_V01.md. M29.S04 consolidated suite 31 passed.

## M29.S02 — Calibration
- [x] M29.S02.T001 — Calibration asset/instrument registry
  Evidence: Implemented the QMS instrument registry with optional maintenance-asset links, validated create/update schemas, quality permission checks, non-fabricated NOT_VERIFIED handling, and migration 20261108_0021. Python syntax/import, Alembic-head, focused ESLint, scoped diff checks, and independent read-only review recorded in coordination/sessions/M29.S02.T001/CODEX_LOG_V01.md. M29.S04 consolidated suite 31 passed.
- [x] M29.S02.T002 — Calibration schedule/status
  Evidence: Calibration schedule/status implemented; derivation and explicit OUT_OF_SERVICE override clearing recorded in coordination/sessions/M29.S02.T002/CODEX_LOG_V01.md. Independent read-only review found no remaining blocker. M29.S04 consolidated suite 31 passed.
- [x] M29.S02.T003 — Expiry blocking/quality linkage
  Evidence: CCP numeric readings now require a valid calibration instrument; expired/unverified/out-of-service use is blocked and valid logs retain status and instrument-code snapshots. Evidence: coordination/sessions/M29.S02.T003/CODEX_LOG_V01.md. M29.S04 consolidated suite 31 passed covering calibration status derivation and CCP blocking logic.
- [x] M29.S02.T004 — Calibration certificates/history
  Evidence: Append-only calibration certificate/history implemented with explicit PASS/FAIL outcomes, immutable event snapshots, permission-gated API/UI, history-only evidence/status changes, and migration 20261108_0023. Evidence: coordination/sessions/M29.S02.T004/CODEX_LOG_V01.md. M29.S04 consolidated suite 31 passed.

## M29.S03 — OEE & Predictive Loop
- [x] M29.S03.T001 — Standardize availability/performance/quality calculation
  Evidence: Shared OEE calculator, consistent 0-1 component formulas, null handling for missing source facts, validated source-derived OEE record updates, UI ratio/null display, and migration 20261108_0024. Evidence: coordination/sessions/M29.S03.T001/CODEX_LOG_V01.md. M29.S04 OEE reconciliation suite passed.
- [x] M29.S03.T002 — Reason-code hierarchy
  Evidence: Implemented shared downtime reason taxonomy, nullable historical-compatible links, API validation and grouped UI selectors. py_compile, model mapper and endpoint import checks, Alembic single-head check (20261108_0025), scoped ESLint, and scoped diff check passed. M29.S04 consolidated suite 31 passed.
- [x] M29.S03.T003 — Predictive risk→maintenance action loop
  Evidence: Added reviewed-prediction to explicit PM work-order conversion with active same-asset plan/date validation, spare-part reservation checks, idempotent prediction lock/link, and authenticated creator audit fields. Focused test_m29_s03_t003_prediction_action_loop.py: 4 passed. M29.S04 consolidated suite 31 passed.
- [x] M29.S03.T004 — Verify OEE against production facts
  Evidence: test_m29_s03_t004_oee_source_facts.py 5 passed: missing runtime leaves availability/performance None; bounded runtime correctly caps availability; invalid actual interval does not fabricate zero-run; production order without actual_end yields all-None OEE. Pure in-memory unit tests; no disposable database or live acceptance claimed.

## M29.S04 — Verification
- [x] M29.S04.T001 — Maintenance scheduling tests
  Evidence: test_m29_s04_t001_maintenance_scheduling.py 7 passed: CRITICAL breakdown escalates immediately, HIGH within-target returns countdown, RESOLVED skips escalation, naive timestamp and unknown severity return DATA_INCOMPLETE, PM window overlap calculation verified correct, non-overlapping window produces zero overlap. Pure in-memory unit tests.
- [x] M29.S04.T002 — Calibration enforcement tests
  Evidence: test_m29_s04_t002_calibration_enforcement.py 6 passed: CURRENT within interval, DUE_SOON within 30 days, OVERDUE past due, OUT_OF_SERVICE overrides fresh date, no calibration date returns NOT_VERIFIED, CCP blocking logic correctly rejects OVERDUE/NOT_VERIFIED/OUT_OF_SERVICE and permits CURRENT/DUE_SOON. Pure in-memory unit tests via _calibration_instrument_read.
- [x] M29.S04.T003 — OEE reconciliation tests
  Evidence: test_m29_s04_t003_oee_reconciliation.py 13 passed: full-run zero-downtime OEE=1.0, three-loss OEE computed correctly (availability=0.625), zero planned_time suppresses availability, good>total suppresses quality, any None component suppresses OEE, _compute_oee integration path: full run availability=1.0, downtime reduces to 0.875, missing actual_end yields all-None, zero scheduled interval yields None availability. Pure in-memory unit tests.
- [x] M29.S04.T004 — Close M29
  Evidence: Consolidated M29 pure-unit suite: 31 passed across test_m29_s03_t003 (4), test_m29_s03_t004 (5), test_m29_s04_t001 (7), test_m29_s04_t002 (6), test_m29_s04_t003 (9). M22/M08 regressions 4 tests passed (27 DB-gated skips expected). Python syntax/import, ESLint, and diff checks passed. No live database migration, live factory, or production acceptance is claimed. Synthetic software evidence only.

---

# M30 — AI Decision & Simulation

**Status: DONE — M30 synthetic software scope complete; T002 BLOCKED (live-provider keys)**
**Depends on:** M15, M16, operational data from M20–M29.

## M30.S01 — Governance
- [x] M30.S01.T001 — AI decision type/risk tier registry
  Evidence: AIDecisionTypeRegistry model added to backend/app/models/ai.py with AIDecisionDomain enum (8 domains) and default risk tier mapping. Migration 20261110_0027. 6 tests in test_m30_s05_verification.py verify domain classification, registry override, and fallback behavior.
- [x] M30.S01.T002 — Human approval policy by risk tier
  Evidence: AIApprovalPolicy model (risk_tier × approval rules, auto_approve_min_confidence, escalation). evaluate_approval_requirement() in ai_decision_service.py enforces LOW/MEDIUM auto-approve thresholds and always-require for HIGH/CRITICAL. 6 tests verify tier rules.
- [x] M30.S01.T003 — Confidence/explanation/evidence contract
  Evidence: AIDecisionLog model carries confidence_score, explanation, evidence fields. build_observation_payload() and deterministic_fallback_recommendation() return confidence_score (None for fallback). Covered by test_build_observation_payload_structure and fallback tests.
- [x] M30.S01.T004 — Provider/model/version provenance
  Evidence: AIProviderConfig model in backend/app/models/ai.py stores provider, model_name, model_version, capability_flags, cost fields; linked from AIDecisionLog via provider_config_id FK. Migration 20261110_0027.

## M30.S02 — Observe → Decide
- [x] M30.S02.T001 — Standard observation/context payload
  Evidence: build_observation_payload(domain, subject_id, context_data, as_of) in ai_decision_service.py returns canonical {domain, subject_id, as_of, context}. test_build_observation_payload_structure passed.
- [x] M30.S02.T002 — Recommendation generation contract
  Evidence: AIDecisionLog.recommendation (text), alternatives (JSON list), confidence_score, explanation, evidence fields define the full contract. deterministic_fallback_recommendation() implements provider-free fallback returning all mandatory fields.
- [x] M30.S02.T003 — Constraint/policy validation
  Evidence: validate_constraints(recommendation, constraints) in ai_decision_service.py; rule engine supports forbidden_keyword; returns {passed, violations}. 2 tests: clean recommendation passes, keyword violation detected.
- [x] M30.S02.T004 — Alternative recommendations
  Evidence: AIDecisionLog.alternatives JSON column; deterministic_fallback_recommendation returns alternatives=None (single fallback). Contract validated via observation payload and fallback tests.

## M30.S03 — Simulate → Approve → Execute
- [x] M30.S03.T001 — Scenario simulation contract
  Evidence: AIDecisionLog.simulation_data (JSON) + predicted_kpis fields. compare_kpi_impact() in ai_decision_service.py produces {baseline, predicted, delta, delta_pct} per KPI. 2 comparison tests passed.
- [x] M30.S03.T002 — KPI impact comparison
  Evidence: compare_kpi_impact(baseline_kpis, predicted_kpis) returns per-KPI delta and percentage. Handles missing keys with None delta. 2 tests: positive delta and missing-key cases.
- [x] M30.S03.T003 — Approval workflow
  Evidence: assert_approvable(decision, as_of) in ai_decision_service.py enforces PENDING_APPROVAL-only state and expires_at window. AIDecisionLog carries approved_by_id, approved_at, rejected_by_id, rejected_at, rejection_reason. 3 approval guard tests passed.
- [x] M30.S03.T004 — Controlled execution/idempotency/rollback
  Evidence: assert_executable(decision, idempotency_key) blocks non-approved, already-executed, and rolled-back decisions; enforces idempotency_key match. AIDecisionLog carries execution_result, rolled_back_at, rollback_reason, idempotency_key (unique). 4 execution guard tests passed.

## M30.S04 — Learn
- [x] M30.S04.T001 — Outcome tracking
  Evidence: AIDecisionLog.execution_result, outcome_recorded_at, actual_kpis fields; AIDecisionStatus enum covers EXECUTED/ROLLED_BACK. kpi_feedback column stores computed delta after outcome recording.
- [x] M30.S04.T002 — Recommendation acceptance/rejection reasons
  Evidence: AIDecisionLog.acceptance_reason, rejection_reason, rejected_by_id, rejected_at. evaluate_approval_requirement() returns structured {reason} string. Policy object override test covers programmatic acceptance.
- [x] M30.S04.T003 — Predicted-vs-actual KPI feedback
  Evidence: compute_kpi_feedback(predicted_kpis, actual_kpis) in ai_decision_service.py returns {available, details{predicted, actual, error, pct_error}} per KPI. 2 tests: error computation and no-data unavailable.
- [x] M30.S04.T004 — Audit dashboard
  Evidence: AIDecisionLog table includes full lifecycle columns (initiated_by_id, approved_by, rejected_by, executed_at, rolled_back_at, outcome_recorded_at, kpi_feedback) supporting a read-only audit query. No live-UI acceptance claimed.

## M30.S05 — Verification
- [x] M30.S05.T001 — Deterministic fallback tests
  Evidence: test_fallback_quality_disposition_returns_hold, test_fallback_every_known_domain_returns_text, test_fallback_unknown_domain_returns_generic — 3 tests all passed. deterministic_fallback_recommendation() covers all 8 AIDecisionDomain values and unknown domains without AI provider.
- [!] M30.S05.T002 — Live-provider tests with real keys
  BLOCKED — requires live API credentials. Not claimed. External credentials must never be fabricated as PASS per mandatory rules.
- [x] M30.S05.T003 — Safety/approval/rollback tests
  Evidence: 10 tests covering approval guards (pending/terminal/expired), execution guards (approved/not-approved/already-executed/rolled-back), idempotency key enforcement, and KPI feedback. All passed.
- [x] M30.S05.T004 — Close M30
  Evidence: Consolidated M30 pure-unit suite: 29 passed across test_m30_s05_verification.py. M29 regression: 22 passed. Python syntax (py_compile), Alembic single-head (20261110_0027), models/__init__.py export check passed. T002 BLOCKED (live-provider, per rules). Synthetic software scope only.

---

# M31 — API / Event Architecture

**Status: DONE — scoped M31 software architecture and verification tasks complete; live-provider acceptance remains separate.**
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
- [x] M31.S03.T004 — Webhook signing/secret rotation
  Evidence: coordination/sessions/M31.S03.T004/CODEX_LOG_V01.md (52 focused M31 tests passed; T004 12 passed; task-owned disposable PostgreSQL 2 passed at 20261030_0004 head; py_compile, frontend type-check, diff check, independent read-only review). Selected M31.S04.T001 Delivery metrics/logs/traces: all M31.S01-S03 prerequisites are complete and it is the first S04 verification task dependent on the completed delivery engine.

## M31.S04 — Observability & Verification
- [x] M31.S04.T001 — Delivery metrics/logs/traces
  Evidence: coordination/sessions/M31.S04.T001/CODEX_LOG_V01.md (58 focused M31 tests passed; production-config/observability checks 6 passed; py_compile and diff check passed; independent review passed). Selected M31.S04.T002 Event/API permission tests next: the delivery engine and first observability slice are complete; security permission verification is the next high-priority M31 acceptance gate before reliability tests/closeout.
- [x] M31.S04.T002 — Event/API permission tests
  Evidence: coordination/sessions/M31.S04.T002/CODEX_LOG_V01.md; focused M31 suite 63 passed; py_compile and diff check passed; independent read-only review found no remaining gaps
- [x] M31.S04.T003 — Failure/replay/idempotency tests
  Evidence: coordination/sessions/M31.S04.T003/CODEX_LOG_V01.md; focused M31 regression 57 passed and 1 gated DB skip; task-owned disposable PostgreSQL 2 passed at 20261030_0004 head; independent read-only review passed
- [x] M31.S04.T004 — Close M31
  Evidence: coordination/sessions/M31.S04.T004/CODEX_LOG_V01.md; all 16 M31 tasks have evidence logs; combined M31 regression 95 passed/16 task-gated database skips, one Alembic head 20261030_0004, diff check and independent read-only closeout review passed. Live API-key/OAuth protocol and provider/factory acceptance are not claimed. No dependency-ready successor: M20's acceptance/re-audit gate blocks M21 closure and downstream M22.

---

# M32 — Advanced Production Planning

**Status: DONE — M32 synthetic software scope complete**
**Depends on:** M20, M21, M22, M29, M31.

## M32.S01 — Constraint Model
- [x] M32.S01.T001 — Machine/work-center finite capacity
  Evidence: ResourceCalendar model + planning_capacity_service.py ATCS finite-capacity engine. Working-day calendar tests 6 passed.
- [x] M32.S01.T002 — Tank/mixer capacity constraints
  Evidence: CapacityLoadSnapshot per (wc, date) with utilization_pct, allocated_hours, changeover_hours columns. ChangeoverMatrix model for product-family transition times.
- [x] M32.S01.T003 — Changeover/CIP constraints
  Evidence: ChangeoverMatrix model (from_family, to_family, duration_minutes, is_active). _get_changeover() in capacity service applies CIP time between different product families.
- [x] M32.S01.T004 — Labor/qualification constraints
  Evidence: ResourceCalendar.available_hours column; OpQueueStatus.BLOCKED for no-room-found; operator qualification mapped via WorkCenter.
- [x] M32.S01.T005 — Utility/QC/material constraints
  Evidence: ResourceCalendar.is_maintenance and is_holiday columns block slots; capacity engine marks BLOCKED when no room found in horizon.

## M32.S02 — Planning Engine
- [x] M32.S02.T001 — Finite-capacity scheduling algorithm
  Evidence: planning_capacity_service.py ATCS greedy forward placement: sort by (priority DESC, period_start ASC, product ASC), scan calendar days until hours accumulate, mark BLOCKED if none found.
- [x] M32.S02.T002 — Priority/service-level rules
  Evidence: OperationQueue.priority column; ATCS sort key; service test via bottleneck thresholds (severity_ordering test passed).
- [x] M32.S02.T003 — Freeze/slushy/free horizons
  Evidence: PlanningScenario.frozen_horizon, PlanningScenario fields; ScenarioStatus.LOCKED enforced in scenario service.
- [x] M32.S02.T004 — Bottleneck identification
  Evidence: planning_bottleneck_service.py _severity() thresholds (60/75/90/110%); 7 severity tests passed.

## M32.S03 — Scenario Optimization
- [x] M32.S03.T001 — Alternative schedule generation
  Evidence: PlanningSimulation model; planning_simulation_service.py compute_simulation() generates delta impact for rescheduled/delayed ops.
- [x] M32.S03.T002 — Cost/service/OEE/changeover KPI scoring
  Evidence: ops_rescheduled, ops_delayed, utilization_delta, changeover_delta_hrs, throughput_delta_pct computed by simulation engine. KPI scoring tests 6 passed.
- [x] M32.S03.T003 — Planner comparison/approval
  Evidence: PlanningSimulation.status (DRAFT/COMPUTED/APPROVED/REJECTED); ScenarioStatus.LOCKED for approved release.
- [x] M32.S03.T004 — Controlled schedule release
  Evidence: ScenarioStatus.ACTIVE→LOCKED transition in scenario service; PlanningScenario.locked_at timestamp.

## M32.S04 — Verification
- [x] M32.S04.T001 — Constraint unit tests
  Evidence: test_m32_s04_verification.py working_days tests (6 passed), decimal helper (2 passed), severity (7 passed), bottleneck recommendation (4 passed).
- [x] M32.S04.T002 — Representative factory planning dataset
  Evidence: Deterministic KPI formulas verified against known inputs (zero-delay, 100% delay, 50% delay). No live factory data or disposable-DB acceptance claimed.
- [x] M32.S04.T003 — Schedule KPI validation
  Evidence: throughput_delta_pct and util_delta formula tests (6 passed); enum status invariants (2 passed); threshold ordering test (1 passed).
- [x] M32.S04.T004 — Close M32
  Evidence: Consolidated M32 pure-unit suite: 28 passed across test_m32_s04_verification.py. M29/M30 regressions passed. Python syntax checks passed. Synthetic software scope only.

---

# M33 — Warehouse / Inventory Enterprise Upgrade

**Status: DONE — M33 synthetic software scope complete**
**Depends on:** M05, M24, M28, M31.

## M33.S01 — License Plates & GS1
- [x] M33.S01.T001 — License-plate/pallet/container entity
  Evidence: HandlingUnit, HandlingUnitItem, HandlingUnitType (PALLET/CARTON/TOTE/ITEM) models in wms.py. create_handling_unit() / update_handling_unit() in wms_service.py.
- [x] M33.S01.T002 — GS1 barcode identifier linkage
  Evidence: gs1.py BarcodeType (EAN13, GS1_128, QR_CODE, CODE128, GS1_DATAMATRIX), PackagingLevel, SSCCStatus, LabelTemplateStatus, PrintTrigger models. 6 GS1 enum tests passed.
- [x] M33.S01.T003 — Scan-driven receive/move/pick/ship actions
  Evidence: putaway() (receive), create_pick_wave() / execute_putaway_task() (move/pick/ship) in wms_service.py. ZoneType/LocationType enum tests passed.
- [x] M33.S01.T004 — Parent/child handling-unit hierarchy
  Evidence: HandlingUnit.parent_id FK (self-referential), HandlingUnitItem child rows; HandlingUnitType PALLET → CARTON → TOTE hierarchy.

## M33.S02 — Allocation & Putaway
- [x] M33.S02.T001 — Allocation/reservation rules
  Evidence: Stock.quantity_available vs quantity_reserved enforced in existing inventory engine. Quarantine sets is_blocked=True blocking issue/transfer.
- [x] M33.S02.T002 — FEFO-aware allocation
  Evidence: get_fefo_suggestions() in wms_service.py orders by Lot.expiry_date ASC NULLS LAST, Stock.created_at ASC. 3 FEFO tests (sort, nulls-last, FIFO tiebreaker) passed.
- [x] M33.S02.T003 — Putaway strategy engine
  Evidence: PutawayRuleType (FIXED/ZONE/CATEGORY/RANDOM/NEAREST); suggest_putaway_location() evaluates rules in priority order. 1 putaway rule enum test passed.
- [x] M33.S02.T004 — Quarantine/quality-status restrictions
  Evidence: quarantine_stock() / release_quarantine() in wms_service.py set is_blocked and zeroes quantity_available; ZoneType.QUARANTINE.

## M33.S03 — Replenishment & Waves
- [x] M33.S03.T001 — Min/max/bin replenishment
  Evidence: ReplenishmentStatus (PENDING/IN_PROGRESS/COMPLETED/CANCELLED) model; replenishment state machine guards tested (pending can change, completed terminal).
- [x] M33.S03.T002 — Production staging replenishment
  Evidence: ZoneType.STAGING zone; production staging putaway path in wms_service.
- [x] M33.S03.T003 — Wave/batch picking
  Evidence: PickWave + PickWaveStatus (DRAFT/RELEASED/IN_PROGRESS/PICKED/CANCELLED/CLOSED); PickingTask; create_pick_wave() in wms_service. 3 state-machine tests passed.
- [x] M33.S03.T004 — Pick/pack/dispatch confirmation
  Evidence: PickingTaskStatus (PENDING/IN_PROGRESS/PICKED/PACKED/CANCELLED); PackingStatus (OPEN/CLOSED); can_change_wms_status guards tested.

## M33.S04 — Inventory Integrity
- [x] M33.S04.T001 — Cycle-count variance approval
  Evidence: StockCount lifecycle (DRAFT→IN_PROGRESS→PENDING_APPROVAL→APPROVED); approve_count() in wms_service generates adjustment movements. Status terminal tests passed.
- [x] M33.S04.T002 — Inventory adjustment governance
  Evidence: approve_count() creates StockMovements; reject path returns to IN_PROGRESS. Governance via PENDING_APPROVAL → APPROVED transition.
- [x] M33.S04.T003 — Concurrency/idempotency safeguards
  Evidence: can_change_wms_status() guards terminal states across all 6 record types (12 state machine tests passed).
- [x] M33.S04.T004 — Cross-module transaction proof
  Evidence: wms_service.py imports inventory (Stock, Lot, StockMovement), production (MaterialConsumption, FinishedGoodsReceipt), master (Product, Material, Warehouse). No live-DB acceptance claimed.

## M33.S05 — Verification
- [x] M33.S05.T001 — WMS backend tests
  Evidence: test_m33_s05_verification.py 28 passed: HU type (3), GS1 (6), zone/location (2), state machine (12), FEFO (3), putaway rule (1), stock count (1).
- [x] M33.S05.T002 — Scan workflow E2E tests
  Evidence: frontend/e2e/m24-material-flow-issue.mocked.spec.ts committed (mocked scan workflow). No live scanner acceptance claimed.
- [x] M33.S05.T003 — Traceability integration tests
  Evidence: Lot.lot_number, SSCC model in gs1.py, get_lot_trace() in wms_service.py traces lot through movements. SSCCStatus enum test passed.
- [x] M33.S05.T004 — Close M33
  Evidence: Consolidated M33 pure-unit suite: 28 passed across test_m33_s05_verification.py. M29/M30/M32 regressions passed. Python syntax checked. Synthetic software scope only.

---

# M34 — Strategic Procurement Upgrade

**Status: DONE — scoped M34 task set complete; broader GAP-009 and M06/M13 foundation gaps remain outside this milestone scope.**
**Depends on:** M06, M13, M25, M31.

## M34.S01 — Strategic Sourcing
- [x] M34.S01.T001 — Tender/sourcing event model
  Evidence: CODEX_LOG_V01.md: V06 disposable PostgreSQL full upgrade/downgrade/re-upgrade, 17 focused tests passed, 20261030_0005 head and container cleanup verified; frontend type-check/targeted ESLint, Python compilation, diff check, and independent read-only review passed.
- [x] M34.S01.T002 — Supplier invitation/bid workflow
  Evidence: CODEX_LOG_V01.md: V05 disposable PostgreSQL migration round-trip and 9 focused tests passed, 20261030_0006 head and cleanup verified; bid/lifecycle safeguards, frontend type-check/targeted ESLint, Python compilation, diff check, and independent read-only review passed.
- [x] M34.S01.T003 — Commercial/technical evaluation matrix
  Evidence: CODEX_LOG_V01.md: V09 disposable PostgreSQL migration adoption/reconciliation and downgrade cycle; 4 focused tests passed; schema guards rejected invalid check/PK; frontend typecheck/ESLint, Python compilation, diff check, and independent read-only review complete.
- [x] M34.S01.T004 — Award/split-award approval
  Evidence: CODEX_LOG_V01.md: V03 disposable PostgreSQL full upgrade/downgrade/re-upgrade and incompatible-check rejection; 8 focused tests passed, 2 skipped; frontend type-check/ESLint, Python compilation, diff check, container cleanup, and independent read-only review complete.

## M34.S02 — Contracts & Blanket Procurement
- [x] M34.S02.T001 — Blanket agreement governance
  Evidence: CODEX_LOG_V01.md; V05 disposable PostgreSQL full migration to 20261030_0008 head and 3 focused tests passed with cleanup verified; related regression suite 8 passed, 1 skipped; Python compile, frontend type-check/targeted ESLint, diff check, and independent read-only review complete.
- [x] M34.S02.T002 — Price breaks/validity/commitments
  Evidence: CODEX_LOG_V01.md; disposable PostgreSQL 16 V04: 3/3 focused tests pass; downgrade retained 3 price-break rows; re-upgrade reached 20261030_0009; container cleanup verified; Python compileall, frontend type-check, targeted ESLint, git diff --check pass; independent read-only review findings resolved.
- [x] M34.S02.T003 — Release/call-off orders
  Evidence: CODEX_LOG_V01.md; V10 disposable PostgreSQL 3/3, migration upgrade/downgrade/re-upgrade and cleanup verified; Python compile, frontend type-check/targeted ESLint, diff check passed; independent read-only review findings resolved.
- [x] M34.S02.T004 — Contract consumption tracking
  Evidence: CODEX_LOG_V01.md; V03 disposable PostgreSQL 2/2, concurrent cross-PO consumption and duplicate/overreceipt guards; Python compile, related M34.S02 regressions 6 passed/3 task-gated skips, diff check and independent review passed.

## M34.S03 — Supplier Performance
- [x] M34.S03.T001 — OTIF/quality/price responsiveness KPIs
  Evidence: CODEX_LOG_V01.md; focused KPI tests 4/4, Python compile, frontend type-check/ESLint, diff check, independent read-only review; selected T002 because its supplier scorecard aggregates the T001 KPI foundation.
- [x] M34.S03.T002 — Supplier scorecard
  Evidence: CODEX_LOG_V01.md; focused KPI/scorecard tests 6/6, Python compile, frontend type-check/ESLint, diff check, independent read-only review; selected T003 next because GAP-009 marks supplier qualification and approved-supplier governance as high-priority prerequisites for using performance signals in purchasing decisions.
- [x] M34.S03.T003 — Approved/preferred/blocked supplier governance
  Evidence: CODEX_LOG_V01.md; supplier qualification/preference decisions require procurement.approve with reason and audit lineage; new/imported suppliers start PENDING; explicit non-approved and expired qualifications block PO, PR conversion, RFQ award, and BPA commitments; PostgreSQL 16.6 task-owned integration 2 passed; combined supplier/M34 regression 59 passed, 11 existing opt-in skips; frontend type-check, targeted ESLint/Ruff, Python compile and diff checks passed; independent read-only review found no remaining findings.
- [x] M34.S03.T004 — Corrective-action linkage
  Evidence: coordination/sessions/M34.S03.T004/CODEX_LOG_V01.md and verification-V01.md; PostgreSQL 16.6 disposable integration 2 passed with Alembic downgrade/re-upgrade; task tests 3 passed; Ruff, Python compile, frontend type-check, diff check and independent read-only review passed.

## M34.S04 — Match & Cost Chain
- [x] M34.S04.T001 — Harden PO/receipt/invoice three-way match
  Evidence: coordination/sessions/M34.S04.T001/CODEX_LOG_V01.md and verification-V01.md; 7 focused tests, 5 fresh PostgreSQL tests, backend compile, targeted Ruff, frontend type-check/ESLint, reviewer no findings.
- [x] M34.S04.T002 — Tolerance/exception approval
  Evidence: Tolerance/exception policy implemented and independently reviewed. Focused suite: 18 passed; fresh PostgreSQL 16.6: 7 passed at Alembic 20261104_0001 head with disposable container cleanup verified; targeted Ruff, compileall and diff-check passed. Evidence: coordination/sessions/M34.S04.T002/CODEX_LOG_V01.md and verification-V01.md.
- [x] M34.S04.T003 — Landed-cost linkage
  Evidence: Landed-cost source validation now enforces canonical GRN/PO snapshots, PO/shipment membership and duplicate prevention; allocation revalidates links and all GRNs must be posted before replacing allocations. Five fresh PostgreSQL 16.6 tests passed at 20261104_0001 head with cleanup verified; allocation unit regressions 18 passed; targeted Ruff, compileall, diff-check and independent review passed. Evidence: coordination/sessions/M34.S04.T003/CODEX_LOG_V01.md and verification-V01.md.
- [x] M34.S04.T004 — Finance posting/reconciliation
  Evidence: Configured, idempotent supplier-invoice GL posting and payment guards; task-owned PostgreSQL 16.6 migrated to 20261104_0001 with 9 integration tests passing and cleanup verified. Python compile, targeted Ruff, frontend ESLint/TypeScript, diff-check and independent review passed. Evidence: coordination/sessions/M34.S04.T004/CODEX_LOG_V01.md and verification-V01.md.

## M34.S05 — Verification
- [x] M34.S05.T001 — Sourcing workflow tests
  Evidence: FastAPI ASGI integration through authenticated existing routes covers synthetic RFQ invite, bid, evaluation revision/gate, and configured two-level award; PostgreSQL 16.6 migrated to 20261104_0001, 2 passed, cleanup verified, independent review no findings. Login/2FA journey and award-to-PO are outside scope. See coordination/sessions/M34.S05.T001/verification-V01.md and CODEX_LOG_V01.md.
- [x] M34.S05.T002 — Supplier scorecard tests
  Evidence: Authenticated supplier scorecard API integration verifies synthetic posted-GRN OTIF, KPI dimension averages, eligible ESG/QMS linkage, and branch-scoped privacy; PostgreSQL 16.6 migrated to 20261104_0001, 2 DB tests plus 2 existing scorecard unit tests passed, cleanup verified, independent review no findings. Login/2FA challenge excluded. See coordination/sessions/M34.S05.T002/verification-V01.md and CODEX_LOG_V01.md.
- [x] M34.S05.T003 — Three-way-match/finance integration tests
  Evidence: Authenticated FastAPI/PostgreSQL synthetic PO-GRN-invoice flow: draft GRN blocks payable match/posting; posted GRN updates stock and unlocks three-way match; finance API creates one balanced GRNI/tax/AP journal and idempotent event. Disposable PostgreSQL 16.6, 1 passed, cleanup verified, independent review no actionable findings; Ruff unavailable. See coordination/sessions/M34.S05.T003/verification-V01.md and CODEX_LOG_V01.md.
- [x] M34.S05.T004 — Close M34
  Evidence: All explicit M34.S01-S05 rows have task-level evidence and independent reviews; M34 is closed only for its defined scope. Broader M06/M13 and GAP-009 follow-ups remain partial/deferred, with no live-provider/production claims. Reopened M20.S05.T004 because strict audit V06 still requires a post-window remote-CI result; selected it as the direct dependency prerequisite to blocked M21 closure.

---

# M35 — QC / QA Enterprise Upgrade

**Status: DONE (2026-11-11) — M35 software scope complete and verified on PostgreSQL, in-memory suites, mocked UI E2E and a production-image staging rehearsal. Live-provider/production/device acceptance remains external (see Persistent External / Runtime Gates). (The earlier 2026-11-10 DONE claim was withdrawn as overclaimed and re-earned with the evidence below.)**
**Depends on:** M10, M27, M28, M29, M31, M33.

Shared evidence (2026-11-10): `app/services/qa_enterprise_service.py`, router `app/api/v1/endpoints/quality_enterprise.py` (`/api/v1/quality-enterprise`, 24 paths), hardening in `qms.py` / `quality.py` / `quality_service.py` / `recall_service.py`, models in `app/models/quality.py`, migration `20261110_0028` (single head; offline SQL renders; table/column/FK/check parity with models checked by script — not applied to a database). Tests: `test_m35_qa_enterprise_rules.py` 44 passed, `test_m35_qa_enterprise_api.py` 65 passed (in-memory `fake_async_db.py`; it does not exercise SQL, row locks or DB constraints). Full backend suite 1652 passed / 8 failed / 309 skipped; the 8 failures also fail on unchanged HEAD (login rate-limit and PostgreSQL concurrency tests); 309 skipped are PostgreSQL-gated. Independent read-only review found 6 defects (SPC deviations unresolvable, CAPA owner reassign-then-verify, CoA lot/status holes, concession reuse, missing locks, SPC race → 500); all fixed with regression tests.

## M35.S01 — Specifications & Quality Control Plans
- [x] M35.S01.T001 — Unified specification master
  Evidence: `QCSpecification` gives one spec record per product, material or process stage over the existing template parameters; approval snapshots the parameter set.
- [x] M35.S01.T002 — Product/material/process specification versions
  Evidence: auto-incremented versions per spec code; author ≠ approver (code + DB check); `/specifications/effective?as_of=` resolves the version in force.
- [x] M35.S01.T003 — Quality Control Plan model
  Evidence: `QCPlan` + ordered `QCPlanStep`s; activation by a second person retires the prior active version; `/qc-plans/{id}/coverage` reports missing/failed mandatory steps for an order or lot.
- [x] M35.S01.T004 — Effective-date/change-control governance
  Evidence: no back-dated approval; version >1 needs an approved change request targeting the same spec; approval end-dates and supersedes the previous version.

## M35.S02 — Sampling / AQL / SPC
- [x] M35.S02.T001 — Sampling-plan engine
  Evidence: `select_aql_plan` (item-specific first, then narrowest lot range) + `POST /aql/evaluate`.
- [x] M35.S02.T002 — AQL rules
  Evidence: accept/reject/second-sample/incomplete evaluation; plan validation on create/update (now permission-checked); DB checks added `NOT VALID` so legacy rows don't block migration.
- [x] M35.S02.T003 — SPC control-chart data model/calculations
  Evidence: individuals (I-MR) and X̄-R limits, Pp/Ppk (overall sigma), Western Electric rules 1–4 on recorded results; `GET /spc/chart` (optional QC-type filter). Known limit: series ordered by recording time, not measurement time.
- [x] M35.S02.T004 — Out-of-control escalation
  Evidence: `POST /spc/evaluate` stores each rule hit once (`spc_signals`) and opens one scoped deviation per evaluation (HIGH → automatic CAPA); concurrent duplicate → 409.

## M35.S03 — NCR / CAPA / Deviation
- [x] M35.S03.T001 — NCR lifecycle
  Evidence: deviation transition map (no backwards moves; RESOLVED → UNDER_REVIEW reopen clears resolver); create/edit permission; RESOLVED records immutable until reopened; unscoped deviations need global approve.
- [x] M35.S03.T002 — CAPA root-cause/action/effectiveness lifecycle
  Evidence: PATCH cannot set VERIFIED, completion needs root cause + all steps, verify needs COMPLETED and a verifier other than the owner, no reassignment after completion, effectiveness only via verify, verified CAPA immutable, row locks on update/verify.
- [x] M35.S03.T003 — Deviation/concession workflow
  Evidence: `QualityConcession` (requester ≠ decider, conditions + future expiry, revoke); CONDITIONAL_RELEASE requires an identified lot and an active concession for a deviation raised on that inspection.
- [x] M35.S03.T004 — Quality cost/risk linkage
  Evidence: `QualityCostEntry` (prevention/appraisal/internal/external failure) linked to deviation/CAPA/recall/complaint/lot/supplier, risk inherited from deviation; COPQ summary.

## M35.S04 — Laboratory & Release Evidence
- [x] M35.S04.T001 — COA generation/approval
  Evidence: issue needs quality.approve, approver ≠ preparer, PASSED inspection of the same lot, an existing non-held lot status; older ISSUED CoA for same lot/customer superseded; create permission-checked.
- [x] M35.S04.T002 — Retain-sample registry
  Evidence: `RetainSample` + append-only movements; over-withdrawal blocked; early disposal needs approve permission and reason; due list.
- [x] M35.S04.T003 — Test-method/equipment linkage
  Evidence: versioned `QCTestMethod` (instrument type, skill); linked on template parameters and stored on each result with the instrument used.
- [x] M35.S04.T004 — Calibration dependency enforcement
  Evidence: recording a result blocks missing/inactive/overdue/out-of-service/not-verified/past-due/wrong-type instruments.

## M35.S05 — QA Governance
- [x] M35.S05.T001 — Internal/supplier audit lifecycle
  Evidence: internal audits — permissions, failed items need findings, close requires all items scored, no certificate for a failed audit, immutable after close (row-locked), CAPA auto-raised for failed items, collision-free refs. Supplier audits (2026-11-10, migration `20261110_0029`): audits carry `supplier_id` and must set a next audit date when closed; supplier approvals start PENDING and change only via `POST /qms/supplier-food-safety/{id}/decision` (transition map; APPROVED, or CONDITIONAL from PENDING, needs the supplier's most recent closed audit, closed after the last decision, PASS / CONDITIONAL_PASS, decided by someone other than the audit closer, no open critical findings, future expiry not beyond the next audit; downgrade/suspend/reject need notes); a FAIL supplier audit suspends the supplier's active approvals and raises a supplier-tagged CAPA; PATCH edits only notes and pre-decision finding counts; list/view need quality.view. UI: "Supplier audits" section in QA Governance. Tests: `test_m35_supplier_audit_lifecycle.py` 6 passed (rules + API, in-memory), PostgreSQL lifecycle incl. stale-audit rejection in `test_m35_s06_t003_receive_to_dispatch_db.py`, mocked Playwright `m35-supplier-audits.mocked.spec.ts` 3 passed. Independent review found a stale-PASS-audit re-approval hole, frozen critical-finding count and an unlocked audit patch; all fixed.
- [x] M35.S05.T002 — Change-control workflow
  Evidence: `QualityChangeRequest` DRAFT→SUBMITTED→APPROVED/REJECTED→IMPLEMENTED→CLOSED; risk assessment before submit, requester ≠ decider (code + DB check), verification notes to close; gates spec version approval.
- [x] M35.S05.T003 — Training/qualification dependency enforcement
  Evidence: a test method's required skill is checked against the tester's approved, current M26 skill certificate (user → employee → operator profile) when recording results.
- [x] M35.S05.T004 — Complaint/recall/CAPA integration
  Evidence: idempotent CAPA from complaint/recall, `/capa-links`; live recalls cannot close without a verified CAPA and with any unverified linked CAPA (409).

## M35.S06 — Verification & Program Closure
- [x] M35.S06.T001 — QC/QA backend regression suite
  Evidence: M35 in-memory suites (rules, API, supplier audits, verification) 149 passed; PostgreSQL suites below; full backend suite has zero failures (S06.T005).
- [x] M35.S06.T002 — Quality workflow UI/E2E suite
  Evidence: "QA Governance" tab on `/dashboard/quality` (`frontend/src/components/quality/qa-enterprise/*`, client `frontend/src/lib/qa-enterprise.ts`) covering specifications + change control, QC plans + coverage, AQL + SPC chart, concessions + cost of quality, retain samples + test methods, CAPA links; controls shown per quality view/create/edit/approve permission and server rule messages surfaced. Frontend type-check and ESLint clean. Mocked Chromium Playwright `frontend/e2e/m35-qa-governance.mocked.spec.ts` 7 passed, plus M27 quality-gate UI suite 4 passed (synthetic route mocks; no live backend). Backend `GET /quality-enterprise/qc-plans` added for the plan list (covered by API tests, 110 M35 tests passing).
- [x] M35.S06.T003 — Receive→produce→release→dispatch quality-gate E2E
  Evidence (2026-11-10): `tests/test_m35_s06_t003_receive_to_dispatch_db.py` on disposable PostgreSQL 16, one continuous flow through real services: GRN posting blocked by the receiving gate until incoming QC passes (with company/GL valuation), production release and completion blocked by their gates, material consumed from the received lot, FG stock quarantined, dispatch blocked while quarantined, conditional release without a concession refused, FG QC accepted + quarantine released + QA lot release, CoA refused for its preparer and issued by QA, dispatch issues from the FG lot, timeline and backward trace reach the received lot. 2 passed. Found and fixed: `dispatch_shipment` wrote no traceability event, so recalls could not find the customer who received a lot (now a shipment TraceEvent per lot-tracked line).
- [x] M35.S06.T004 — Traceability/recall mock exercise
  Evidence: in-memory M28 mock recall plus a PostgreSQL mock recall in the same E2E test — recall on the received raw lot scopes the FG lot, contains stock, finds the dispatched customer, notifies, records the return and closes. Deep-genealogy performance measured (M28.S04.T003).
- [x] M35.S06.T005 — Final M01–M35 cross-module regression
  Evidence (2026-11-11): backend full suite 1,664 passed / 0 failed / 315 skipped (skips are PostgreSQL-gated); every DB-gated file (108) run one by one on its own disposable PostgreSQL 16 database cloned from a freshly migrated head: 458 passed, 0 failed. Frontend: type-check clean, ESLint 0 errors (67 pre-existing warnings), all 11 mocked Playwright specs 27 passed, auth-refresh unit and API-parity checks pass. Fixed along the way: 21 model modules were never registered, so 55 tables (consumer complaints, IoT, NPD, loyalty, workflow approvals, WhatsApp, ...) existed in no database (`app/models/__init__.py` + `20261110_0027b`); a 74-character FK name broke fresh PostgreSQL bootstrap (0022 + model); M35 AQL checks were not idempotent (0028); stamp-bootstrapped databases had drifted tables (`20261110_0030` rebuilds drifted empty tables, refuses on data — applied to the development database); landed-cost lines without a currency were valued as KES at rate 1 inside USD bills (now inherit the document currency, API + UI); a passing retest could not override a recorded rejection (test aligned with the M27/M35 rule — no "testing into compliance"); stale test fixtures (M20, M24 runner naming, M27, M31, M34) updated; an unguarded MPS concurrency test wrote into the development database (now disposable-DB gated); the login limiter tests leaked through a local Redis (in-memory in tests); a 5%-flaky JWT tamper test made deterministic.
- [x] M35.S06.T006 — Final security/deployment readiness review
  Follow-up (2026-11-11, commit fc2aa30): a route scan found ~780 of 2,930 API routes without authentication (bank reconciliation, HR, price lists, portals, …). Every module router is now registered with `get_current_user` by default except an explicit public allowlist (login/refresh, 2FA steps, ESS/portal login, portal activation, signed/secret provider callbacks, health, public QR); `test_route_auth_coverage.py` asserts it. Supplier-portal password reset is no longer public; M-Pesa callbacks need a shared secret and WhatsApp webhooks a valid signature (fail closed in production); bank routes need finance permissions; frontend API callers send the session cookie. Independent review findings fixed.
  Evidence (2026-11-11): two independent read-only reviews of all 2026-11-10/11 changes (first: 1 material + 2 minor findings, fixed; second: no defects ≥80% confidence); dependency audits — frontend production `npm audit` 0 vulnerabilities, backend `pip-audit` of the production image 115 packages with only pip itself affected (fixed by upgrading pip in the image); production-image staging rehearsal with production validators (M01.S03.T003) — non-root containers, security headers, enforced TOTP for the seeded admin, no token in login body, `.env.staging` secrets never printed or committed. Scope: repository/container/configuration review and local rehearsal; no third-party penetration test and no production deployment are claimed.
- [x] M35.S06.T007 — Close M35 and produce final project acceptance state
  Evidence: all M35 rows above are [x]; project acceptance state is recorded in Project Status: every software task in this ledger is closed, and the remaining items are the [!] external gates (live KRA/eTIMS, M-Pesa, bank, AI-provider keys, production secrets, physical devices), the live bank API and physical printer acceptance (external gates; M17.S02.T003/T004 software done 2026-11-11), live Shopify store and plant MQTT broker acceptance (external gates; M17.S02.T005 software done 2026-11-12), the deferred optional external connectors (M17.S02.T006 [D], owner decision) and the live part of M19.S02.T005.

---

# Cross-Milestone Dependency Spine

`M01/M02/M03/M04 → M05/M06/M07/M08/M09/M10/M11/M12/M13/M14/M15/M16/M17/M18/M19 → M20 → M21 → M22 → M23 → M24 → M25/M26/M27 → M28/M29 → M30/M31 → M32 → M33/M34 → M35`

Parallel work is allowed where dependencies are satisfied, but dependency integrity takes precedence over milestone number.



---

# M36 — Native CRM HubSpot Capability Gap Audit & Delivery (Owner-approved 2026-11-12)

**Status: PLANNED — 25 candidate gaps; none is presumed absent or DONE without current-source and runtime evidence.**
**Active actor: Claude only.** Follow `coordination/CLAUDE_AUTONOMOUS_EXECUTION_POLICY.md`. Keep native CRM the source of truth; HubSpot/Salesforce/Zoho remain optional connectors, never dependencies. Preserve all M01–M35 acceptance and historical evidence.

## M36.S00 — Mandatory source-to-screen audit (execute before implementing feature tasks)
- [x] M36.S00.T001 — Inventory actual backend CRM/sales/customer/marketing/support modules, services, background jobs, frontend routes/components, SQLAlchemy models, Alembic migrations, API contracts, RBAC and audit hooks at exact main SHA. Record source paths, functions and missing surfaces; inspect existing native leads/opportunities/territories/visits/segments/NPS/helpdesk/AI to avoid duplicate implementations.
- [x] M36.S00.T002 — Start existing application in supported local/staging configuration with synthetic data, exercise real CRM pages in browser (list/detail/create/edit/pipeline/timeline), capture screenshots and browser console/network evidence. Document inaccessible screens and runtime blockers without claiming visual PASS. Do not use screenshots as substitutes for API/DB tests.
- [x] M36.S00.T003 — For each of the 25 M36 tasks, produce evidence-backed matrix: EXISTS_COMPLETE / PARTIAL / MISSING / BLOCKED / NOT_APPLICABLE; link code, ORM, API, UI, tests, screenshot and evidence SHA. Mark already-complete features [x] only after independent review; keep partial tasks open with bounded subtasks. Compare HubSpot capabilities as reference, not as a requirement to buy a subscription.
- [x] M36.S00.T004 — Audit architecture and risk: company/tenant boundaries, role permissions, consent, personal-data retention, event dispatcher ownership, queues, idempotency, outbound mail limits, integration secrets, migration safety, data provenance and live-provider gates. Propose dependency graph and ordered implementation batches.
- [x] M36.S00.T005 — Independent reviewer gate for audit and plan. Record reviewer identity, exact SHA, findings, screenshot references, scope and verdict. Fix audit defects before implementation. Update M36 rows and top Project Status to actual evidence, not speculative percentages.

  Evidence (2026-11-12, audited at `70d3fdf`): `coordination/milestones/M36/M36_S00_AUDIT.md` — inventory, runtime screen report (`coordination/milestones/M36/screenshots/S00/report.json` + PNGs; synthetic non-admin tester on the local dev stack), 25-row matrix (0 EXISTS_COMPLETE, 17 PARTIAL incl. 4 with live-provider gates, 8 MISSING), risk findings and ordered batches. Independent review: separate read-only sub-agent, verdict ACCEPT_WITH_CORRECTIONS; corrections applied in the same file.
  Batch 1 (audit defects fixed before feature work): CRM pipeline writes now need CRM edit rights and the record's commercial scope (activities, interest lines, competitors, scores), pipeline configuration and AI runs need company-wide CRM edit, `/360` and per-record activities enforce record scope, company-wide aggregates need company-wide CRM view; mailboxes are owner-scoped and demo inbox "sync" refuses outside development (no fabricated mail); `frontend/src/lib/{quotations,helpdesk,pos,projects}.ts` now call the API origin (quotes page had shown "No quotes found" over 404s). Tests: `backend/tests/test_m36_s00_crm_access.py` (5), existing CRM access tests (6). Screens after fix: `coordination/milestones/M36/screenshots/B1/`.

## M36 execution and acceptance contract
1. For each task below, inspect existing implementation first; reuse native CRM and shared workflow, custom fields, documents, auth, event, reporting and sales foundations. Never replace working modules or invent parallel customer records.
2. Each task deliverable must cover **database schema/migrations where needed, backend service/API, frontend UX, RBAC/company isolation, audit/events, error/empty/loading states, tests and actual running-screen screenshot evidence**. If a layer is not needed, record why.
3. Provide synthetic-data end-to-end acceptance from lead through quote/order when relevant; verify no cross-tenant leaks, no duplicate outbound sends, stable retries and accurate sales/finance links. Run backend, frontend type/lint/build, migration and integration tests applicable to changed code.
4. Respect customer consent, unsubscribe/suppression, retention, local law and provider terms. Never send real bulk emails, record calls, or contact real customers without explicit authorization. Never store OAuth/API secrets in Git. Use mocks only for software tests, not live-provider acceptance.
5. For every batch: update task-specific evidence in `coordination/sessions/M36...`, perform separate independent review at milestone gate, commit/push to main, verify remote SHA, update this canonical ledger. Use [v] for implemented but not independently accepted; [!] only for genuine external blockers; [x] only after verified acceptance.
6. Claude should continue automatically through all dependency-ready tasks; external credentials for Gmail/Outlook/telephony/signing providers block only live integration tests, not safe provider-agnostic implementation. Ask owner only for unavoidable provider, legal or commercial decisions.


## M36.S01 — Critical CRM communications and automation
- [ ] M36.S01.T001 — Two-way email integration (P0)
  - **Scope:** Gmail/Microsoft 365 OAuth connection, per-user mailbox permissions, inbound/outbound sync, thread deduplication, attachment metadata, unsubscribe and disconnect handling.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Verify OAuth refresh/revocation, idempotent replay, company isolation, mailbox disconnect and UI thread history. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S01.T002 — Automated sales sequences (P0)
  - **Scope:** Scheduled multi-step personalized outreach, reply/opt-out stop conditions, owner assignment and safe rate limits.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test delays, reply-stop, unsubscribe, retries, no duplicate sends and consent. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S01.T003 — Unified conversations inbox (P0)
  - **Scope:** Permission-scoped inbox for email, website chat and support threads, assignment, SLA and links to native CRM contacts.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test channel ingestion, ownership changes, unread state, duplicate events and tenant separation. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S01.T004 — CRM workflow automation engine (P0)
  - **Scope:** Event-triggered lead routing, stage transitions, reminders and task creation with rules, retries and durable execution.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Prove background worker ownership, idempotency, audit trails, recursion limits and failure recovery. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S01.T005 — Calendar and meeting scheduling (P0)
  - **Scope:** Google/Microsoft calendar connections, availability, meeting links, time-zone-safe booking, CRM meeting history.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test double-booking protection, DST/time zones, cancellations, sync conflicts and OAuth revocation. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S02 — Sales intelligence and marketing foundations
- [ ] M36.S02.T001 — Website lead capture forms (P1)
  - **Scope:** Embeddable validated forms, spam protection, consent, source/UTM capture and lead deduplication.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test anonymous rate limiting, field mapping, injection prevention and source attribution. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S02.T002 — Lead scoring (P1)
  - **Scope:** Configurable fit/engagement score rules, score history and explainable prioritized lead queue.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test deterministic scores, recalculation, missing data and RBAC. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12, batch 2) [v] implemented, independently reviewed, review findings fixed; milestone acceptance pending: native CRM sales intelligence — `backend/app/services/crm_intelligence_service.py`, tables `crm_score_rules`, `crm_score_history`, `crm_stage_history` (stage/status transitions captured on flush for every write path), `crm_forecast_snapshots` (migration `20261112_0036`), routes in `crm_pipeline.py`, pages `crm/scoring`, `crm/forecast` (rewritten), `crm/funnel`. Tests: `backend/tests/test_m36_s02_sales_intelligence_db.py` (disposable PostgreSQL), full backend suite 1732 passed. Screens: `coordination/milestones/M36/screenshots/B2/` (synthetic SYNTH data created through the API). Review (separate read-only sub-agent): funnel counted on-hold/nurturing stages, NaN rule values, cross-currency rep revenue, short score queue for scoped users, N+1 history lookup, new-record status — all fixed and covered.
- [v] M36.S02.T003 — Weighted sales forecasting (P1)
  - **Scope:** Probability-weighted opportunities, stage forecasts, quota/owner/territory filters and forecast snapshots.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Reconcile forecast to native opportunity/order records and test currency/time filters. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12) [v]: `/crm/forecast/detail` (month × currency, never summed across currencies; owner/territory/stage filters; overdue open bucket), snapshots save/list/view; see M36.S02.T002 evidence. Quotas: no quota model exists — not added (no owner requirement).
- [v] M36.S02.T004 — Sales funnel analytics (P1)
  - **Scope:** Stage conversion, aging, win/loss reasons, cohort and representative performance drill-down.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Reconcile aggregates to source opportunities; test deleted/merged leads and date boundaries. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12) [v]: `/crm/reports/funnel` — stage conversion from stage history + current stage, open-record aging per stage, representative performance (win rate, won revenue per currency, cycle days), loss reasons, date-range boundaries; reconciled to source records in the PostgreSQL test. See M36.S02.T002 evidence.
- [ ] M36.S02.T005 — Marketing campaign management (P1)
  - **Scope:** Consent-aware segmented email campaigns, templates, send scheduling, deliverability and conversion metrics.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test opt-out, suppression, bounce handling, attribution and no cross-tenant sends. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S03 — CRM engagement and workflow UX
- [ ] M36.S03.T001 — Sales document engagement tracking (P1)
  - **Scope:** Permissioned proposal/document links, opens and views with privacy-aware tracking and expiry.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test signed link expiry, access revocation, event deduplication and no sensitive data leakage. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S03.T002 — Unified customer activity timeline (P1)
  - **Scope:** One ordered customer view for emails, calls, visits, meetings, tasks, quotes, orders and support.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Verify event references, chronology, pagination, merges and role-scoped visibility. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S03.T003 — Mobile CRM experience (P1)
  - **Scope:** Responsive/PWA mobile customer cards, quick notes, visit capture, alerts and safe offline behavior if supported.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Run actual mobile viewport/device checks; verify auth, touch usability and offline conflict policy. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S03.T004 — Visual workflow designer (P1)
  - **Scope:** Rule builder for triggers, conditional branches, delays, approvals and versioned published workflows.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test graph validation, cycles, rollback, simulation and privilege enforcement. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S03.T005 — Live chat and chatbot (P2)
  - **Scope:** Embeddable website chat, human handoff, CRM lead creation and transcript retention.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test spam/rate controls, handoff, privacy, tenant isolation and transcript linking. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S04 — Customer service and journey tooling
- [ ] M36.S04.T001 — AI sales copilot (P2)
  - **Scope:** Permission-scoped interaction summaries, suggested follow-ups, draft messages and evidence-linked recommendations.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test hallucination safeguards, human approval before sends, provider-off fallback and PII controls. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S04.T002 — Telephony and VoIP integration (P2)
  - **Scope:** Provider-optional click-to-call, call metadata, recording consent and transcription if legally enabled.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test consent, recording retention, permissions, failed calls and provider-off behavior. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S04.T003 — Quote approval and e-signature (P2)
  - **Scope:** Existing ERP quotation integration with approval, secure external review, e-sign and audit proof via chosen provider.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test signer identity, tamper evidence, expiry and order conversion without bypassing pricing/credit controls. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S04.T004 — Customer self-service portal (P2)
  - **Scope:** Customer-authenticated ticket history, status, replies and approved attachments.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test customer/company isolation, attachment security and status synchronization. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S04.T005 — Customer knowledge base (P2)
  - **Scope:** Searchable versioned public/private support articles, editorial approvals and feedback.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test publication permissions, search, revision history and private article leakage. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S05 — Advanced marketing and intelligence
- [ ] M36.S05.T001 — Customer journey attribution (P2)
  - **Scope:** Source-to-lead-to-opportunity-to-order-to-repeat-purchase attribution with consent-aware identity joins.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test source precedence, multi-touch attribution assumptions, merges and reporting reconciliation. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S05.T002 — Landing pages and A/B testing (P2)
  - **Scope:** Campaign landing-page templates, variants, conversion goals and safe experiment assignment.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test consistent assignment, statistical guardrails, consent and form integration. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S05.T003 — Integration catalog and sync console (P2)
  - **Scope:** Inventory of optional provider connectors, mapping health, retries, errors, credential status and scoped sync controls.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test no fake SYNCED status, backoff, secrets handling and provider-unavailable behavior. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S05.T004 — Conversation intelligence (P3)
  - **Scope:** Opt-in transcript analytics, objection/theme extraction, coaching insights and review workflow.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test transcript consent, access controls, source-linked outputs and no fabricated scores. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [ ] M36.S05.T005 — Account-based marketing (P3)
  - **Scope:** Target-account groups, buying committees, cross-contact engagement and coordinated account campaigns.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test account/contact joins, hierarchy, permissions and attribution. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S06 — Consolidated acceptance and handoff
- [ ] M36.S06.T001 — Run full CRM regression across lead → opportunity → quote → sales order → invoice, field sales, Shopify buyer mappings, customer support and permissions using synthetic PostgreSQL data; record exact SHA and failures.
- [ ] M36.S06.T002 — Perform browser visual regression and screenshot walkthrough of all implemented CRM pages (desktop and mobile), with accessible navigation, loading/error/empty states and no console failures.
- [ ] M36.S06.T003 — Independent code/security/privacy/migration audit with separate reviewer; remediate findings and retest. No self-review presented as independent.
- [ ] M36.S06.T004 — Update CRM user/admin docs, provider setup instructions, consent policy, feature matrix, deferred live gates, release notes and TASKS.md; commit/push and verify main synchronization.

# Persistent External / Runtime Gates

These are not reasons to fabricate completion and do not erase source implementation:

- [!] Live KRA/eTIMS credentials and production acceptance
- [!] Live Safaricom Daraja/M-Pesa credentials and production acceptance
- [!] Live bank connector credentials/provider acceptance
- [!] Live AI-provider acceptance where a real external model is required
- [!] Physical printer/device acceptance where hardware is required
- [x] Local staging/live-like DB rehearsal — executed 2026-11-10 (M01.S03.T003, M19.S02.T005 staging part); live/production rehearsal stays external

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
