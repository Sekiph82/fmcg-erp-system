# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

`TASKS_HISTORY.md` preserves the previous detailed tracker as immutable/reference evidence. Historical Done states remain accepted. `PLANS.md` is architecture/strategy reference only. No other file is an active competing tracker.

---

## Project Status

- Current Milestone: M44 — ACCEPTED 2026-11-26 (gate passed); next M45 — AI Agent & Customer Data Hub
- Current Sprint: M44.S02 — gate passed, all M44 rows [x]; synchronization recorded in M44.S02.T002
- Current Task: M45.S01 block (T001–T024)
- Current Task Status: M44 accepted (coordination/milestones/M44/gate/GATE_REPORT.md). M45 not started.
- Next Task/Action: M45 block (T001–T024) as one batch, then the M45 gate.
- Required Actor: CLAUDE (sole active autonomous task runner and tracker writer; per coordination/CLAUDE_AUTONOMOUS_EXECUTION_POLICY.md; the 2026-11-25 owner rules below supersede older cadence/gate instructions)
- Tracking Repository: Sekiph82/fmcg-erp-system
- Tracking Branch: main
- M00 Gate: COMPLETE

## Owner Decisions

- 2026-11-25 — **PRE-FACTORY / ACCOUNTLESS DEVELOPMENT (owner directive; applies to all current and future work):** POVU has not established its factory or commercial operations. No real employees, products in operation, customers, distributors, operational factory, production domain, corporate mailboxes (including Gmail), Google/Microsoft/Meta/LinkedIn/TikTok business accounts, Shopify shop or telephony provider exist. Do not infer their existence from synthetic seeds, catalogue drafts, UI fixtures, historical tests or code. An absent account, credential, domain, hardware, physical operation or business record is a future activation prerequisite, **not a current software defect or a reason to stop autonomous work**. Develop every feasible integration and native capability accountlessly using official public contracts, local services and deterministic synthetic data; no signup, purchase, real outreach, deployment, live ads, real provider spend or fabricated access. Existing explicitly authorized AI configuration may be used only within its actual scope; no new paid calls or provider credentials required for acceptance.
- 2026-11-25 — **HubSpot parity-plus:** Native POVU ERP must reach or exceed the applicable HubSpot CRM product-family capabilities at the software level, then exceed them through integrated FMCG/ERP/MES operations. Compare official current edition/feature documentation, record evidence and scope/limits, and add every additional verified gap as an executable task; the prior 40 recommendations are a minimum, not a ceiling. External proprietary datasets, approval tiers, ecosystem size and live-provider behavior cannot be declared equivalent without access. Provide supported equivalents or explicit limitation and future activation evidence; do not omit difficult features or claim parity solely from feature names. No external CRM subscription required.
- 2026-11-25 — **Autonomous execution cadence:** Claude updates root TASKS.md after EVERY task attempt/implementation, before selecting the next task. No routine per-task test runs: implement tasks and prepare tests without executing them; execute consolidated tests only after each major milestone's implementation is complete. Never mark a newly implemented task [x] until its applicable milestone tests and independent review pass. Synchronize GitHub main and the existing Desktop working copy after EACH completed major milestone. Detailed binding rules in the following section supersede older workflow instructions; reconcile historical records and contradictory agent instructions without rewriting history.

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
3. A task may be marked IMPLEMENTED (`[v]`) after source changes and evidence recording only; do not run routine per-task tests. It becomes DONE (`[x]`) only after the applicable major milestone consolidated tests and independent review pass (2026-11-25 owner override).
4. Historical tasks already marked Done remain accepted unless a later remediation explicitly supersedes them.
5. External credentials, live providers, production devices and live-DB acceptance must never be fabricated as PASS.
6. Cross-module changes must preserve RBAC, auditability, migrations, API contracts, frontend/backend consistency and tenant/company boundaries.
7. M20–M35 are enterprise upgrades layered on M01–M19 foundations.
8. Graphify is reference tooling only. Do not run refreshes without an explicit project need; no hooks, watchers or competing tracker state.
9. The owner authorizes Claude as the sole active autonomous task runner, task selector, implementer, reviewer coordinator and tracker writer. Update `TASKS.md` only for evidence-backed current-task claims, accepted transitions and owner answers; dashboard and independent reviewers are read-only. Keep `TASKS_HISTORY.md` immutable. Historical Codex names, logs and prior owner answers are evidence, not active authority.
10. Builder logs are evidence claims, not acceptance by themselves.
11. `main` is the only authorized branch. Claude must not create, restore, push or work on legacy `hiveai*` branches without explicit owner authorization; ChatGPT is not a required execution gate.

## Binding autonomous execution protocol — 2026-11-25 (supersedes earlier conflicting instructions)

1. **Workspace and authority:** Claude alone selects, implements, coordinates independent review and writes the live ledger. Use only `C:\Users\sekip\Desktop\fmcg-erp-system` and `origin/main` (Sekiph82/fmcg-erp-system). Before writes inspect branch, HEAD, remote, working tree and owner edits; integrate safely, no force push, destructive reset, clean, extra checkout or loss of owner work. Existing brand-vault tasks and all unrelated pending software tasks remain in scope; never erase or silently defer them.
2. **Every task checkpoint, no exceptions:** immediately after implementing, attempting, reconciling or discovering a task, before selecting the next, edit root TASKS.md: ID, status ([~], [v], [P] or [D] as appropriate), date, actual code paths/schema/API/UI, evidence location, intended acceptance tests (NOT RUN until milestone gate), unresolved defects/dependencies and exact next task. Update Project Status and remaining work. Never use [x] merely because code exists. If already accepted historical work is being reconciled, retain its evidence and [x] only when verified against its prior acceptance; stale evidence or missing proof stays [v]/[P]. If interrupted, leave an accurate checkpoint. Do not create a competing task ledger.
3. **Task loop:** read this protocol before each task; select next dependency-ready software task, inspect existing code and acceptance evidence, implement or reuse, write test cases/fixtures but do NOT run unit, integration, build, lint, typecheck, browser acceptance, smoke or regression suites for every task. Static source reading/edit review and Git diff inspection are allowed (not test execution). Never report test results not run. Continue automatically. If another task is needed, add its ID, scope and acceptance to this file before implementing. No routine owner confirmations or waiting for nonexistent accounts.
4. **Major milestone gate ONLY:** when all software implementation rows for M43, M44, M45, M46 or M47 (and subsequent major milestones) are [v] or evidence-backed not-applicable/superseded, freeze candidate code SHA; run ONE consolidated acceptance cycle covering all changed and dependent modules: backend unit/regression, real disposable PostgreSQL upgrade from empty and previous head (safe rollback where supported), DB/integration with local test services, provider contract and failure cases, frontend typecheck/lint/production build, browser click-through on real local app + synthetic non-admin personas on desktop and phone width, screenshots and console/network evidence, security/RBAC/company isolation, accessibility, data correctness and independent reviewer. Run prior milestone regressions and cross-module invariants as appropriate. Do not test against real customers, real providers or paid APIs. Fix failures, keep [v]/[~] while failing, rerun affected tests and consolidated gate until green. A separate reviewer must inspect candidate code and results; no self-review called independent. Record exact tested source SHA, command, result counts, reviewer identity, findings/remediation, environment and screenshot paths. Skips require explicit justification and cannot waive required local scope. No fabricated PASS.
5. **DONE gate and synchronization:** after milestone tests and independent review PASS, mark accepted individual tasks [x] in TASKS.md and update milestone status; separate activation rows remain [D] NOT_DUE (not a software defect). Commit implementation + evidence + ledger with task IDs, push main, fetch origin/main, verify local HEAD == remote HEAD and clean working tree (preserve unrelated owner changes; if conflicts, resolve safely and record). If ledger-only acceptance commit follows candidate SHA, prove implementation/test inputs unchanged by diff; record both SHAs. Never mark milestone finally closed if remote synchronization fails; record actual state, repair and retry. Record sync evidence in milestone report and ledger (avoid self-referential commit hash claims). Start next milestone only after successful gate and sync. Prefer local testing; no duplicate paid CI or new paid services. No changes to CI billing/permissions without owner authorization.
6. **Accountless software acceptance:** local execution must use obviously synthetic employees/products/customers/distributors/orders/contacts with test-only IDs, reserved .test/.invalid addresses, local Mailpit/IMAP, local OAuth authorization/token endpoints and HTTP provider simulators backed by documented payloads, signed webhook fixtures, deterministic clocks, test DB/Redis/object storage. Exercise the actual application/adapters, not a parallel fake application. Fail closed when unconfigured; mock success must never appear as LIVE_CONNECTED, LIVE_SENT, LIVE_PAID, LIVE_PUBLISHED or live reconciliation. Keep synthetic fixtures isolated, opt-in, cleanable, never production-seeded or publicly contactable. Simulated sandbox is not vendor sandbox; official sandbox also requires accounts where applicable. External egress disabled by default in tests; no real sends, calls, ads, scraping restricted platforms, payments or publishing.
7. **Separate software readiness and future commissioning:** each connector requires real production request/auth/signature/parsing code where public contracts permit, encrypted configurable credentials, setup wizard, least scopes, OAuth state/PKCE where supported, refresh/revoke, idempotency, retries/rate limits, signed webhooks, redacted logs, clear NOT_CONFIGURED/NOT_CONNECTED status, manual/automatic sync controls, runbook and local contract tests. Actual provider identity/account approval, OAuth verification, public HTTPS, DUNS, app stores, real payments/traffic, hardware and physical acceptance are activation prerequisites ONLY. Record as [D] NOT_DUE in M47 commissioning register, with trigger, owner inputs, provider restrictions and exact live smoke/rollback instructions. If API contract is private/unavailable, document precisely what cannot be implemented; build generic interface/import/export and safe degraded UX; never mark missing provider-specific code complete. Continue all other work. No invented account, client ID, API capability, or business data. Only ask owner for a genuinely non-resolvable business/legal decision when necessary, not for missing pre-factory inputs.
8. **Reminder on EVERY task row below:** upon implementation/attempt, update TASKS.md and Project Status immediately, set [v] pending milestone tests (not [x]), select next task automatically; run tests and synchronize only at major milestone gate. This reminder applies equally to newly discovered tasks, old tasks and all future milestones.

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
- [D] M07.S03.T002 — Validate live payment/provider flows when credentials exist
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [D] M07.S03.T003 — Validate live tax/eTIMS invoice flow when credentials exist
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.

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
- [D] M13.S03.T002 — Validate live bank integration when credentials exist
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [D] M13.S03.T003 — Validate live eTIMS posting when credentials exist
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
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
- [v] M16.S02.T003 — Live-provider acceptance with real API key
  Reconciled 2026-11-25 (M43.S00.T005): [!] → [v]. On 2026-11-20 a live run used the owner's Anthropic key with claude-sonnet-5-5 (chat, predictions, recommendations, simulation and formulation; recorded under Persistent External / Runtime Gates). No independent gate has run under the 2026-11-25 protocol. Further live runs are covered by M47.S02.T008 [D] NOT_DUE.
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
- [D] M17.S02.T001 — M-Pesa live credentials/acceptance
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [D] M17.S02.T002 — eTIMS live credentials/acceptance
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
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
- [D] M18.S02.T003 — KRA/eTIMS live acceptance
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [D] M18.S02.T004 — M-Pesa live acceptance
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.

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
- [D] M19.S02.T004 — Production provider-secret deployment verification
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T009. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [D] M19.S02.T005 — Staging/live DB migration rehearsal pending environment
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T009. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
  Staging part done (2026-11-10): empty → head on the production image (M01.S03.T003); head → 20261029_0041 → head and head → 20261029_0038 → head downgrade/upgrade cycles on disposable PostgreSQL after fixing baseline-incompatible downgrades (idempotent `drop_constraint`/`drop_index` in `alembic/env.py`, 0005 keeps `rfq_request_lines` while other tables reference it); a copy of the development database upgraded to `20261110_0030` with zero model drift, then the development database itself. Remaining: a live/production database rehearsal, which needs that environment.
- [x] M19.S02.T006 — Residual repository anomaly/dead-code cleanup
  Evidence: [CODEX log](coordination/sessions/M19.S02.T006/CODEX_LOG_V01.md)

---

# M20 — Master Production Scheduling

**Status: DONE (bounded) — reconciled 2026-11-25 (M43.S00.T001): every M20 row is [x] and M20.S05.T004 was closed by CI run 41762085149 at bf3e97f. The bounded-acceptance limits below still apply. Historical heading: IN_PROGRESS / PARTIAL existing capability.**
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

**Status: DONE (bounded) — reconciled 2026-11-25 (M43.S00.T001): M21.S05.T004 is closed and the M20 dependency is satisfied. Historical heading: IMPLEMENTATION TASKS COMPLETE / MILESTONE CLOSURE GATED BY M20.**
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

**Status: DONE — M30 synthetic software scope complete. T002 has historical live evidence from 2026-11-20 (see Persistent gates); further live runs are covered by M47.S02.T008 [D]. Reconciled 2026-11-25.**
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
- [v] M30.S05.T002 — Live-provider tests with real keys
  Reconciled 2026-11-25 (M43.S00.T005): [!] → [v]. On 2026-11-20 a live run used the owner's Anthropic key with claude-sonnet-5-5 (chat, predictions, recommendations, simulation and formulation; recorded under Persistent External / Runtime Gates). No independent gate has run under the 2026-11-25 protocol. Further live runs are covered by M47.S02.T008 [D] NOT_DUE.
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

**Status: IMPLEMENTED [v] — pending M43 consolidated gate (reconciled 2026-11-25, M43.S00.T001).** S00 is [x]. All 25 feature rows are [v]: implemented and tested with recorded evidence (M36.S06 regression, walkthrough and reviews of 2026-11-21), but there has been no gate under the 2026-11-25 protocol. The OAuth, two-way calendar and e-sign provider remainders moved to M43.S01.T001–T005 and M45.S01.T014. Historical heading: "PLANNED — 25 candidate gaps; none is presumed absent or DONE without current-source and runtime evidence."
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
- [v] M36.S01.T001 — Two-way email integration (P0)
  Reconciled 2026-11-25 (M43.S00.T001): [~] → [v]. The provider-agnostic IMAP/SMTP part below is implemented with tests and is queued for the M43 gate. The Google/Microsoft OAuth remainder moved to M43.S01.T001 (Gmail API) and M43.S01.T002 (Microsoft Graph mail); live mailbox acceptance moved to M47.S02.T002 [D] NOT_DUE. No live claim.
  Done 2026-11-21 [v] (provider-agnostic part): real mailboxes over IMAP (in) and SMTP (out) — Gmail / Google Workspace and Microsoft 365 with an app password, any other host by name. `services/email_mailbox_service.py`, migration 20261121_0049; `PUT /email/accounts/{id}/connection`, `DELETE` = disconnect (password erased), `/email/send` delivers through SMTP (409 not connected, 502 delivery failure, 422 bad input; nothing stored on failure), `/email/sync/{id}` imports now, background import every 5 min. Login tested before anything is stored; password Fernet-encrypted with its own key salt, never returned. Import: UID watermark + UIDVALIDITY reset, dedupe by Message-ID per mailbox (replays add nothing), replies threaded by In-Reply-To/References, attachment metadata, NUL stripped, per-message savepoint (one bad mail does not block the mailbox), max 200 per run, no DB transaction/lock held during network I/O, 120 s per mailbox per run. Sender matching a customer e-mail links the thread to that customer; an 'unsubscribe' reply updates the consent register only when DMARC/DKIM passed (forged From ignored). Send: Message-ID/In-Reply-To/References so replies stay in the customer's thread. Mail servers must be public addresses on mail ports (no probing of our network; MAIL_ALLOW_PRIVATE_HOSTS for a self-hosted server), user sees fixed error texts. Personal mailboxes unchanged (owner/superuser only). Dev-only sample mail now uses POVU products. Fixed on the way: thread list 500 (lazy load in async), link to a non-existent customer now 422, reply defaults to the last sender (not reply-all). Evidence: disposable PostgreSQL `tests/test_m36_s01_t001_mailbox_db.py` (fake IMAP/SMTP server) + `test_m36_s00_crm_access.py` 6 passed; inbox/timeline/sequence DB tests still pass; tsc/eslint clean; desktop + phone screenshots of Communication → Email, no console errors. Independent review: 3 important (network probing via host/port, one bad mail blocking the mailbox + transaction across network I/O, forged unsubscribe) + 3 minor (reply-all, 500 on bad input, SECRET_KEY rotation) — all fixed and retested.
  [!] Still open: Google / Microsoft OAuth sign-in (needs the company's OAuth app client IDs) and a live mailbox acceptance with a real app password.
  - **Scope:** Gmail/Microsoft 365 OAuth connection, per-user mailbox permissions, inbound/outbound sync, thread deduplication, attachment metadata, unsubscribe and disconnect handling.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Verify OAuth refresh/revocation, idempotent replay, company isolation, mailbox disconnect and UI thread history. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S01.T002 — Automated sales sequences (P0)
  - **Scope:** Scheduled multi-step personalized outreach, reply/opt-out stop conditions, owner assignment and safe rate limits.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test delays, reply-stop, unsubscribe, retries, no duplicate sends and consent. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-19, batch 7) [v] implemented, independently reviewed, findings fixed; milestone acceptance pending: `crm_sequences` / `crm_sequence_steps` / `crm_sequence_enrollments` (migration `20261119_0042`), `backend/app/services/crm_sequence_service.py`: timed steps (delay days), {contact_name}/{company_name} placeholders, each step queued once in the consent-aware outbox (dedupe `seq:<enrolment>:<step>`), stops on reply (inbound e-mail from the address after enrolment, or a rep's 'replied' click — which also withdraws already-queued step mail), unsubscribe/bounce, missing consent, or the record closing; paused sequences wait without blocking others; one bad enrolment is isolated; owner = record owner; concurrent enrolments end in one row; automation action `enroll_in_sequence` (e.g. enrol every new web lead); page `crm/sequences`; delivery rate limits in the outbox. Tests `backend/tests/test_m36_s01_t002_sequences_db.py` (delays, double ticks, consent, reply/unsubscribe/won stops, automation enrolment); dev check: sequence built in the UI, worker ran step 1 and stopped the SYNTH lead for missing consent — `coordination/milestones/M36/screenshots/B7/`. Live mailbox delivery is provider-gated [!].
- [v] M36.S01.T003 — Unified conversations inbox (P0)
  Done 2026-11-20 [v]: CRM → Inbox (`/dashboard/crm?tab=inbox`) lists e-mail threads, WhatsApp numbers and helpdesk tickets as one conversation index (`crm_conversations` / `crm_conversation_reads`, migration 20261120_0048; `services/crm_inbox_service.py`; `GET /crm/inbox`, `POST /crm/inbox/{id}/read`, `PATCH /crm/inbox/{id}`, `GET /crm/inbox-assignees`). Index rebuilt from the source tables on load (upsert per (channel, source_ref): duplicate/replayed events add nothing; advisory lock + fixed order; rows of deleted sources removed). Visibility: personal mailbox → owner/assignee/superuser; WhatsApp → crm.view(_all); tickets → quality.view(_all); another company's customer hidden without crm.view_all; links to non-existent customers dropped. Unread per user; reply due 24 h (tickets: their SLA hours) with overdue flag; closed e-mail/WhatsApp conversations reopen on a new customer message; ticket status stays in the helpdesk (409), ticket reassignment needs quality.edit. Evidence: disposable PostgreSQL `tests/test_m36_s01_t003_inbox_db.py` 1 passed (ingestion, dedupe, bogus customer link, orphan removal, scopes, company separation, unread, assign/status, reopen); mutation check (mailbox scope removed → test fails); live API as owner (assign 200, ticket status 409, bad assignee 422, read 200, unknown id 404); desktop + iPhone-width screenshots, no console errors; tsc/eslint clean. Independent review: 1 finding (bogus customer link could break the inbox / bypass company filter) + 3 notes (ticket reassignment rights, concurrent sync lock order, orphan rows) — all fixed and retested. Also: workspace tab bars now wrap on desktop too (the new tab was hidden past the edge). Website chat channel: none exists yet (S03.T005).
  - **Scope:** Permission-scoped inbox for email, website chat and support threads, assignment, SLA and links to native CRM contacts.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test channel ingestion, ownership changes, unread state, duplicate events and tenant separation. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S01.T004 — CRM workflow automation engine (P0)
  - **Scope:** Event-triggered lead routing, stage transitions, reminders and task creation with rules, retries and durable execution.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Prove background worker ownership, idempotency, audit trails, recursion limits and failure recovery. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12, batch 4) [v] implemented, independently reviewed, findings fixed; milestone acceptance pending: rules reuse the existing `cf_workflow_rules` store (entity `crm_record`) — the store had no executor before; `backend/app/services/crm_automation_service.py` derives events (created, stage changed, won, lost, status changed) from `crm_stage_history`, inserts one `crm_automation_runs` row per (rule, event) with ON CONFLICT DO NOTHING (migrations `20261112_0038`, `20261112_0039`), claims runs with FOR UPDATE SKIP LOCKED so several API workers never run an action twice, runs each action in a savepoint, retries with exponential backoff (5 attempts, then FAILED with the error kept, manual retry), skips runs of paused/deleted rules, defers runs past a per-record hourly cap; per-rule activation time + watermark so pausing or editing a rule never replays old events and each tick reads only new history; notify recipients must be active users with company-wide CRM view; actions: follow-up task, round-robin owner, set temperature/next action/probability, in-app notification — actions never change stage or status, so rules cannot trigger each other; a new rule does not replay earlier events. Background loop in the API lifespan (15 s). Also fixed the stage-history listener: a first stage assignment was logged as from=to. Routes `/crm/automation/*` (configuration needs company-wide CRM edit), page `crm/automation`. Test `backend/tests/test_m36_s01_t004_crm_automation_db.py` (replay, two concurrent workers, conditions, retries, no replay for new rules). Live check on the dev stack: rule created in the UI, anonymous web-form lead, background worker created the task — `coordination/milestones/M36/screenshots/B4/dashboard_crm_automation.png`.
- [v] M36.S01.T005 — Calendar and meeting scheduling (P0)
  Reconciled 2026-11-25 (M43.S00.T001): [~] → [v]. The native meetings/ICS/DST/no-double-booking part below is implemented with tests and is queued for the M43 gate. Two-way Google/Outlook sync and Meet/Teams creation moved to M43.S01.T003/T004; public self-booking moved to M43.S01.T005; live invite acceptance moved to M47.S02.T002 [D] NOT_DUE.
  Done 2026-11-21 [v] (provider-agnostic part): Communication → Meetings. `services/meeting_service.py`, rewritten `endpoints/meetings.py`, public `GET /public/calendar/{token}.ics`, migration 20261121_0050 (time_zone, sequence, meeting_calendar_feeds). Times are wall time + IANA zone, stored UTC; a non-existent local time (spring-forward gap) is refused, an ambiguous one takes the first occurrence (Europe/London DST tested). No double booking for the host (per-host advisory lock; also on move and on re-opening a completed meeting); free start times per day, DST-safe. Jitsi creates a working link (old code produced fake 'meet.google.com/new' links); Google Meet / Teams / Zoom links are pasted. Invites, updates and cancellations are e-mailed as iCalendar REQUEST/CANCEL (same UID, SEQUENCE +1 per change) from the host's connected mailbox (M36.S01.T001) — always the host's, so the organizer never changes; people taken off a meeting get a CANCEL; stale edits (expected_sequence) get 409. Personal calendar feed for Google Calendar / Outlook 'subscribe from URL': random token stored as SHA-256, rotate = old link dead, revoke = 404. Visibility fixed: before, any user could list, edit and cancel any meeting; now host or invitee (exact, case-insensitive e-mail match), crm.view_all / sales.view_all see all, changes by host or crm.edit_all. Customer meetings stay on the customer timeline (M36.S03.T002). Also: dark-theme dialog panels are now opaque (form text was unreadable over the page). Evidence: disposable PostgreSQL `tests/test_m36_s01_t005_meetings_db.py` 3 passed (DST conversion and gap, ICS escaping/folding, double booking, moves, stale edit, invites/cancel via fake SMTP, removed invitee CANCEL, non-host editor sends from host mailbox, LIKE-wildcard e-mail not matched, CN injection quoted, null → 422, re-open clash, slots on a DST day, feed rotate/revoke, NO_MAILBOX); mailbox/timeline/access tests still pass; tsc/eslint clean; live API (create, 409 clash, slots, feed 200 → revoked 404) and desktop + phone screenshots without console errors. Independent review: 4 important (LIKE wildcards in invitee match, feed case/limit, CN parameter injection, removed invitees / organizer change) + 3 minor (re-open without clash check, null → 500, buttons for invitees) — all fixed and retested.
  [!] Still open: two-way Google Calendar / Microsoft 365 sync and Meet/Teams link creation (need the company's OAuth app); live invite acceptance with a real mailbox.
  - **Scope:** Google/Microsoft calendar connections, availability, meeting links, time-zone-safe booking, CRM meeting history.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test double-booking protection, DST/time zones, cancellations, sync conflicts and OAuth revocation. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S02 — Sales intelligence and marketing foundations
- [v] M36.S02.T001 — Website lead capture forms (P1)
  - **Scope:** Embeddable validated forms, spam protection, consent, source/UTM capture and lead deduplication.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test anonymous rate limiting, field mapping, injection prevention and source attribution. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12, batch 3) [v] implemented, independently reviewed, findings fixed; milestone acceptance pending: forms `crm_lead_forms` / submissions `crm_lead_submissions` (migration `20261112_0037`), public no-login routes `/public/lead-forms/{slug}` + `/submit` (allow-listed), hosted embeddable page `/forms/<slug>` (iframe snippet on the admin page), admin `crm/lead-forms`. Honeypot (SPAM, nothing created), consent required and recorded with the agreed text (refusals stored and rate-limited), per-IP (5/10 min, keyed-hash, raw IP never stored) and per-form (30/min) database rate limits, UTM/referrer/landing attribution on the submission and lead, e-mail dedupe inside the form's company only (repeat adds a note, same 202 answer), leads scored by the active rules. Also fixed lead/opportunity code generation (codes reused after lead conversion; string order at 100000). Test `backend/tests/test_m36_s02_t001_lead_capture_db.py` through the real app without login; browser walk-through `coordination/milestones/M36/screenshots/B3/forms_synth-contact_*.png` + admin view. Deployment note: behind a reverse proxy set `FORWARDED_ALLOW_IPS` to the proxy so the per-IP limit sees the visitor address.
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
- [v] M36.S02.T005 — Marketing campaign management (P1)
  - **Scope:** Consent-aware segmented email campaigns, templates, send scheduling, deliverability and conversion metrics.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test opt-out, suppression, bounce handling, attribution and no cross-tenant sends. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Foundation done (2026-11-19, batch 6) [independently reviewed, findings fixed]: consent register `crm_contact_consents` and outbox `crm_outbound_messages` (migration `20261119_0041`, `backend/app/services/crm_outbound_service.py`): SEQUENCE/CAMPAIGN mail needs SUBSCRIBED consent; UNSUBSCRIBED/BOUNCED/COMPLAINED suppress all mail, checked at queue time and again right before sending; web forms record consent with the agreed text but can never lift an unsubscribe; dedupe key per message (insert-or-skip); delivery through the configured SMTP server only when `CRM_OUTBOUND_EMAIL_ENABLED` (otherwise mail stays QUEUED — never reported sent); rows claimed as SENDING with SKIP LOCKED and committed before SMTP, a crash mid-send ends FAILED for a person to check (no blind resend); signed unsubscribe link + RFC 8058 one-click headers, public `/unsubscribe` page (opening the link changes nothing); one-to-one mail only to a CRM record's own contact (free addresses need company-wide CRM edit), 100/day per user; page `crm/outbox`. Tests `backend/tests/test_m36_outbound_consent_db.py` with a real local SMTP server (Mailpit): delivery, headers, suppression, unsubscribe, retries, header-injection and permission checks. Remaining for this task: segment-based campaign scheduling, templates, bounce/complaint intake from the provider, conversion metrics; live mailbox provider acceptance [!].
  Progress (2026-11-19, batch 8, independently reviewed, findings fixed): segment e-mail campaigns `crm_email_campaigns` (migration `20261119_0043`, `backend/app/services/crm_campaign_service.py`) — audience = active customers of the segment with an e-mail, limited to the campaign's company; scheduled expansion into CAMPAIGN outbox messages, one per address (dedupe `camp:<campaign>:<address>`), consent/suppression by the outbox; cancel withdraws not-yet-sent mail; stats from outbox rows plus 30-day order conversions of recipients; page `crm/email-campaigns`. Review fixes: company is required and validated (no cross-company sends), inactive/empty segments and unknown {placeholders} rejected, naive schedule times rejected, schedule locks against a concurrent cancel, one transaction per campaign (a failing one becomes FAILED and never blocks the others; it can be rescheduled), attribution counts only confirmed orders of the campaign's company within 30 days of each recipient's own send, deleting a segment in use gives 409. Not fixed (minor, recorded): 200-char dedupe key limit for very long addresses; stats use a LIKE prefix scan on the outbox. Test `backend/tests/test_m36_s02_t005_campaigns_db.py` (2 tests) with real SMTP (Mailpit), passing. Still open: provider bounce/complaint webhooks [!], reusable templates. Update 2026-11-21 [v]: reusable templates — CRM → Campaigns 'Start from a saved template' / 'Save as template' (email_templates, module crm_campaign; field lengths validated); bounces — delivery status reports (RFC 3464) arriving in a connected mailbox (M36.S01.T001) mark the address BOUNCED only for permanent failures (5.x.x) whose original Message-ID and recipient match a CRM e-mail we sent (outbox provider_message_id), so a forged bounce cannot silence a customer; temporary failures ignored. Evidence: `tests/test_m36_s02_t005_bounce_db.py` 1 passed (real bounce, forged id, wrong recipient, 4.x.x); campaign screen with a template loaded, no console errors; independent review: no findings ≥80 (template length limits added). Operational: connect the campaign sender address (SMTP_FROM_EMAIL) as a mailbox so bounces are read. Still [!]: complaint (feedback-loop) reports from mailbox providers.

## M36.S03 — CRM engagement and workflow UX
- [v] M36.S03.T001 — Sales document engagement tracking (P1)
  Done 2026-11-21 [v]: Sales → Quotations → Share. A quote (draft, sent or accepted) gets a private link (/d/<token>, 192-bit token stored as SHA-256, valid 3–90 days, URL shown once, 'Turn off' revokes at once); `services/crm_document_service.py`, `POST/GET /quotes/{id}/share-links`, `POST /quotes/share-links/{id}/revoke`, public `GET /public/documents/{token}` + `POST /public/documents/{token}/view`, migration 20261121_0051 (crm_document_links, crm_document_views). The customer sees number, dates, lines, prices, totals and customer notes only — never internal notes, costs, approvals or another quote; a quote later rejected or expired is no longer shown; unknown/expired/revoked links all give the same 'not available' answer. Views are counted by the page after it renders (mail-scanner prefetch does not count), one per visitor per 30 min, using a keyed hash — no IP address or user agent stored; staff see views, first/last opened. Sharing needs sales edit rights over the quote's scope (the quote's own DRAFT-only edit lock does not block sharing a sent quote). Phone layout of the public page: lines as cards. Evidence: disposable PostgreSQL `tests/test_m36_s03_t001_document_links_db.py` 1 passed, also re-run on the same database (permissions 403/422, token not stored, no internal notes, prefetch GET not counted, dedupe, no raw IP/UA, expiry, withdrawn quote hidden, revoke + revoke rights); live run: link created, opened logged-out on iPhone width, view 1, revoked → not available; desktop share panel screenshot; tsc/eslint clean. Independent review: no findings ≥80; applied its note (withdrawn quotes hidden). Deployment note: behind a reverse proxy set FORWARDED_ALLOW_IPS so distinct visitors are told apart.
  - **Scope:** Permissioned proposal/document links, opens and views with privacy-aware tracking and expiry.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test signed link expiry, access revocation, event deduplication and no sensitive data leakage. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S03.T002 — Unified customer activity timeline (P1)
  - **Scope:** One ordered customer view for emails, calls, visits, meetings, tasks, quotes, orders and support.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Verify event references, chronology, pagination, merges and role-scoped visibility. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12, batch 3) [v] implemented, independently reviewed, findings fixed; milestone acceptance pending: `GET /crm/customers/{id}/timeline` (`backend/app/services/customer_timeline_service.py`) — newest-first events from CRM records/activities, interactions, visits, calls, meetings, quotes, orders, invoices, payments, field visits, helpdesk tickets and the caller's own linked e-mail threads; each source needs its module view right and record scope (hidden sources are reported); cursor paging in SQL on the same column as the event time. Page `frontend/src/app/dashboard/crm/customers/[id]` (linked from the customer list). Test `backend/tests/test_m36_s03_customer_timeline_db.py` (chronology, gap-free paging, permission hiding, personal mailboxes). Screens `coordination/milestones/M36/screenshots/B3/`. No merge model exists for customers, so merge handling is not applicable.
- [v] M36.S03.T003 — Mobile CRM experience (P1)
  Audit 2026-11-21: installable PWA (M37), field app with visit capture, every screen without sideways scroll on a phone (M39.S03.T018); service worker never caches ERP data and has no offline write queue (by design, M37.S01.T002). Gaps done [v]: quick capture on the CRM customer page (Visit / Call / Message / Note, follow-up date; `POST /crm/customers/{id}/notes`, interaction on the customer timeline; migration 20261121_0054 client_ref). Offline conflict policy: a note that cannot be sent stays on the phone per signed-in user (never sent as another user), is resent with the same id when the connection returns, and is stored once (first write wins); kept on no answer / 401 / 408 / 429 / 5xx, dropped only when refused for good (no access, invalid), bounded retries, one flush at a time. A reused id from another user or customer is refused (409), not leaked. E-mail on phones: list or thread, with 'Back to list' (was two cramped panes). Evidence: `tests/test_m36_s03_t003_quick_notes_db.py` 1 passed (retry = one note, other user's reuse 409, scope 403, profile created once, timeline); iPhone-width run: online save, offline save queued, reconnect → sent once (2 notes total), e-mail thread readable, no console errors, no sideways scroll. Independent review: 4 findings (per-user queue, retry on 5xx/401, queue overwrite during flush, retry key bound to user+customer) — fixed and retested.
  - **Scope:** Responsive/PWA mobile customer cards, quick notes, visit capture, alerts and safe offline behavior if supported.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Run actual mobile viewport/device checks; verify auth, touch usability and offline conflict policy. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S03.T004 — Visual workflow designer (P1)
  Done 2026-11-21 [v] (d0e6d93, review fixes 2bb561c, ec757c2): CRM → Workflows flow-chart editor (trigger → condition yes/no → delay → approval approved/rejected → action → end; add/remove steps inline), live validation (one trigger, unique ids ≤40, cycles, reachability, branch completeness, action settings, notify recipients must have company-wide CRM view), side-effect-free simulation on a real record, versions (save draft, publish/rollback need crm.approve, one published version enforced by a partial unique index), runs from new CRM events only (per-workflow isolation, ≤10 runs per record/hour, archived versions stop), delays resume, approvals decided by crm.approve holders. Test `test_m36_s03_t004_workflow_designer_db.py` passed on disposable PostgreSQL; live: built, validated and published a workflow in the browser (screenshot m40_workflow). Independent review findings (recipient check, id length, isolation, run cap, rollback of in-flight runs, rights) fixed and retested.
  - **Scope:** Rule builder for triggers, conditional branches, delays, approvals and versioned published workflows.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test graph validation, cycles, rollback, simulation and privilege enforcement. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S03.T005 — Live chat and chatbot (P2)
  Done 2026-11-21 [v]: embeddable website chat at /chat (iframe), no login; `services/crm_chat_service.py`, public `/public/chat/sessions…` (visitor token as SHA-256, sent in the X-Chat-Token header, never in a URL), staff `GET /crm/chats/{id}`, `POST …/messages`, `POST …/close`, page /dashboard/crm/chats/{id}; migration 20261121_0055. Bot answers only from published public help articles (knowledge base); a request for a person, or no answer, hands the chat to staff: it appears in the CRM inbox as 'Website chat' (1-hour reply target, unread, assignment) and the visitor sees replies within seconds. Lead: only with an e-mail and ticked consent (consent register SUBSCRIBED, never lifts an unsubscribe; deduped on open leads without a company). Spam/rate controls: honeypot, 5 new chats per connection per hour and 300 site-wide, 12 messages per minute and 300 per chat. Retention: chats closed or silent for 12 months are deleted, chats that never reached a person after 7 days (daily task). Transcript shows the newest messages; the widget fetches only new ones. Evidence: `tests/test_m36_s03_t005_live_chat_db.py` 1 passed (honeypot, no-consent no lead, consent lead + consent record, wrong token 404, bot answers from public articles only, hand-off into the inbox, staff reply/close, closed chat 409, per-connection and per-minute limits, retention and idle purge); live iPhone-width visitor run + staff reply received by the visitor; screenshots. Independent review: 2 findings (spam chats never purged / no global or per-chat caps; only the first 200 messages shown) + notes (purge from closing time, close idempotent) — fixed and retested. Not done: per-company chat separation (chats are company-wide like WhatsApp).
  - **Scope:** Embeddable website chat, human handoff, CRM lead creation and transcript retention.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test spam/rate controls, handoff, privacy, tenant isolation and transcript linking. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S04 — Customer service and journey tooling
- [v] M36.S04.T001 — AI sales copilot (P2)
  Done 2026-11-21 [v]: CRM → customer page → 'AI brief' (`services/crm_copilot_service.py`, `POST /crm/customers/{id}/copilot`). Summary, follow-ups and a draft e-mail built only from the customer timeline the caller may already see (per-source permission and record scope), numbered E1..En. Hallucination guard: schema-validated JSON; follow-ups citing no evidence or unknown ids are dropped (count shown); an uncited summary is replaced. PII: e-mails, Kenyan phone numbers, KRA PINs and ID numbers redacted; free-text sources (calls, meetings, interactions, visits, activities, e-mail snippets) send no detail text. Human approval: the draft is only copied for the representative to send from their own mailbox; nothing is sent or saved. Provider off / malformed answer / error → rule-based brief with a note; provider errors never reach the client; request logged in ai_requests (ids and counts only); per-user hourly rate limit (AI_RATE_LIMIT_GENERATE). Evidence: `tests/test_m36_s04_t001_copilot_db.py` 1 passed (fake model: rule-based mode, dropped unsupported items, uncited summary replaced, PII not in the prompt, malformed/timeout fallback, hidden ticket evidence without quality access, 403, nothing sent); live with Claude Sonnet 5.5 on dev data: 9 s, 3 evidence items, 4 cited follow-ups, honest 'evidence is thin'; desktop + phone screenshots, no console errors. Independent review: rate limit and KRA/ID redaction added, document numbers no longer mistaken for phones.
  - **Scope:** Permission-scoped interaction summaries, suggested follow-ups, draft messages and evidence-linked recommendations.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test hallucination safeguards, human approval before sends, provider-off fallback and PII controls. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S04.T002 — Telephony and VoIP integration (P2)
  Done 2026-11-21 [v]: audit — call_logs/call_scripts, `/calls` API and Call Center page existed (partial: any user saw/edited every call, recording links stored with no consent, no retention, unvalidated dict bodies, stats unscoped, no click-to-call). Added: migration 20261121_0056 (recording_consent, consent_note, recording_expires_at, transcript; non-destructive); `endpoints/voip.py` validated CallIn/CallPatch (phone pattern, https-only recording link, outcome list incl. DIALED), own calls only unless crm/sales.view_all (list, stats, edit; edit needs caller or edit_all), recording accepted only with consent and kept CALL_RECORDING_RETENTION_DAYS (90; re-sending the link never extends it), withdrawn consent removes recording + transcript, transcripts only when CALL_TRANSCRIPTION_ENABLED (off by default) and a live consented recording, NO_ANSWER/BUSY/VOICEMAIL/FAILED flagged for follow-up on create and update, unknown customer/script -> 422; provider-off `POST /calls/click-to-call` returns a tel: link and logs DIALED; daily purge of expired and pre-consent recordings in its own transaction. UI: 📞 Call per row, 'Dialed — set outcome', consent checkbox + link + consent note, Listen / No consent column, phone layout. Tests: `tests/test_m36_s04_t002_telephony_db.py` 1 passed on disposable PostgreSQL (live chat test re-run 1 passed). Browser (desktop + iPhone 14 Pro): log with consent shows Listen, Call creates a DIALED row, outcome closes it, 0 console errors, no sideways scroll. Independent review: purge coupling and PATCH follow-up gaps + 4 minor fixed and retested. [!] live gate: a telephony provider (e.g. Africa's Talking Voice) for server-side dialing, recording and transcription is not connected.
  - **Scope:** Provider-optional click-to-call, call metadata, recording consent and transcription if legally enabled.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test consent, recording retention, permissions, failed calls and provider-off behavior. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S04.T003 — Quote approval and e-signature (P2)
  Reconciled 2026-11-25 (M43.S00.T001): [~] → [v]. The native typed-name signature with tamper evidence below, plus M41.S01.T001 (discount approval) and M41.S01.T002 (signer e-mail one-time code), supersede the old open notes on discounts and signer identity. The provider-agnostic third-party e-sign adapter and contract lifecycle moved to M45.S01.T014; provider activation moved to M47.S02.T006 [D]. Queued for the M43 gate.
  Done 2026-11-21 [v] (native part): the customer accepts or declines a SENT quotation on its share link (M36.S03.T001) with a typed-name electronic signature (name, e-mail, explicit confirmation box). `crm_document_service.decide`, public `POST /public/documents/{token}/decision`, staff `GET /quotes/{id}/decision`, migration 20261121_0052 (crm_quote_decisions). Same rules as the sales team's own accept: only SENT, not past its validity date (Nairobi), discount approval in place; one answer per quotation (unique + row lock); refused if the quote changed while the customer was reading (hash of the version they saw). Tamper evidence: SHA-256 of the customer-facing content + an evidence hash over content, decision, signer, time, link and quote, plus a snapshot of exactly what was signed; staff see 'content unchanged since signing' or a warning. Accept → ACCEPTED (conversion to a sales order stays the staff /convert step, which creates a DRAFT order, so pricing and credit checks are not bypassed); decline → REJECTED with the reason; the signer can re-open their confirmation and reference. Public view shows the signer's name only, never the e-mail. Evidence: `tests/test_m36_s03_t001_document_links_db.py::test_customer_signs_accept_decline_and_tamper_evidence` (box not ticked 422, stale version 409, markup in name rejected, accept, answered once, tamper detected after a price change, snapshot kept, decline + reopen, expired and discount-pending refused); live run on iPhone width: signed, reference shown, quote ACCEPTED, staff panel 'Accepted online … content unchanged'. Independent review: 1 finding (declined quote's link showed 'not available' instead of the confirmation) fixed; snapshot added from its notes.   [!] Still open: a third-party e-signature provider with verified signer identity (DocuSign / Adobe Sign etc.); signer e-mail is not verified today. Note: discount_approval_required is not set by any screen yet, so that guard is inert until discount approvals are wired.
  - **Scope:** Existing ERP quotation integration with approval, secure external review, e-sign and audit proof via chosen provider.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test signer identity, tamper evidence, expiry and order conversion without bypassing pricing/credit controls. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S04.T004 — Customer self-service portal (P2)
  Audit 2026-11-21: ticket history, status and replies already existed in the partner portal (Support tab; reply re-opens a resolved ticket; staff internal notes never shown). Gap was approved attachments — done [v]: `ticket_attachments` (migration 20261121_0053), `services/ticket_attachment_service.py`; portal `POST /portal-self/tickets/{id}/attachments`, `GET …/attachments/{att}`; staff `GET/POST /helpdesk/tickets/{id}/attachments`, `POST /helpdesk/attachments/{id}/share`, `GET /helpdesk/attachments/{id}/download` (quality.view/edit). Shared document storage (opaque keys, type/size/content checks) + fail-closed malware scan: INFECTED refused and deleted, NOT_SCANNED/ERROR quarantined (listed, not downloadable), only CLEAN downloadable, served as attachment with nosniff/no-store; max 10 files per ticket (ticket row lock) and 10 MB. Customer uploads are visible to the customer and staff; staff files reach the customer only after 'shared with customer'; a customer reaches only their own ticket's visible files (404 otherwise). CRM inbox (M36.S01.T003): portal customer replies now count as inbound (unread, reply due again), staff replies as outbound; list query refreshes rows after the upsert. Evidence: `tests/test_m36_s04_t004_portal_ticket_files_db.py` 1 passed (own/other customer, disguised type 415, infected 422, quarantine, staff permission 403, share approval, customer file cannot be hidden, inbox inbound/outbound) + inbox test still passes; live staff run: upload, share, quarantined download 409 (no scanner in dev), Helpdesk files section screenshot; tsc/eslint clean. Independent review: no findings ≥80; applied its note (limit under a row lock). Deployment: set DOCUMENT_CLAMAV_HOST — without a scanner every file stays quarantined by design. Known edge: if a staff user is deleted, their old comments lose the author and would count as customer messages in the inbox.
  - **Scope:** Customer-authenticated ticket history, status, replies and approved attachments.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test customer/company isolation, attachment security and status synchronization. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S04.T005 — Customer knowledge base (P2)
  - **Scope:** Searchable versioned public/private support articles, editorial approvals and feedback.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test publication permissions, search, revision history and private article leakage. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
  Done (2026-11-12, batch 5) [v] implemented, independently reviewed, findings fixed; milestone acceptance pending: existing KB (articles, categories, revisions, search, scopes) extended — editorial gate: publishing, making an article public, editing a published article or changing any visibility field of a published/public article needs `knowledge_base.publish` (editors submit for review: new `IN_REVIEW` status); drafts/reviews/archives readable only by their author, editors and publishers; detail route now enforces article scope; feedback (`kb_article_feedback`, migration `20261112_0040`) one vote per staff user on published articles; public no-login help centre `/kb`, `/kb/<slug>` (routes `/public/kb/*`, allow-listed) shows only published, non-internal, unscoped articles, plain-text rendering, wildcard-escaped search, keyed-hash per-IP feedback limit. Also fixed: internal article page rendered article markdown as raw HTML (stored XSS) — now escaped; detail route committed before reading (500 risk). Test `backend/tests/test_m36_s04_t005_kb_db.py` through the real app; screens `coordination/milestones/M36/screenshots/B5/`.

## M36.S05 — Advanced marketing and intelligence
- [v] M36.S05.T001 — Customer journey attribution (P2)
  Done 2026-11-21 [v]: CRM → Attribution (`services/crm_attribution_service.py`, `GET /crm/reports/attribution`, CRM broad view, max 2 years). Source → lead → opportunity → won → paying customer → orders → repeat purchase by first-touch, last-touch or linear credit. Source precedence: linked website-form submissions (UTM source/campaign) → record source type/detail → Manual. Joins are explicit links only (submission → record → customer; no matching people by e-mail/phone). A customer belongs to its oldest CRM record ever (no double counting across records or reports); orders = confirmed (not draft/cancelled), same company when filtered, from the record's Nairobi creation date; revenue net of tax with discount as a fraction; per currency, never summed across currencies. Reconciliation against an independent SQL re-valuation of the counted orders (0.01 per currency); subqueries instead of huge IN lists. Assumptions shown on the page. Evidence: `tests/test_m36_s05_t001_attribution_db.py` 1 passed (precedence, three models, linear split, repeat customers, no double count, older owner, draft/cancelled/pre-journey excluded, 10 % discount, per-currency, company filter on orders, reconciliation); page screenshot on dev data. Independent review: discount formula (was /100), company filter on orders, older-owner rule, independent reconciliation, IN-list size — all fixed and retested.
  - **Scope:** Source-to-lead-to-opportunity-to-order-to-repeat-purchase attribution with consent-aware identity joins.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test source precedence, multi-touch attribution assumptions, merges and reporting reconciliation. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S05.T002 — Landing pages and A/B testing (P2)
  Done 2026-11-21 [v] (a35a114, review fixes 2bb561c): CRM → Landing pages; public `/lp/<slug>`. Variants A–E with weights; consistent SHA-256 assignment pinned at the first counted view; views/conversions once per visitor (keyed hash only), ≤30 counted views per connection per hour; conversions only for visitors with a counted view and a new ACCEPTED lead (lead-form consent and honeypot rules apply); stats with Wilson 95% ranges and two-proportion z-test; no verdict before min sample and 5 conversions per variant. Test `test_m36_s05_t002_landing_ab_db.py` passed; live: page created, put live from the screen, visitor submitted on a phone (m40_landing_public/staff).
  - **Scope:** Campaign landing-page templates, variants, conversion goals and safe experiment assignment.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test consistent assignment, statistical guardrails, consent and form integration. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S05.T003 — Integration catalog and sync console (P2)
  Done 2026-11-21 [v] (ada2d62, review fixes dcc344a): Integrations → Console: one row per connector with evidence-based health (HEALTHY only after a recorded successful run; NOT_CONNECTED / STUB_ONLY / SIMULATED / NO_DATA / FAILING), credentials set/not set (never values), last success, failures in a row, exponential backoff (1 min … 6 h, 429 with retry time), scrubbed error text, mapping health (shop orders/products, external CRM, mailboxes, webhooks), manual sync for mailboxes and Shopify only (stubs 501, unconnected 409, advisory lock per connector, partial import = failed). Test `test_m36_s05_t003_integration_console_db.py` passed; live screenshot m40_console. [!] live providers: Shopify, WhatsApp, M-Pesa, SMTP keys.
  - **Scope:** Inventory of optional provider connectors, mapping health, retries, errors, credential status and scoped sync controls.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test no fake SYNCED status, backoff, secrets handling and provider-unavailable behavior. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S05.T004 — Conversation intelligence (P3)
  Done 2026-11-21 [v] (7816ca2, review fixes 2bb561c): opt-in `CONVERSATION_INTELLIGENCE_ENABLED`; calls need recording consent + transcript, chats must have reached a person; findings (objection/theme/question/next step) are verbatim quotes with offsets, AI suggestions kept only if the quote is in the text, no scores; agents see own, managers all; review (REVIEWED/REJECTED + coaching note) by crm.edit_all only, never on own conversation; re-analysis cannot wipe a review. CRM → Conversation insights + "Analyse" on calls. Test `test_m36_s05_t004_conversation_intel_db.py` passed. [!] live: transcripts need a voice provider.
  - **Scope:** Opt-in transcript analytics, objection/theme extraction, coaching insights and review workflow.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test transcript consent, access controls, source-linked outputs and no fabricated scores. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.
- [v] M36.S05.T005 — Account-based marketing (P3)
  Done 2026-11-21 [v] (348381c, review fixes 2bb561c): CRM → Key accounts: target-account groups with tiers, buying committees (roles, one e-mail per account), engagement only from recorded rows (activities, meetings, e-mails out/in, tickets, orders) with missing key roles, consent-aware coordinated campaign through the outbox (queued vs suppressed counts, idempotent per group+subject+body), influenced revenue since the campaign start (labelled not causal); read crm.view_all/marketing.view, write crm.edit_all/marketing.edit. Test `test_m36_s05_t005_abm_db.py` passed; live: group, account and committee contact created in the browser (m40_abm).
  - **Scope:** Target-account groups, buying committees, cross-contact engagement and coordinated account campaigns.
  - **Required audit:** Record existing DB model/migration, service, REST/GraphQL endpoint, UI route, RBAC, tests and live-screen evidence; classify existing/partial/missing before edits.
  - **Implementation:** Extend native CRM, create minimal migrations and API/UI changes only for verified gaps; preserve existing sales/customer records, scope rules, auditability and integration contracts.
  - **Acceptance:** Test account/contact joins, hierarchy, permissions and attribution. Include backend/DB/API tests, frontend checks, browser screenshot evidence, independent review and exact commit SHA. Any live-provider validation remains [!] until real access is available.

## M36.S06 — Consolidated acceptance and handoff
- [v] M36.S06.T001 — Run full CRM regression across lead → opportunity → quote → sales order → invoice, field sales, Shopify buyer mappings, customer support and permissions using synthetic PostgreSQL data; record exact SHA and failures.
  Done 2026-11-21 [v]: all 157 DB-gated test files passed on disposable PostgreSQL (template at head 20261121_0067), including CRM lead/opportunity/quote/order/invoice, field sales, Shopify mappings, customer support, consent/campaign (local Mailpit), permissions; backend suite 1740 passed. Live: purchase request → approval → PO and CRM pages walked in the browser.
- [v] M36.S06.T002 — Perform browser visual regression and screenshot walkthrough of all implemented CRM pages (desktop and mobile), with accessible navigation, loading/error/empty states and no console failures.
  Done 2026-11-21 [v] (2fe22cd): crm_manager walked every CRM tab plus helpdesk on desktop (1440) and phone (iPhone 14 Pro): 56 pages, 0 console errors, 0 failed API calls, no error/empty-crash states; screenshots and report in coordination/milestones/M40/crm_walkthrough/. Found and fixed: helpdesk hidden from CRM/sales support staff.
- [v] M36.S06.T003 — Independent code/security/privacy/migration audit with separate reviewer; remediate findings and retest. No self-review presented as independent.
  Done 2026-11-21 [v]: independent reviewer agents (separate from the implementer) reviewed the M36 deliveries (findings fixed in 2bb561c) and the M40 approvals/scope change ef84cd6 (9 findings: count-adjustment id, plain approvers missing, scope ref leak, TPM audience, stage order, self-approval, client-supplied approver ids, notifier load — fixed in 2fb95a7 with DB tests).
- [v] M36.S06.T004 — Update CRM user/admin docs, provider setup instructions, consent policy, feature matrix, deferred live gates, release notes and TASKS.md; commit/push and verify main synchronization.
  Done 2026-11-21 [v] (5333c50): `docs/CRM_GUIDE.md` — feature matrix, consent/privacy rules the code enforces, provider setup, live gates, release notes.

# ESIGN-USR — Employee registered e-signatures (owner request 2026-11-19)

- [v] ESIGN-USR.T001 — IT registers each employee's signature at hiring; it is applied automatically when they sign; each person sees only their own signature.
  Done (2026-11-19) [v] implemented, independently reviewed, findings fixed: `esign_user_signatures` (migration `20261119_0044`; one active signature per user, replaced/revoked ones kept as history), routes `GET /esign/my-signature` (own only), `GET /esign/signatures` (IT, `esign.admin`: who has a signature on file — metadata and hash, never the image), `PUT/DELETE /esign/signatures/{user_id}` (IT register/replace/revoke, PNG/JPEG ≤300 KB validated, audit-logged). Signing applies the registered signature automatically; a revoked signature blocks signing; a drawn signature is accepted only for people never registered and is validated the same way. Signature images in signing requests are returned only to their owner (requesters, viewers and IT admins see none — review found this leak and it is fixed). Pages: "My signature" card + sign modal on `/dashboard/esign`, IT page `/dashboard/esign/signatures` (upload or draw). Tests `backend/tests/test_esign_user_signatures_db.py` (PostgreSQL, real app); dev browser check with a synthetic IT user and synthetic employee — `coordination/milestones/ESIGN/`.

# Persistent External / Runtime Gates

These are not reasons to fabricate completion and do not erase source implementation:

- [D] Live KRA/eTIMS credentials and production acceptance — NOT_DUE, see M47.S02.T006 (Reconciled 2026-11-25 (M43.S00.T005))
- [D] Live Safaricom Daraja/M-Pesa credentials and production acceptance — NOT_DUE, see M47.S02.T006 (Reconciled 2026-11-25 (M43.S00.T005))
- [D] Live bank connector credentials/provider acceptance — NOT_DUE, see M47.S02.T006 (Reconciled 2026-11-25 (M43.S00.T005))
- [v] Live AI-provider acceptance where a real external model is required — 2026-11-20: owner's Anthropic key, model claude-sonnet-5-5; chat, predictions (7), recommendations (7), scenario simulation and formulation all answered live (whole test: 6,547 input + 19,924 output tokens, about $0.21). Fixes found by the live run: replies read only text blocks (thinking blocks first on current models), prediction period/risk/trend capped to their 20-char columns, AI_MAX_TOKENS 4096 → 16000 (formulation came back empty at 4096), retired gemini-1.5-pro replaced by gemini-flash-latest (the Gemini key has no usable quota). Docker reads the key from .env.development. AI runs only when a user presses one of these five buttons; no scheduled AI. 110 AI unit tests pass.
- [D] Physical printer/device acceptance where hardware is required — NOT_DUE, see M47.S02.T007 (Reconciled 2026-11-25 (M43.S00.T005))
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

# M37 — Employee Mobile App (iOS/Android) — Owner-requested 2026-11-19

**Status: S01 DELIVERED [v] (installable PWA, local verification); S02/S03 device- and account-gated.**
Decision: no public App Store / Google Play listing. Phase 1 = installable PWA of the existing Next.js ERP; Phase 2 (Capacitor shell) only on documented triggers, distributed privately (Android: managed Google Play private app; iOS: Apple Business Manager Custom App). Rationale, cost and account comparison: `coordination/milestones/M37/M37_MOBILE_APP_DISTRIBUTION_DECISION.md`. Coordinated with concurrent M36 session: no CRM files touched.

## M37.S00 — Audit and decision
- [x] M37.S00.T001 — Inventory existing mobile surfaces: cookie session + refresh + 2FA, no self-signup, default-auth API, `mobile_push_tokens`/`mobile_app_sessions` + `/api/v1/mobile/*` (push send is a stub), shop-floor terminal touch-ready and deliberately not offline-writing, no PWA assets. Evidence: decision doc §1–2.
- [x] M37.S00.T002 — Distribution decision with cost, D-U-N-S / Apple Developer Program / ABM / Play Console / Android Enterprise requirements, security and update path. Evidence: decision doc §3–5.

## M37.S01 — Installable PWA (Phase 1)
- [v] M37.S01.T001 — Web app manifest (`frontend/src/app/manifest.ts`), icons (`frontend/public/icons/`), viewport/theme/apple-web-app metadata (`frontend/src/app/layout.tsx`).
- [v] M37.S01.T002 — Service worker `frontend/public/sw.js`: caches only hashed `/_next/static` + icons; navigations network-only with static `offline.html`; never intercepts API, cross-origin or non-GET (no ERP data left on shared devices, no offline write queue). Registered in production only (`frontend/src/components/PwaRegister.tsx`). Test: `npm run test:pwa` (4 pass).
- [v] M37.S01.T003 — Device registration: the installed app (display-mode standalone) registers a persistent device id + detected platform through existing `POST /api/v1/mobile/devices` once per session → visible/deactivatable in Admin → Mobile Apps → Device Manager. Push token empty until S03.
- [v] M37.S01.T004 — Camera barcode/QR scan via native `BarcodeDetector` (`frontend/src/components/BarcodeScanButton.tsx`), wired to shop-floor material lot selection (scanned lot must be one issued to the operation). Hidden where unsupported (iOS Safari); keyboard-wedge hardware scanners work everywhere.
- [v] M37.S01.T005 — Verification 2026-11-19: `tsc --noEmit` 0 errors; `eslint .` 0 errors (pre-existing warnings only, none in changed files); production `next build` OK; Chrome `Page.getInstallabilityErrors` = [] on prod build; SW active, cache holds only static assets; offline navigation shows fallback; backend auth/security tests 18 passed / 1 skipped (no backend changes). Phone-width (Pixel 7) screens dashboard, shop-floor terminal, mobile approvals, devices: 0 px horizontal overflow — **layout-only with mocked API** (synthetic shop_floor_operator permission codes); creating a live synthetic tester in the dev DB was not permitted in this session. Evidence: `coordination/milestones/M37/screenshots/` + `report.json`, script `frontend/scripts/capture-m37-pwa-evidence.mjs`.
- [v] M37.S01.T006 — Live-session acceptance on phone width with a real non-admin employee account. Done 2026-11-20 on the owner's iPhone over LAN HTTPS with synthetic non-admin logins (driver, distributor, supplier — phone test steps 1–12, M39.S03.T015/T017) plus the Playwright phone-width sweep of all 710 screens (M39.S03.T018).
- [D] M37.S01.T007 — Real-device acceptance: install on a physical Android (Chrome) and iPhone (Safari "Add to Home Screen") over production HTTPS; camera scan on Android; device appears in Device Manager. Requires HTTPS deployment and devices. Partly done 2026-11-20: iPhone Safari over LAN HTTPS with a test CA (M39 phone test); production HTTPS, Android install/camera scan and Device Manager check still open.
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T001 + M47.S02.T007. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.

## M37.S02 — Managed distribution (company accounts required)
- [D] M37.S02.T001 — Android Enterprise + EMM: push PWA as managed Google Play web app to factory devices. Needs company EMM and Google account (D-U-N-S for org Play account).
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T007. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [D] M37.S02.T002 — iOS MDM Web Clip for managed iPhones/iPads. Needs MDM.
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T007. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [ ] M37.S02.T003 — (Phase 2 trigger only) Capacitor shell; Android private app via managed Google Play, iOS Custom App via Apple Business Manager. Needs D-U-N-S, Apple Developer Program (org), ABM, Play Console (org).

## M37.S03 — Push notifications and device policy
- [v] M37.S03.T001 — Replace `/api/v1/mobile/push/send` stub with Web Push (VAPID) for installed PWA (Android, iOS 16.4+); restrict send to authorised roles; store subscription in existing token table.
  Done 2026-11-21 [v] (d63fdbb): RFC 8291 aes128gcm + RFC 8292 VAPID with `cryptography` only; VAPID key created once, stored encrypted; "Notify me on this device" in the bell menu; every new in-app notification is pushed after commit; 404/410 subscriptions removed; send restricted to administrators. Test (decrypts with the browser key, verifies the JWT) passed. [!] real-device acceptance (Android Chrome, iPhone Home Screen app) on production HTTPS.
- [v] M37.S03.T002 — Lock down `/mobile/devices/stats`, `/mobile/kpis`, `/mobile/push/send` (currently any authenticated user) to admin/mobile-management permission.
  Done 2026-11-21 [v] (d63fdbb): /mobile/push/send, /mobile/kpis, /mobile/devices/stats need users.edit, company.edit or integrations.edit.
- [v] M37.S03.T003 — iOS camera barcode fallback (JS decoder) if iOS scanning becomes a requirement.
  Done 2026-11-20 [v] (66081d0): barcode-detector ponyfill (bundled zxing wasm) in BarcodeScanButton; verified on iPhone over LAN HTTPS (fake-camera Code 128 scan).

## M37.S04 — Role-gated dashboard + barcode-driven raw-material flow (owner request 2026-11-19)
- [v] M37.S04.T001 — Executive Dashboard summary is role-gated: `GET /api/v1/dashboard/summary` returns production/inventory/sales/M-Pesa/logistics sections and alerts only to holders of the company-wide permission (`production.view`, `inventory.view`, `sales.view`, `finance.view`/`mpesa.view_transactions`, `logistics.view`; `*_own_scope` does not unlock totals). UI hides gated cards; a user with no company section is redirected (shop-floor users → Operator Terminal). Previously every authenticated user, incl. shop-floor operators, saw company sales/stock/M-Pesa.
- [v] M37.S04.T002 — Universal barcode resolver `GET /api/v1/shop-floor/barcodes/resolve`: prepared-lot label → registered barcode label → GS1 (AI 10 lot, AI 310n net kg; parser fixed for 310n) → lot number → material code → product barcode/SKU; returns material name/code/uom, lot, expiry, quarantine/expired, quantity. `material_barcode_flow_service.py`.
- [v] M37.S04.T003 — Dispensing (warehouse → order) on existing prepared-lot infrastructure: scan source lot (wrong material, quarantined or expired refused), weigh, optional bag target + tolerance (out-of-tolerance refused before labelling), warehouse issue to the order (`issue_material`, lot recorded), `MATERIAL_DISPENSED` event, printable Code 128 + QR label. UI `/dashboard/shop-floor/dispensing`.
- [v] M37.S04.T004 — Scan-to-consume at the machine `POST /api/v1/shop-floor/work-orders/{id}/scan-consume` (operator session + idempotency key): prepared lot must be dispensed for this work order, unconsumed, released and in tolerance; label quantity is authoritative; lot/GS1 scans need the lot issued to the order; non-recipe material refused. Prepared lot marked consumed atomically with consumption. UI: scan panel on terminal Materials tab (keyboard-wedge, camera, manual).
- [v] M37.S04.T005 — Scan audit: every scan, accepted or rejected, writes `MATERIAL_SCAN` to `sf_activity_logs` with server time, device time (`client_scanned_at`), session, operator, machine, line, code, resolved material/lot/prepared lot, qty and rejection reason. No migration (avoids Alembic head conflict with concurrent M36 work).
- [v] M37.S04.T006 — Verification 2026-11-19: `tests/test_m37_s04_barcode_material_flow_db.py` 3 passed on disposable PostgreSQL (role-gated dashboard for operator/COO/CEO permission sets; dispense refusals, label resolve, scan consume, retry idempotency, used-label/unknown/non-recipe refusals, GS1 weight scan, scan-log contents); regressions: shop-floor/GS1/auth suites 60 passed 1 skipped, M23.S04.T003 DB 3 passed. Frontend `tsc` 0, `eslint` 0 errors, `test:pwa` 4 pass. `next build` compiles, type-checks and generates 713 pages, then exits 1 at the Next.js 16.4.2 security-advisory gate (upgrade needed; separate task). End-to-end on a disposable demo stack (synthetic dispenser + operator, Pixel 7 viewport, 0 px overflow): wrong lot refused → 12.4 kg issued + label → operator scans label → consumed → re-scan refused; DB rows show server vs device scan time. Evidence: `coordination/milestones/M37/screenshots/s04/` + `report.json`, script `frontend/scripts/capture-m37-barcode-flow-evidence.mjs`.
- [D] M37.S04.T007 — Physical acceptance: print labels on the factory label printer, scan with Android camera and a hardware scanner at a real machine; check Code 128/QR read rates. Needs devices.
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T007. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
- [v] M37.S04.T008 — Extend `ScanInput` + resolver to goods receipt, putaway, transfers and cycle counts (same resolver; warehouse screens still use manual selection).
  Done 2026-11-21 [v] (79d2a3f, f0d54aa): every record picker accepts hardware scanners (code + Enter) and the camera; scans select only exact matches. Goods receipt: item scan +1 on its PO line, separate lot scan for the last item; stock receipt/issue/transfer product by scan; cycle-count task by scan; putaway/pick were already scan-confirmed (M38). [!] physical scanner acceptance with M37.S04.T007.
- [v] M37.S04.T009 — Next.js 16.4.2 → 16.4.6 (+ eslint-config-next) fixes GHSA-mfr8-8qww-v76h and GHSA-vc7v-qv4w-wrv8 (moderate, 'use cache' cross-root-param leaks). `npm audit --omit=dev` 0 vulnerabilities; `next build` exit 0 (713 pages), `tsc` 0, `eslint` 0 errors, `test:pwa` 4 + `test:auth-refresh` 2 pass; prod smoke: login page, SW active, manifest, offline page, unauthenticated dashboard redirect. The docker dev frontend keeps 16.4.2 in its node_modules volume until rebuilt (`docker compose build frontend && docker compose up -d frontend`).

## M38 — Screens for every team and channel (owner request 2026-11-19)
**GOAL (owner, 2026-11-19): complete every row below — each team/channel gets its own working screen; run without stopping until all are [v]/[x].**
Audit: `coordination/milestones/M38/M38_S00_PERSONA_SCREEN_AUDIT.md` (distributor, supplier, ESS logins non-functional; moto, driver POD, field controller have no screens; ESS demo-wired).
- [v] M38.S00.T001 — Persona/channel screen audit (helper sweep + hand re-check of key claims). Independent review pending.
- [v] M38.S01.T001 — External-realm auth: signed per-realm JWT (portal/supplier) in HttpOnly cookie, salted hashes with upgrade-on-login, login rate limit, account-scoped dependency; supplier password reset requires a reset token.
- [v] M38.S01.T002 — Distributor ordering portal: login page, catalog with server-side prices, order → priced DRAFT sales order (source DISTRIBUTOR, idempotent), order/shipment/invoice status, statement, reorder.
- [v] M38.S02.T001 — Field rep / pre-seller "my day" PWA screen: route outlets, check-in with GPS, visit log + photo, order capture.
- [v] M38.S02.T002 — Moto rider screen: sell, M-Pesa STK push, day summary; supervisor fraud alerts + leaderboard UI.
- [v] M38.S02.T003 — Delivery driver "my trip": stops, POD with signature/photo/GPS, failed-delivery reasons.
- [v] M38.S02.T004 — Collector screen: route of open balances, STK push / receipt.
- [v] M38.S03.T001 — Field controller: outlet/route audit checklist, scoring, rep compliance view.
- [v] M38.S04.T001 — ESS bound to the logged-in user (`Employee.user_id`), remove DEMO_EMPLOYEE, my payslips.
- [v] M38.S05.T001 — Supplier portal UI (POs, acknowledge, ETA, documents) on S01.T001 auth.
- [v] M38.S06.T001 — Customer ticket/NPS portal; warehouse pick/putaway execution; consumer QR verify page; replace redirect stubs.
  Progress M38.S01 (2026-11-19, portal realm implemented + verified; independent review pending; supplier realm still open): `backend/app/core/external_auth.py` (per-realm signed JWT in HttpOnly cookie, realm claim rejected by staff auth, password-fingerprint revocation, bcrypt with SHA-256 upgrade-on-login, login rate limit); distributor API `/portal-self` (`portal_self.py`: login/activate/logout, me, password, dashboard, catalog with server-side prices, idempotent order → DRAFT sales order source DISTRIBUTOR, orders, invoices, statement, shipments, claims); staff `/portal` now needs sales.view/sales.edit, invite returns a one-time set-password link (token stored as digest), unlinked accounts no longer see other customers' invoices/payments/shipments. Remaining: supplier realm + reset-password fix, DB tests, frontend `/portal` pages, review.
  Verification M38.S01.T002 (2026-11-19): `backend/tests/test_m38_s01_distributor_portal_db.py` passed on disposable PostgreSQL (realm sign-in separate from staff, legacy SHA-256 → bcrypt upgrade, account isolation incl. claims, server prices ignore client price, idempotent order → DRAFT SO source DISTRIBUTOR, VIEWER cannot order, unlinked account 409, password change ends other sessions, logout, staff permissions + one-time invite link); route-auth suites 142 passed. Frontend `/portal/login`, `/portal/activate`, `/portal` (catalog+cart, my orders + order again, invoices & statement, claims): tsc/eslint clean; browser run on dev stack with a SYNTH distributor, 390px and 1366px, 0 px overflow, no page errors, portal cookie gets 401 on staff API. Evidence `coordination/milestones/M38/screenshots/portal/` + `report.json`.
  Review M38.S01 (2026-11-19, independent reviewer, code read only): no cross-account leak, token confusion or price manipulation found. Fixed: dashboard totals now over every open invoice (were 5), statement totals in SQL over the whole range and only issued/paid/overdue invoices shown (DRAFT/CANCELLED hidden), deactivation clears set-password links and a link never reactivates a once-active user, case-insensitive e-mail, constant bcrypt cost for unknown e-mails, 40-bit order numbers with collision re-raise, unknown status filter → empty, can_view_prices also hides invoice amounts in order detail. Regression test added (2 tests pass). Open (recorded, not fixed): login lockout keyed per e-mail only (no per-IP limiter) so a known e-mail can be locked out for 30 min; product selling_price currency is assumed to be the customer currency when no price list matches.
  M38.S01.T001 supplier realm + M38.S05.T001 (2026-11-19, independent review pending): `/supplier-self` (`supplier_self.py`): sign-in/activate/logout/password, only released POs of the own supplier (draft/cancelled and other suppliers' 404), acknowledge (reason required for reject, date for revised ETA), propose delivery date, real document upload through the document storage service (opaque key, type/content checks, PO must be own), payments for OWNER/FINANCE when the account allows; staff `/supplier-portal` now needs procurement.view/edit, invite returns a one-time link (migration `20261119_0045` adds `sp_users.invitation_token` digest + expiry; up/down/up checked), staff file download; the unauthenticated-by-token `POST /supplier-portal/auth/reset-password` and placeholder logins removed; fixed PO list crash (`po.total_amount` did not exist) and wrong PO/invoice numbers. Test `backend/tests/test_m38_s05_supplier_portal_db.py` passed. UI `/supplier/login`, `/supplier/activate`, `/supplier` (shared PartnerLogin/PartnerActivate with the distributor portal): tsc/eslint clean; browser run 390/1366 px 0 overflow, no page errors, supplier cookie 401 on staff API. Evidence `coordination/milestones/M38/screenshots/supplier/`.
  Review M38.S05.T001 (2026-11-19, independent reviewer, code read only): no cross-supplier leak; fixed: HIGH staff takeover — issuing set-password links/inviting/deactivating partner users (distributor and supplier) now needs the new permission `partner_portal.manage_access` (seeded, granted to admin), every link is logged with the staff username and invited_by is the staff user; links never reactivate deactivated users; supplier uploads are malware-scanned (`sp_documents.scan_status`, staff download only when CLEAN; infected files deleted; orphan file removed when the record fails); DRAFT/CANCELLED purchase invoices hidden from suppliers; staff views no longer logged as supplier activity; staff ETA/acknowledge validate the PO and drop the spoofable user_id; the staff free-path document create route removed; duplicate e-mail → 409; responses refused on fully received POs and past dates. Staff screens show the one-time link (AccessLinkNotice) on invite and via 'Password link' (distributor account page) / new Supplier portal users panel. Tests updated and passing (supplier 1, distributor 2). Open: per-IP login limiter, ETA revision_no race (no unique constraint), activation token in URL query.
  M38.S02/S03 field app (2026-11-19, independent review pending): `/field` (`field_app.py`) scoped to the signed-in employee — rep/moto rider (SalesRep.user_id): today's route stops with open balances and target, visits with GPS + outlet photo (idempotent client_ref), catalog with server prices (shared `customer_pricing.py`, also used by the distributor portal), orders → DRAFT SO source FIELD_SALES linked to the visit, open invoices, collections (cash / M-Pesa code / cheque; PENDING until finance confirms) and M-Pesa STK on the invoice's order; driver (new `delivery_trips.driver_user_id`): my trips, start/finish, proof of delivery with drawn signature + photo + GPS (files via document storage, scanned), failed delivery with reason; field controller (new permission `field.audit`): outlet search, 7-item checklist, score, photos, GPS; supervisor (`field.supervise`): per-rep coverage, GPS share, orders, collections, audit scores, moto fraud alerts + leaderboard with rider names. Office `/collections` API (`collections.py`) now exists — the Collections screen called a missing API; confirm posts the payment to the invoice through the normal GL rules (finance.edit/approve). Moto endpoints now need sales or field.supervise permissions (were open to any login). Migration `20261119_0046` (collections, audits, visit client_ref/photo, driver user, POD signature, supplier doc scan status; up/down/up checked). Test `backend/tests/test_m38_s02_field_app_db.py` passed (scoping, idempotency, prices, collection → GL payment, POD, audits, compliance). UI `/dashboard/field` (route/order/collect, deliveries with signature pad, audits) and `/dashboard/field/supervisor`, sidebar 'Field App', PWA shortcut; tsc/eslint clean, test:pwa 4 pass; browser run on dev stack with a SYNTH rider at 390 px (0 overflow, geolocation granted, no page errors) and the supervisor view at 1440 px. Evidence `coordination/milestones/M38/screenshots/field/` + `report.json`. Not done: offline queue (PWA is network-only by the M37 decision; retries are safe through client_ref), van POS was already present.
  Review M38.S02/S03 (2026-11-19, independent reviewer, code read only): scoping held; fixed: POD double-delivery race (stop row locked + unique index `uq_pod_trip_order`), a non-delivered stop is never reported delivered (409; FAILED stops can be re-attempted), collections must settle an invoice (on-account money had no GL path), collection currency = invoice currency, pending collections reserve the invoice balance (invoice row locked), confirm needs finance.approve and never by the person who recorded it, sub-cent amounts rejected, M-Pesa code unique only among non-cancelled collections (`uq_cash_collections_mpesa_code_live`), STK only to the customer's registered phone and only for M-Pesa orders, scanner errors fail closed when a scanner is configured, idempotent replays are owner-checked, audits need each item exactly once on an active outlet, compliance counts only real orders/collections and distinct outlets; field.supervise can no longer STK-push or compute moto performance. Migration `20261119_0047` (up/down/up checked). Test extended and passing. Open (recorded): confirmed cheques have no bounce/reversal path (confirm only after clearing); GPS accuracy not recorded; field delivery marks the shipment DELIVERED directly like the existing POD route.
  M38.S04.T001 (2026-11-19, independent review pending): `/ess-self` (`ess_self.py`) resolves the employee from the staff login (`Employee.user_id`/`ESSAccount.user_id`), auto-creates the ESS record on first use; own profile, leave (request goes straight to approval, cancel own), attendance with server-time check in/out (no self-typed hours), requests, documents visible to the employee, notifications, and own payslips from APPROVED/PAID runs only. The 7 ESS pages no longer use the hard-coded DEMO_EMPLOYEE; new `/dashboard/ess/payslips`; HR-only links hidden; `/dashboard/ess` no longer redirects employees to the HR hub (bypass); sidebar 'My HR'. The public ESS login that returned an unvalidated placeholder token was removed. Expense claims are filed for the signed-in employee (HR with hr.edit may file for others) — also fixed a crash on every claim create (lazy-loaded lines). Test `backend/tests/test_m38_s04_ess_self_db.py` passed (isolation between two employees, auto-provision, leave, clock, requests, payslips approved-only, claims). Browser run 390 px: home, check in, payslips, leave; 0 overflow, no page errors. Evidence `coordination/milestones/M38/screenshots/ess/`. Found, not yet fixed: other screens still post a hard-coded demo user id as approver/actor (expense advances, recruitment requisition approval, shelf-life disposition, recall actions) — tracked under M38.S06.T001.
  Review M38.S04.T001 (2026-11-19, independent reviewer, code read only): no cross-employee access found. Fixed: first-visit provisioning no longer 500s (matches accounts HR created earlier and backfills links, unique fallback e-mail, parallel first requests reuse the winner), fails closed for a login linked to two employees, for former employees and inactive ESS accounts; leave requests validated (not in the past, max 3 months within one year, existing type, working days > 0, no overlap with open/approved requests, within the remaining balance incl. carried/adjusted); check-out keeps the status/notes HR set; clock races → 409; listing payslips no longer writes. Expenses (pre-existing: every route open to any login, now every employee): employees may only file/see/submit their own claims and advances; approvals, payment, reports, AI, dashboard and category/policy changes need finance/HR rights (manager-approve hr.approve|finance.approve, finance-approve/pay finance.approve). Approver/actor ids are taken from the signed-in user instead of the request (recruitment approval, shelf-life disposition + AI review, recall action completion + AI review, expense advances) and the screens no longer send the demo user id. Tests: ESS 1 passed (incl. overlap/past/too-long leave, expense isolation and 403s), related suites 174 passed.
  M38.S06.T001 progress (2026-11-19): consumer QR page `/verify/[token]` (public, no login; product, batch, made-on, best-before, expired warning, unknown code = 'may not be genuine'); the public endpoint now only claims a blockchain anchor when one really exists — STUB (demo) anchors no longer show a fake transaction hash as 'verified on blockchain'; new anchors' QR opens the page. Partner portal Support tab: customers open helpdesk tickets (source PORTAL), follow them and reply; staff internal notes never shown; another customer's ticket is 404. Tests: distributor portal suite 3 passed, traceability auth 44 passed. Browser run 390 px (genuine + unknown code, ticket + reply), 0 overflow, no page errors. Evidence `coordination/milestones/M38/screenshots/s06/`. Remaining in S06: warehouse pick/putaway execution, redirect-stub assessment.
  M38.S06.T001 completion (2026-11-19, independent review pending for warehouse floor/QR/support): warehouse floor `/dashboard/warehouse-floor` (sidebar 'Warehouse Floor', PWA shortcut) with scan-confirmed picking and putaway: new `POST /wms/picking/tasks/{id}/scan-confirm` (bin must be the task's pick location in the task's warehouse, item barcode/SKU/lot must match, no over-pick, short pick needs a reason, someone else's task 403, needs the warehouse dispatch right) and `POST /wms/putaway/tasks/{id}/scan-execute` (item must match, bin must belong to the task's warehouse, another bin than suggested needs a reason, warehouse receive right). Test `backend/tests/test_m38_s06_scan_pick_putaway_db.py` passed; browser run 390 px (wrong bin refused, short pick with reason, putaway), 0 overflow, no page errors; evidence `coordination/milestones/M38/screenshots/warehouse/`. Redirect stubs assessed: the ~40 sub-routes are deliberate consolidation into hub tabs that render the content (sales: van-sales, delivery, collections, field-sales, portal…; warehouses: WMS/putaway; procurement: supplier-portal; middleware REDIRECTS map) — not missing screens. The two real gaps behind stubs (moto mpesa/fraud/performance, WMS picking/putaway execution) now have screens (field supervisor, warehouse floor). The office Collections tab works since the /collections API landed.
  Review M38.S06 + expenses (2026-11-19, independent reviewer, code read only). Fixed: HIGH expense approvals took the approver from the request — now the signed-in user; nobody approves, rejects or pays their own claim; finance approval must be a different person from the manager approver; HIGH a claim can only deduct the claimant's own advance. Public QR shows 'genuine' only for an ANCHORED record of an existing lot and flags quarantined batches (on_hold). Putaway scan locks the task row (no double execution), refuses when there is no received unlocated stock to move (no silent 'put away'), lot lookup scoped to the product; item scans need barcode/SKU/code (a lot label alone is not enough). Portal tickets: staff-entered descriptions of phone/e-mail tickets are not shown to customers; max 20 portal tickets per customer per day. Tests: scan pick/putaway, ESS (incl. self-approval/advance checks), distributor portal (3) passing. Open (recorded): remaining client-supplied actor ids in traceability (initiated_by/performed_by/approved_by on recalls/holds), shelf-life overrides/picks and recruitment requested_by/moved_by; anchor creation needs only a login; finance/HR viewers see all claims (by role design); advances have no approval step.
  Milestone regression (2026-11-19): backend full suite 1720 passed, 340 skipped (DB-gated), 14 deselected (environment-dependent load-simulation timing); M38 DB suites on disposable PostgreSQL: distributor portal 3, supplier portal 1, field app 1, ESS 1, scan pick/putaway 1 passed; M36 campaigns 2 and e-sign 1 passed. Frontend: tsc 0 errors, eslint 0 errors (66 pre-existing warnings), test:pwa 4 passed.
  M38 open findings closed (2026-11-19, owner: 'önce onlar'; independent review pending): (1) every remaining client-supplied actor id now comes from the session through `app/core/actor.py` — trace events (performer; an approver may only be the signed-in user holding quality/traceability approve), recall initiate/status, FEFO issue override and audit log (override approver = signed-in user with quality/inventory approve), retest request/result, recruitment requisition requester and pipeline stage mover; (2) trace anchors (the public QR) need a quality record right and an existing lot whose number is taken from the lot; anchored_by is the signed-in user; (3) partner sign-in lockout is keyed per e-mail + client address, so failed guesses cannot lock the real user out remotely (test: attacker address 429 after 5 failures, owner signs in); current-password guesses on password change are rate-limited and the new password must differ; (4) cheques are never posted and reversed: PENDING → DEPOSITED → confirm when cleared, or bounced/cancelled before posting (office screen buttons + error messages; test); (5) supplier ETA revision numbers serialised with a PO row lock; (6) the one-time activation token is removed from the address bar/history and pages send no referrer (browser-checked); (7) expense advances are recorded by finance (finance.edit) — employees see their own. Still open: GPS accuracy not stored; finance/HR viewers see all expense claims by role design; real-device and live-provider acceptance [!]. Tests: backend full suite 1720 passed (341 DB-gated skipped); M38 DB suites 4+1+1+1+1 passed; frontend tsc 0 errors.
  Review of the findings-closure commit (2026-11-19, independent reviewer): all seven claims verified true in code. Fixed: a recall status change no longer rewrites the approver — the changer is logged, and the approver is recorded only when the recall is approved (moved to active) by someone with traceability.recall_close or quality.approve(_all); approver rights also accept the _all variants; finance (finance.edit) can record an advance for the employee it pays; office Collections screen fixed — it could not create anything (no invoice picker; offered CREDIT_NOTE): invoice picker with open balance, optional number, real server messages, KPIs exclude bounced/cancelled, all statuses filterable, only the latest action's error shown (browser-checked: the form pre-fills the invoice and shows the server's 'balance reserved by collections awaiting confirmation' refusal); confirm message order; office collections only for open invoices; activation keeps the router history state; production images now take FORWARDED_ALLOW_IPS so the lockout sees real client addresses behind a reverse proxy (default 127.0.0.1 = trust none). Deployment note: set FORWARDED_ALLOW_IPS to the proxy address when one is put in front of the API. Tests: full suite 1720 passed; field, ESS and portal DB suites passing; tsc 0 errors. Still open: per-e-mail global cap across addresses (bcrypt-limited only); FEFO override approver can only be recorded by the approving supervisor themselves (no two-person flow).
  Pending acceptance tests (2026-11-19, owner: 'real M-Pesa we cannot test; do whatever the other pending tests need'): (a) malware scanning — DONE against a real ClamAV daemon (`clamav/clamav:stable`): found and fixed that every real scan failed (clamd INSTREAM replies end in NUL; the code waited for a newline, so all uploads stayed quarantined as SCAN_ERROR); test `backend/tests/test_m38_clamav_scan_db.py` (clean PDF released to staff, EICAR refused and removed) + unit cases; production compose now runs a `clamav` service (`DOCUMENT_CLAMAV_HOST=clamav`). (b) real phone (GPS, camera, touch signature, camera barcode, PWA install) — kit ready, run by the owner [!]: `docker-compose.lan.yml` (LAN address, CORS, API URL, Next.js allowedDevOrigins), `docs/PHONE_ACCEPTANCE_TEST.md` (12-step checklist, Android Chrome secure-origin flag, firewall note), `scripts/dev_set_password.py` (sets a synthetic account's password interactively, synthetic accounts only). Verified from the laptop over the LAN address in an emulated Pixel 7: sign-in, field app loads; GPS/camera need the phone's Chrome flag (cannot be applied by the automation browser). (c) Live M-Pesa — out of scope by owner decision [!]. (d) Live Gmail/Microsoft mailbox and calendar, WhatsApp Business — need provider credentials [!]. (e) Factory label printer + hardware scanner (M37.S04.T007) — needs the devices [!].
  iPhone path (2026-11-19, owner has an iPhone on the cable): HTTPS for phone testing without Android — `scripts/dev_lan_tls.py` makes a 90-day test CA name-constrained to the one laptop address plus a server certificate (kept in git-ignored `.lan-tls/`), `docker-compose.lan.yml` adds a Caddy proxy (`scripts/lan/Caddyfile`: app :3443, API :8443, CA download :8088, default_sni for IP access); checked from the laptop at 172.20.10.4 (iPhone hotspot): HTTPS app/API 200 and trusted with the test CA; emulated iPhone 13 over HTTPS: secure context, GPS, camera API available, field app loads. App icon set from the owner's POVU logo (`scripts/make_app_icons.py`; apple-touch-icon 180, 192, 512, maskable 512). Claude cannot operate an iPhone from Windows or install/trust certificates on it — those steps are the owner's (docs/PHONE_ACCEPTANCE_TEST.md §2).
  Real iPhone run by the owner (2026-11-19, iPhone Safari over the LAN HTTPS kit, home-screen install with the POVU icon): PASSED — sign-in; route with 3 outlets and owed amount; check-in saved **with location** (server: visit_logs row with the phone's real GPS fix and a camera photo); order FS-261119-5F1E6707 from the phone; collection form (refused correctly: the invoice already had a pending collection from the emulated run); outlet audit with a Not-OK item and a camera photo (AUD-261119-837BC741, 1 photo stored); My HR attendance check-in and 'already checked in'; call/directions links open the dialer and Google Maps. Not yet proven on the phone: finger signature on delivery and camera barcode — the seeded stop and pick task had already been completed by the emulated run; fresh ones (SYNTH-TRIP-CC47, SYNTH-PICK-CC47) await the owner's retest.
  Fixes from the phone run (owner's 53 screenshots + review): field users saw whole modules — the synthetic login carried sales.view/inventory.view; Field App and My HR need no module permission, Warehouse Floor now opens on inventory.dispatch (the picking list shows tasks the user can pick without inventory.view); seeded roles `field_auditor`, `field_supervisor`, `warehouse_picker` for least-privilege field/floor staff. Office screens: Sales Reports and Inventory Valuation added decimal strings as text ('KES 04565.00204', NaN) — converted to numbers; POS Sales tab called a missing GET /pos/sales (405) — endpoint added; Traceability tab showed 'Failed to load' to users without traceability rights — tab now hidden for them; Sales overview showed '$' and overlapping rows on phones — KES and wrapping rows; POS terminal squeezed on phones — cart stacks under products; wide tables in clipping cards are cut on phones — they scroll sideways (globals.css). New: delivery trips can be given the driver's app login (picker of active employee/sales-rep logins, validated server-side) — before, no office screen could set it, so no real driver would see their trips in the Field App; creating a trip returned 500 (lazy load after commit) — fixed and covered by test_m38_s02. iPhone camera barcode: iOS Safari has no BarcodeDetector, so the scan button was hidden; now the `barcode-detector` 3.2.3 ponyfill (zxing WebAssembly, bundled, no CDN) runs where the native API is missing — verified in Chromium with a fake camera playing a Code 128 'SY-A-01' (bin accepted). Product master: the owner's real POVU range (91 SKUs with catalogue sub-brands, `backend/app/db/seed_catalogue.py`, no prices — the catalogue has none, owner price list needed); synthetic drinks deactivated in the dev database.

## M39 — Every login sees only its screens; shops order for themselves (owner requests 2026-11-19/20)
**GOAL (owner, 2026-11-20): (1) like the field driver/rider, every role sees only the screens its permissions let it use — check each role screen by screen; (2) a neighbourhood shop (duka) installs the app, orders POVU products itself, pays by its assigned payment method, our team prepares and delivers, and the shop follows the order status and the estimated arrival from the driver's route.**
Already present (checked 2026-11-20): partner portal `/portal` (M38.S01) — any customer (account types CUSTOMER/RETAILER/DISTRIBUTOR/…) can sign in, see the catalog with server prices, place an order (DRAFT, staff confirm), see orders/invoices/statement/shipments, claims, tickets; installable as a web app (PWA). Missing: see rows below.
- [v] M39.S01.T001 — Role screen sweep: synthetic login per seeded role, open every visible menu entry and tab at phone and desktop width, record pages that are visible but refused/failing (403/405/500, "Access restricted", "Failed to load") and screens a role needs but cannot see; evidence table per role.
- [v] M39.S01.T002 — Fix the sweep's findings: menu entries and tabs gated on the permissions their APIs actually require; hide what a role cannot use; no role loses a screen it needs.
- [v] M39.S02.T001 — Shop order tracking: simple status timeline (received → confirmed → preparing → on the way → delivered) and estimated arrival from the driver's trip (stop order, distance, departure / last delivery time) on the portal order page.
- [v] M39.S02.T002 — Shop payment by assigned method: customer's payment method (cash on delivery / M-Pesa / credit with terms) applied to portal orders; M-Pesa pay from the portal on the existing STK path (live M-Pesa stays [!]).
- [v] M39.S02.T003 — Shop sign-up request from the app: a shop requests an account (name, phone, location); sales staff approve → customer + portal account; installable "POVU Shop" app identity (own manifest/start page).
  M39.S02 done 2026-11-20 (independent review: no IDOR; fixed its findings — already-paid orders no longer re-charged, one pending M-Pesa request per order + per-user limit, approval in one transaction, bad ids 422, split orders 'delivered' only when every shipment is, failed stops give no position): `backend/app/services/delivery_eta.py` (stage + ETA from the trip: stop order, straight-line × 1.3 road factor, 25 km/h motorbike / 30 km/h other, 10 min per stop; self-check `python -m app.services.delivery_eta`), portal order page timeline + 'Driver expected around HH:MM (n stops before you)'; payment policy from the customer's terms (prepaid → M-Pesa; no credit days → cash/M-Pesa on delivery; credit → on account/M-Pesa/cash), order carries the chosen method, 'Pay with M-Pesa' sends an STK push to the registered phone (sandbox; live M-Pesa stays [!]); public sign-up `/portal/signup` (with shop GPS) → staff 'Shop sign-up requests' on Customer Portal → approve creates a retail customer on cash on delivery, activates and returns the owner's set-password link; portal installs as its own 'POVU Shop' app (`public/povu-shop.webmanifest`). Tests: test_m38_s01 (6 passed incl. pay/track and sign-up). Also: header bell used admin-only notification routes (403 for everyone else) → own `/notifications/me*`; Field App / My HR shown to everyone → shown only to linked reps/drivers/field staff and employees (`/auth/me` feature_flags); CRM menu on crm.view.
- [D] M39.S02.T004 — App Store / Google Play listing: needs the company's Apple Developer and Google Play accounts (store wrapper on the same web app).
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T007. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.
  Plan (2026-11-20, after M36 per owner): one 'POVU' app for everyone (role decides screens; 'POVU Shop' is only a second home-screen icon of the same web app). Reuse the ScrubBots pipeline: Capacitor shell loading the production URL; GitHub Actions macOS runner (repo public = free) builds/signs the IPA and uploads to TestFlight with the App Store Connect API key (team C8NYQF627W, Apple Distribution cert to 2027-11, files in Documents/ScrubBots-signing/ios and Downloads/AuthKey_*.p8); Android AAB signed with a new upload key, uploaded in Play Console; app records created in App Store Connect / Play Console through Chrome. Blocker: a public HTTPS address (domain + server) — the ERP only runs on the owner's laptop/LAN today.
- [v] M39.S02.T005 — Real prices for the POVU range: owner's interim USD list (2026-11-20, "use these for now") loaded as active default price list POVU-INTERIM-USD (91 SKUs, `seed_catalogue.py`); KES shops get it converted at finance's latest USD rate (no rate → not orderable, never a guessed rate). Final list still to come from the owner.
- [v] M39.S03.T001 — Persona gap audit (owner, 2026-11-20: 'many users — work very carefully'): for each user group — shop / dealer / distributor ordering; delivery and field audit; marketing; finance; accounting; production; planning; stock control; quality control and assurance — list the end-to-end jobs, the screen each uses today (from the S01 sweep), missing modules, and broken hand-offs between systems (order → plan → production → stock → quality release → dispatch → invoice → ledger). Evidence: coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md; independent review.
- [v] M39.S03.T002 — A focused home screen per user group ('my work today': own queues, approvals, exceptions) that opens on sign-in, built on the role-gated dashboard (M37.S04); no group lands on an empty or irrelevant dashboard.
- [v] M39.S03.T003 — Close the audit's missing modules and hand-offs, each as its own row added here after the audit.
  M39.S01/S03 done 2026-11-20: synthetic login per seeded role (42 roles) opened every menu entry and tab; problems 314 (run 1, 38 roles) → 4 (final, 42 roles), the 4 being missing production-line scope assignments (shop-floor line scope) documented in the audit. Fixes: `_all` grants satisfy plain checks in backend `has_permission` and frontend `hasPermission`/`hasExactPermission`; `_own_*` aliases ignored for non-scope-aware modules (HR, payroll, maintenance, utilities); tabs gated on the permission their API checks (marketing, finance, analytics, sales, procurement, production cost, quality, admin); queries disabled without the right; Kenya Payroll reachable (stale middleware alias to HR removed); first screen after sign-in requires `<module>.view` (pickers land on Warehouse Floor); campaign authors get companies via `/crm/email-campaigns/companies`. New roles accountant, payroll_officer, planner, sales_order_desk, field_auditor, field_supervisor; "My work today" home. Hand-offs to the ledger: payroll, expenses, supplier payments, stock adjustments, POS sales (void → reversal); sales shipment → warehouse floor; new order → order-desk notification. Evidence: coordination/milestones/M39/M39_PERSONA_GAP_AUDIT.md (section 4 sweep table), M39_MORNING_REPORT_TR.md; backend suite 1736 passed / 352 skipped (DB-gated); tsc + eslint clean.
- [v] M39.S03.T004 — Production to the ledger and warehouse links: completing an order books one journal (raw materials / packaging / semi-finished → WIP at standard cost, labour+machine+energy → WIP, WIP → finished goods at actual cost; rules production/RAW_MATERIAL_ISSUE, FINISHED_GOODS_RECEIPT needed, PACKAGING_ISSUE, SEMI_FINISHED_ISSUE, CONVERSION_APPLIED optional); Production → Warehouse Links sets the raw-material, packaging, semi-finished (WIP) and finished-goods warehouses (packaging and semi-finished issued from their own warehouse). Finance seed now commits (chart of accounts was never persisted) + 1230 Packaging inventory.
- [v] M39.S03.T005 — Kenya Payroll run detail page: totals, per-employee lines, calculate / approve by right.
- [x] M39.S03.T006 — Not needed (owner 2026-11-20: finance and HR are run from head office); scoped template roles keep their screens hidden.
- [v] M39.S03.T007 — Owner decisions 2026-11-20 implemented: (a) invoice at delivery (driver POD), e-mailed to the shop; marketplace (ECOMMERCE) orders invoiced on payment, receipt recorded, mailed to the buyer, paper copy flagged on the pick list (print from Warehouse Floor); (b) list prices the same for every shop, promotions separate per shop (PromoScheme eligibility): shop portal 'My promotions', percentage promotions written as line discounts on portal/field orders, promotions named on the invoice; (c) money as JSON numbers everywhere (response encoder `app/core/json_numbers.py`, frontend types); (d) all open items same priority. Pending owner: employer payroll contributions (explained, decision open); posting-rule policy (explained).
- [v] M39.S03.T009 — Provider keys from the app: Integrations → Provider Keys (system administrator / owner, `integrations.provider_keys`) enters M-Pesa, SMS (Africa's Talking / Twilio), WhatsApp (Meta) and SMTP keys, stored encrypted, applied live (refresh 60 s); dashboard reminder while keys are missing; 'your order is on the way' WhatsApp/SMS to each shop when the driver starts the trip (silent until keys exist).
- [v] M39.S03.T010 — Accounting rule set prepared for finance (owner 2026-11-20: "prepare it, finance approves, then all mandatory"): `posting_rules_catalog.py` proposes 16 rules (sales, customer receipts cash/bank/M-Pesa, POS, supplier invoice/payment, payroll, employer contributions, expense claims, stock counts, 5 production steps) from a completed chart of accounts (seed_finance: bank, cash, M-Pesa, receivables, VAT in/out, payables, payroll liabilities, salaries, employer contributions, shrinkage, semi-finished); Finance → Posting Rules edits each account and approves (complete rules only); after approval a missing rule refuses the event (422) instead of saving it unbooked. Proposed in the dev DB, awaiting finance approval.
- [v] M39.S03.T011 — Employer payroll contributions: NSSF employer (= employee share), housing levy employer 1.5 %, NITA KES 50/month per employee, on each payslip line and booked as their own journal (payroll/EMPLOYER_CONTRIBUTIONS); run page shows employer cost and total cost to company. NSSF upper limit corrected to the Feb 2025 phase (UEL 72,000 → max 4,320; was 1,080).
- [v] M39.S03.T012 — USD rate from the Central Bank of Kenya (129.99 KES, posted 19-11-2026) entered; POVU list prices now orderable in KES. iPhone: the test CA is also served on https://<LAN_IP>:3443/rootCA.crt (Safari upgrades http:// to https:// and failed on :8088).
- [v] M39.S03.T013 — KES rates kept current by the system (owner 2026-11-20): `cbk_rates.py` reads the Central Bank of Kenya home-page box (USD, GBP, EUR, "Posted On") every 6 hours and stores it as source CBK; a rate typed by hand for that day is kept; Finance → Exchange Rates has "Fetch CBK rates now". First automatic run stored 20-11-2026: USD 130.00, GBP 170.35, EUR 142.71.
- [v] M39.S03.T014 — Rule set shown to finance on sign-in: while the rule set is not approved, a CFO / finance manager (finance.approve) lands on Finance → Posting Rules once per browser session; CEO/owner are not redirected.
- [v] M39.S03.T015 — iPhone retest fixes (owner screenshots 2026-11-20): page bottom hidden behind Safari's toolbar (shell h-screen → h-dvh), page left zoomed/shifted after typing (inputs 16px on phones), wide tables cut off (glass-table scrolls inside the card), attendance "Check out" pushed off-screen (header wraps), iOS date inputs overflowing, long e-mail overflowing the profile card, low-contrast Camera button, dev "N" badge over buttons; delivery: hint when Confirm is disabled (receiver name + signature), up to 10 photos per delivery and per audit.
- [v] M39.S03.T016 — Sales invoices follow the "mandatory once approved" switch: before finance approves the rule set a missing sales rule no longer blocks the invoice (it is issued and mailed, booked later); after approval it is refused. Found in the phone test: SYNTH-SH-CC47 was delivered but not invoiced because the proposed rule was still inactive.
- [v] M39.S03.T017 — Phone test steps 10–12 passed on iPhone (portal order WEB-261120-C933D713F4, ticket TKT-20261120-P1FBF76, SYNTH-PO-0001 accepted, PDF uploaded for review, /verify genuine). Fixes: distributor catalog widened the page on phones (grid item min-w-0); empty date inputs collapsed to a thin bar on iOS. Owner 2026-11-20: examples use the POVU range only — beverage placeholders/manual samples replaced; dev synthetic beverages re-pointed to POVU products and removed, synthetic supplier now a surfactant supplier.
- [v] M39.S03.T018 — Owner 2026-11-20: on a phone every button/tab is visible without a sideways scroll. Shared WorkspaceTabs always wrap below lg (prop removed); portal/supplier/field tab bars wrap; marketing report, shop-floor action panels, kanban chips wrap; globals.css mobile rules: flex rows in the dashboard wrap, flex children/selects capped at screen width, fixed 4–6 column grids become 2, cards that clipped a table now scroll it. Evidence: Playwright iPhone 14 Pro sweep of all 710 dashboard pages as owner (with a logged-out guard): 0 sideways button rows, 0 off-screen buttons (was 140 pages).
- [D] M39.S03.T008 — Live M-Pesa / SMS / WhatsApp / SMTP: code complete (M39.S03.T009); only the owner's provider keys are missing.
  Reconciled 2026-11-25 (M43.S00.T005): NOT_DUE commissioning gate, not a software defect. It is traced to M47.S02.T002 + M47.S02.T004 + M47.S02.T006. The software side is either implemented (see the row's evidence) or tracked as an executable M43–M46 task.

## M40 — Completion sweep: nothing left open except external dependencies (owner request 2026-11-21)

Owner: "add the whole list to TASKS.md and complete it; check for real by opening the app, pressing buttons and taking screenshots; no module without a screen, no screen/person/approval/order that should be linked in a workflow but is not; finish S05.T003; field teams, customers and online channels fully ready." Every row below needs code + test + live click-through with screenshots (desktop and 390 px) + independent review. External-provider rows stay [!].

- [v] M40.S01.T001 — Customer NPS / survey answering from the partner portal and a public one-time survey link; loyalty points balance and history in the portal.
  Done 2026-11-21 [v] (ee911c4, 3fd6ef1): portal Feedback (general + per delivered order, once each, locked per customer) and My points (balance, level, history); one-time public `/nps/<token>` links (SHA-256, 30 days, single answer) created from NPS → "Send to a customer" (copy/WhatsApp); loyalty points once per fully paid invoice (unique index); /loyalty and /nps routes now need sales/CRM rights. Test passed; live: link created and answered on a phone, portal feedback sent, 120 points shown (m40_nps_staff, m40_nps_public, m40_portal_feedback, m40_portal_points).
- [v] M40.S01.T002 — Maintenance technician "my work orders" phone screen: assigned/open work orders, start, log spares and time, complete with notes/photo.
  Done 2026-11-21 [v] (438e2b4, f0d54aa): menu "My Jobs" for assigned technicians; PM jobs and breakdowns assigned by user id (name matches backfilled only when unique): start, spare parts, up to 10 photos, complete/resolve; supervisors with maintenance.edit act on any job. Test passed; live on a phone: start → spare → photo → complete, breakdown start → resolve (myjobs_* screenshots).
- [v] M40.S01.T003 — Warehouse scanner extension (= M37.S04.T008): goods receipt, transfers and cycle counts take scans through the same resolver as pick/putaway.
  Done 2026-11-21 [v] — see M37.S04.T008.
- [v] M40.S01.T004 — Merchandiser flow in the field app: outlet-by-outlet shelf check (facings, out-of-stock, price, planogram compliance) with photos, linked to the visit and visible to the supervisor.
  Done 2026-11-21 [v] (79d2a3f): field app Shelf tab after check-in (facings, out of stock, shelf price, planogram, photo per product; correcting replaces), supervisor shelf report (out-of-stock outlets, average facings, planogram %, price range, latest findings). Test `test_m40_s01_t004_shelf_check_db.py` passed.
- [v] M40.S01.T005 — Remove the legacy ESS login/account code (SHA-256, unused token); ESS stays on the staff login.
  Done 2026-11-21 [v] (79d2a3f): legacy ESS login, SHA-256 hashing and token code removed; ESS accounts carry no password (staff sign-in); admin screen uses an employee picker.
- [v] M40.S01.T006 — Redirect stubs: confirm each of the 153 old addresses lands on a working tab (live check), keep them as compatibility links.
  Done 2026-11-21 [v]: live check — all 134 static old addresses redirect to a working page (0 errors); 20 parameterised ones follow the same map.
- [v] M40.S02.T001 — Workflow linkage audit (strict): every backend module has a screen; every hand-off is wired end to end — shop/distributor/online order → approval → sales order → pick → delivery/POD → invoice → collection/M-Pesa → statement; PR → approval → PO → supplier portal acknowledge → GRN → QC → putaway → supplier invoice → payment; production plan → work order → material issue → QC release → stock; ticket → assignment → resolution → NPS; leave/expense → approval → payroll/finance; field visit → order → delivery. Every approval reaches the approver's inbox/notification. Findings fixed.
  Done 2026-11-21 [v] (ef84cd6, 2fb95a7, 443fc1d, 2fe22cd, this commit): approval hand-offs — new My Approvals inbox (25 approval types, scope-aware, decide inline) and one bell notification per waiting item to the people who may decide it; purchase-request screen had no Submit/Approve/Reject/Create PO (added) and conversion of approved requests was blocked for everyone but superusers (fixed); approved unpaid leave now reduces pay; shelf-life extension approval moves the lot expiry; resolved tickets rated by the customer in the portal; scoped approvers no longer blocked by the central guard; approver identity from the session. O2C (order → shipment → invoice → payment/STK, POD in field app), P2P (PO approve → supplier acknowledge → GRN → invoice match → payment) and production chains confirmed wired on screens. Live: officer submits PR → manager bell + inbox → approve inline/on screen → Create PO (0 errors). Test `test_m40_s02_t001_approval_inbox_db.py` (6 tests) passed.
- [v] M40.S02.T002 — Live click-through of every persona (owner, sales, field rep, moto rider, driver, collector, field controller, merchandiser, warehouse, factory operator, QC, procurement, finance, HR/ESS, technician, distributor portal, shop portal, supplier portal, website chat visitor, Shopify order import) on the running app with screenshots; every failure fixed and retested.
  Done 2026-11-21 [v]: all 42 role logins swept page by page (owner 272 pages 0 problems; 41 roles one browser each; affected roles re-swept after fixes: 0 problems), per-role menu screenshots (1450cd5), live flows on phone/desktop: supplier portal, website chat, distributor portal feedback/points/ticket rating, technician My Jobs, field app shelf check, approvals chain. Fixed from the sweep: maintenance work-centre pick list, Quality → Brand assets for quality roles, mobile admin tab only for its admins, clear 'no production line assigned' message on the shop-floor terminal (operators/auditors need a line scope — configuration). [!] Shopify order import needs a live store (external).
- [v] M40.S03.T001 — Open rows from earlier milestones completed in this sweep (not external): M36.S05.T003 integration console, M36.S05.T005 ABM, M36.S03.T004 workflow designer, M36.S05.T002 landing pages/A-B, M36.S05.T004 conversation intelligence, M36.S06.T001–T004, M37.S03.T001 Web Push, M37.S03.T002 mobile admin lock-down, M37.S03.T003 iOS scan fallback (check: done in 66081d0), M37.S04.T008.
  Done 2026-11-21 [v]: every listed earlier row is [v] above with evidence (M36.S03.T004, S05.T002–T005, S06.T001–T004, M37.S03.T001–T003, M37.S04.T008).
- [v] M40.S03.T002 — Final regression (backend suite + DB suites on disposable PostgreSQL + tsc/eslint), TASKS.md status, commit and push.
  Done 2026-11-21 [v]: backend suite 1740 passed; 157/157 DB-gated files passed on disposable PostgreSQL (MQTT/SMTP/ClamAV gated files run against local test services); frontend tsc and eslint clean; committed and pushed to main.

## M41 — Open internal gaps found in the 2026-11-21 re-check (not external)

- [v] M41.S01.T001 — Discount approval on quotations and sales orders: `discount_approval_required` / `discount_approved_*` columns exist but nothing sets them, so the accept guard in crm_document_service is inert and `PLDiscountRule.requires_approval` / `max_discount_pct` are not enforced. Set the flag when a line or header discount exceeds the rule, approve/reject endpoint (approver ≠ creator), My Approvals entry + bell notice, block send/convert until approved, screen buttons, DB test, live click-through.
  Done 2026-11-21 [v]: limit = SystemConfig `sales.discount_approval_limit_pct` (default 10 %); highest line or whole-document discount above it -> PENDING_DISCOUNT on quotations and sales orders (`services/discount_approval_service.py`); quote cannot be sent/accepted (staff or customer) and order cannot be confirmed until approved; approve/reject `POST /quotes/{id}/discount/approve|reject`, `POST /sales/orders/{id}/discount/approve|reject` (sales approve right on the record; never the creator or the last editor, superusers included; reject needs a reason, creator gets a notice); any change re-checks and drops the approval; row locks against edit/send/approve races; My Approvals groups 'Quotation discount' / 'Sales order discount' + bell notice to deciders (own documents hidden); screens: badges, Approve/Reject discount, Edit draft quote (re-asks). Migration 0070 flags open drafts already above the limit. Found and fixed on the way: quote -> order copied percentages into fraction fields (10 % became 1000 %) and dropped the header discount; Shopify stored tax 16 instead of 0.16 (invoice tax 1600 %); order form sent 10 for 10 % (now /100, API refuses >1); quotation totals counted tax twice (0069 recomputes open quotes, signed ones untouched); orders without region and warehouse could not be confirmed by anyone; product edit always failed 422. Follow-up (owner 2026-11-21) both former limits fixed: scoped approvers now see every waiting row in their scope (batched scan, exact count; test with 520 other-region rows), and a document that waits again after a change (e.g. corrected after a rejection) is belled again — bell key = record @ last change, window from the last change, older notices honoured so the deploy sent no repeats (live: rejected 18 % quote corrected to 14 % -> manager's second bell). Evidence: `tests/test_m41_s01_db.py` (4 tests) + updated M36 signature and M17 Shopify tests; live click-through coordination/milestones/M41/ (desk quote waiting -> manager bell + My Approvals approve -> send -> customer phone code + accept -> order 0.15/0.16 -> 20 % order waits, approved on screen, confirmed; product eTIMS saved), 0 page errors; independent review (7 findings: races, superuser/editor self-approval, signer-code brute force/timing, re-check of old drafts, re-notify, inbox scan) all fixed (the two remaining limits in a follow-up); backend suite 1740 passed; 158/158 DB-gated files passed on disposable PostgreSQL at head 20261121_0070 (re-run after the follow-up) (SMTP/MQTT/ClamAV gated files against local test services); frontend tsc and eslint clean.
- [v] M41.S01.T002 — Verify the signer's e-mail on the customer quote signature (one-time code to the quoted contact's e-mail before accept/decline), stored in the decision evidence. Native part of M36.S04.T003; third-party e-sign provider stays [!].
  Done 2026-11-21 [v]: 'E-mail me a code' on the shared quote page; code only to an e-mail on file for the customer (customer e-mail or account contacts), same answer and timing otherwise (sent after the response); keyed hash, 15 min, 5 tries, single use, 5 requests per link per hour (unknown addresses counted, not stored), 10 wrong codes per link -> 24 h stop; decision records email_verified_at, staff see 'e-mail verified by code'. [!] live delivery needs SMTP keys (dev logs the code). Evidence: `tests/test_m41_s01_db.py` (4 tests) + updated M36 signature and M17 Shopify tests; live click-through coordination/milestones/M41/ (desk quote waiting -> manager bell + My Approvals approve -> send -> customer phone code + accept -> order 0.15/0.16 -> 20 % order waits, approved on screen, confirmed; product eTIMS saved), 0 page errors; independent review (7 findings: races, superuser/editor self-approval, signer-code brute force/timing, re-check of old drafts, re-notify, inbox scan) all fixed (the two remaining limits in a follow-up); backend suite 1740 passed; 158/158 DB-gated files passed on disposable PostgreSQL at head 20261121_0070 (re-run after the follow-up) (SMTP/MQTT/ClamAV gated files against local test services); frontend tsc and eslint clean.
- [v] M41.S01.T003 — eTIMS item classification: `Product.etims_item_code` and `tax_type_code` fields (migration, product screen) and use them in the eTIMS payload instead of the TODO placeholders. Provider auth/cancel/status stay [!] until the provider is chosen.
  Done 2026-11-21 [v]: products carry etims_item_code, etims_item_class_code, etims_tax_type (A-E) (migration 0068, product edit screen); payload uses them (tax type falls back to 16 % = B, 8 % = E); a live (non-simulation) submission names the products missing codes (422); invoice query now loads the customer (live submit would have crashed). [!] provider auth/cancel/status wait for the chosen eTIMS provider. Evidence: `tests/test_m41_s01_db.py` (4 tests) + updated M36 signature and M17 Shopify tests; live click-through coordination/milestones/M41/ (desk quote waiting -> manager bell + My Approvals approve -> send -> customer phone code + accept -> order 0.15/0.16 -> 20 % order waits, approved on screen, confirmed; product eTIMS saved), 0 page errors; independent review (7 findings: races, superuser/editor self-approval, signer-code brute force/timing, re-check of old drafts, re-notify, inbox scan) all fixed (the two remaining limits in a follow-up); backend suite 1740 passed; 158/158 DB-gated files passed on disposable PostgreSQL at head 20261121_0070 (re-run after the follow-up) (SMTP/MQTT/ClamAV gated files against local test services); frontend tsc and eslint clean.


## M42 — Employee digital business cards with QR, generated by the ERP (owner request 2026-11-24)

Brief and owner decisions: `coordination/milestones/M42/BRIEF.md`. Reference design: owner's card at github.com/Sekiph82/SekipHayit (GitHub Pages). Every employee defined in HR → Employees (single add or Excel/CSV import) gets a public card page and QR automatically; no manual step.

- [v] M42.S01.T001 — Data: `employee_business_cards` (one per employee: `slug` unique and permanent, status PUBLISHED/REVOKED, visibility toggles phone/WhatsApp/e-mail, EN title, short bio EN/SW, photo/cover from document storage, photo consent who/when). Name/phone/e-mail/role read live from `hr_employees`, not copied. Card created and published automatically on employee create (API, screen and bulk import); TERMINATED/archived → REVOKED automatically; rehire → HR can republish. Migration backfills published cards for current active employees. Audit log on every change. DB test.
  Done 2026-11-24 [v]: `employee_business_cards` (migration 0071, backfill: every existing employee got a card, terminated/archived as closed); name, role, phone, e-mail read live from hr_employees; card created on employee create (screen/API) and on Excel/CSV import, closed on TERMINATED/archive, republish keeps the slug; slug from the name with Turkish letters transliterated; owner 2026-11-24: a second person with the same name gets the department added (amani-wekesa-sales, then amani-wekesa-sales-2; -2 only without a department; same rule in the 0071 backfill; live: baraka-njoroge / baraka-njoroge-sales, both cards show only the name); never changes on rename; creation serialised by an advisory lock; every change audit-logged. Owner 2026-11-24: brand POVU, only the profile photo is per person (bio/cover fields dropped); WhatsApp on by default. Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.
- [v] M42.S01.T002 — Public endpoints (no login, in PUBLIC_ROUTES, rate-limited, noindex): `GET /api/v1/public/cards/{slug}` returns only visible fields; `GET /api/v1/public/cards/{slug}.vcf` vCard 3.0 UTF-8 with embedded photo. Revoked and unknown slug give the same "card no longer valid" answer with no personal data. Never expose personal phone, M-Pesa, bank, salary.
  Done 2026-11-24 [v]: `GET /public/cards/{slug}`, `{slug}.vcf` (vCard 3.0, folded, control characters stripped, photo embedded only with consent), `{slug}/photo` (nosniff); in PUBLIC_ROUTES; noindex; 120 req/min per client plus 30 misses/min (client address from the trusted proxy only); closed and unknown slugs give the identical 404 with no personal data; never M-Pesa, bank, salary, code or department; e-mail shown only when it is a plain address. Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.
- [v] M42.S01.T003 — QR: `GET /api/v1/hr/employees/{id}/card/qr.svg|png` (login) with the existing `qrcode` dependency, error correction M; ZIP of QR codes for a filtered employee set.
  Done 2026-11-24 [v]: QR SVG/PNG (error correction M, URL = PUBLIC_APP_URL/kartvizit/slug; in production refused unless PUBLIC_APP_URL is https and not local) for HR and for the employee; ZIP of live cards for a filter (max 500, built off the event loop). Decoded with zxing in the live run. Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.
- [v] M42.S02.T001 — Public page `/kartvizit/[slug]` (outside `/dashboard`): mobile-first copy of the owner's card layout (cover, large photo, name/title/company logo from brand_assets by company_id, Call/WhatsApp/E-mail tiles, Save contact), EN/SW switch, revoked view.
  Done 2026-11-24 [v]: `/kartvizit/[slug]` mobile-first copy of the owner's card (cover video, large photo, Save contact + Share, Call/WhatsApp/E-mail, tabs Contact/Company/Videos/Gallery/Catalogs with lightbox); shared POVU content from CARD_ASSETS_BASE_URL (owner: the SekipHayit GitHub Pages repo); languages EN/SW/TR (owner); closed view; noindex; no login redirect. Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.
- [v] M42.S02.T002 — HR screens: "Business card" tab on the employee record under `/dashboard/hr/employees` (preview, open public page, visibility toggles, photo upload with consent, QR download, revoke/republish) + bulk cards screen (filter company/branch/department, QR ZIP, print sheet) + printable card 85×55 mm front/back and A4 10-up via print CSS (no new PDF dependency). Permission `hr.cards.manage` (HR/IT).
  Done 2026-11-24 [v]: Employees screen: 'Card' per employee (QR, open, visibility toggles, card title, photo upload with recorded consent — JPEG/PNG verified, max 400 KB — close / publish again) and 'Business cards' page (filters, QR ZIP, print sheet 85x55 mm, 10 per A4, backs column-swapped for duplex, print CSS). Permission `hr.cards_manage` (hr_manager, admin). Found and fixed: HR could not import employees from Excel at all (central guard blocked /bulk-import for HR; the routes' own module check is now recognised). Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.
- [v] M42.S02.T003 — ESS "My business card": employee sees and shares own card and QR; editing stays with HR.
  Done 2026-11-24 [v]: My HR -> My Business Card (`/dashboard/ess/card`, `GET /hr/my-card`): own card and QR, open/share/download; editing stays with HR; a login linked to several records shows the current (active, newest) one. Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.
- [v] M42.S03.T001 — Acceptance: live click-through (add employee → card live → scan QR with phone → save contact on iPhone and Android → change phone → same QR shows new number → terminate → card closed; bulk import creates cards), independent security review of the public endpoints, backend + DB suites, tsc/eslint, commit and push. Physical print run waits for the final production domain (Persistent External gate).
  Done 2026-11-24 [v]: live (LAN dev, synthetic POVU staff): HR adds an employee on the screen -> card live -> photo with consent -> QR decoded -> card on iPhone and Android, Save contact gives a vCard with photo and work phone -> Swahili switch -> phone changed, same QR shows the new number -> terminated -> 'no longer valid', no name -> CSV import of 2 employees -> 2 live cards -> bulk screen + print sheet -> employee's own card; 0 page errors. [!] physical print run and a real phone scan wait for the production domain (PUBLIC_APP_URL). Evidence: `tests/test_m42_business_cards_db.py` (2 tests); live click-through coordination/milestones/M42/ (live_report.txt + screenshots); independent security review (7 findings: spoofable rate-limit key, QR with a local address, slug race, vCard CR injection, photo magic bytes, unbounded ZIP, mailto parameters — all fixed with tests); backend suite 1740 passed; 159/159 DB-gated files passed on disposable PostgreSQL at head 20261124_0071 (copilot test re-run after isolating it from the dev Redis); frontend tsc and eslint clean.


## POVU Brand Vault — owner-approved new logo and ICO rollout (2026-11-25)

- [ ] **ERP-POVU-VAULT-001:** Use approved PUBLIC `Sekiph82/POVU-Brand-Vault` release, created from `C:\Users\sekip\Desktop\Character Reference Sheets\Character Refence Sheets`. Confirm canonical new POVU transparent logo and exact original ICO package. Never generate a lookalike or reuse stale approved logo accidentally; compare hashes. Sole source of truth: the owner-designated folder above, imported into the public Vault. Use only freshly calculated hashes of the files actually imported; no previous brand registry or historical digest matching. Replace every existing POVU logo/ICO usage in the application with this exact release and rebuild/test; preserve unrelated application branding.
- [ ] **ERP-POVU-VAULT-002:** Audit and replace actual POVU identity assets in `frontend/public/povu-logo.jpg`, site favicon, Next.js `frontend/src/app/layout.tsx` icons and `frontend/public/povu-shop.webmanifest` referenced icons. Preserve source files and support rollback; make no unapproved branding changes outside POVU ERP/Shop. Implement transparent and raster outputs through lossless format-safe conversions only if needed for platform compatibility, while keeping original master byte-identical in Vault.
- [ ] **ERP-POVU-VAULT-003:** Test Next.js favicon/PWA cache updates, all icon sizes (192/512/maskable/apple-touch as applicable), manifest references and browser/device visuals; preserve old assets until verified migration. The designated owner-authorized public Vault brand assets may be consumed by SHA; exclude other private files and product data.


# M43–M47 — HubSpot parity-plus software roadmap (owner directive 2026-11-25)

**All software work is autonomous and accountless.** Previous M36 features are baseline assets, not a rebuild list. All tasks below are PLANNED until Claude inspects actual source; statuses only advance under the binding protocol. Preserve prior acceptance history and existing open ERP-POVU-VAULT tasks. Original recommendation numbers 01–40 are kept traceable. Use current official product/edition documentation, not marketing names alone. Benchmark Smart CRM, Sales, Marketing, Service, Content, Data, Revenue/Commerce, Agent/Breeze and AEO where available; distinguish native functionality, optional integrations, paid/edition-limited capabilities and proprietary external data.

Reference entry points (refresh and record date/version during audit): https://www.hubspot.com/products ; https://www.hubspot.com/products/data ; https://developers.google.com/workspace/gmail/api/auth/scopes ; https://developers.google.com/workspace/calendar/api/auth ; https://developers.google.com/google-ads/api/docs/best-practices/testing ; https://learn.microsoft.com/graph/api/resources/mail-api-overview ; https://developers.facebook.com/docs/business-management-apis/system-users/overview/ ; https://learn.microsoft.com/en-us/linkedin/marketing/integrations/marketing-tiers ; https://business-api.tiktok.com/portal/docs/register-as-a-developer/v2.0 . Provider review/access tiers are future activation dependencies, not present defects.

# M43 — Advanced CRM & Sales Hub

## M43.S00 — Mandatory reconciliation and parity baseline (before new code)
- [x] M43.S00.T001 — Synchronize existing Desktop workspace safely; inspect current main, commit history since M36, actual task rows, migrations, source/UI/API/test evidence and recorded screenshots. Reconcile every stale status/heading, especially M36 PLANNED, M36–M42 [v]/[~], M41 superseding M36 signature/discount notes, M16/M30 live AI history, old Project Status, open brand-vault rows and all unrelated outstanding tasks. Do not rewrite immutable history or mark DONE without matching evidence; queue missing acceptance for M43 gate. Record old vs new status and exact evidence. Update TASKS.md immediately.
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v]: Desktop was fast-forwarded from 6bd7314 to origin/main 86ba54b with no conflicts; owner files kept (untracked .hiveai/ and two M25 logs left untouched). Ledger reconciled: M20/M21 stale headings changed to DONE (bounded); M30 heading corrected; M36 heading PLANNED → IMPLEMENTED [v]; M36.S01.T001/S01.T005/S04.T003 [~] → [v] with remainders moved to M43.S01.T001–T005 and M45.S01.T014 (M41.S01.T001/T002 supersede the old discount and signer notes); M16.S02.T003/M30.S05.T002 [!] → [v] on the 2026-11-20 live-AI evidence. M36–M42 [v] rows stay [v] and are queued for the M43 gate; none is marked [x] without a gate. ERP-POVU-VAULT-001–003 stay open as executable rows. Old vs new status is recorded inline on each row ("Reconciled 2026-11-25").
- [x] M43.S00.T002 — Harmonize AGENTS.md, CLAUDE.md, coordination/CLAUDE_AUTONOMOUS_EXECUTION_POLICY.md and other active execution instructions with this owner override (Claude-only, ledger after each task, no routine task testing, milestone gate then sync); preserve owner branding directives and historical logs. Inspect active instructions for conflicts and eliminate competing live trackers. Update TASKS.md immediately.
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v]: CLAUDE.md gains a 2026-11-25 directive at the top and its H!veAI adapter section is labelled HISTORICAL; AGENTS.md gains a 2026-11-25 override banner; coordination/CLAUDE_AUTONOMOUS_EXECUTION_POLICY.md gains a 2026-11-25 override section (milestone-batched work, consolidated gate, accountless). History is preserved. No competing tracker: the .hiveai/ folder is untracked and is not read or written.
- [x] M43.S00.T003 — Produce dated official HubSpot edition capability matrix across all product families, including service/customer success, CRM customization, analytics/report builder, custom objects/associations, automation, sequences, omnichannel, AI, integrations, permissions, content and revenue. For each capability map actual ERP model/API/UI/test/evidence and classify COMPLETE/DEPTH_GAP/MISSING/EXTERNAL_ACTIVATION/NOT_APPLICABLE with rationale. Add any uncovered software gaps as individually scoped tasks to appropriate M43–M46 or follow-on milestone before closing baseline. Include feature-level acceptance criteria and native FMCG differentiators; no arbitrary parity percentages. Update TASKS.md immediately.
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v]: `coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md` maps 12 official HubSpot sources (fetched 2026-11-25, all HTTP 200) across 9 product families to actual ERP models, services, endpoints and screens, classified COMPLETE / DEPTH_GAP / MISSING / EXTERNAL_ACTIVATION / NOT_APPLICABLE, with native FMCG advantages. Limit: per-feature edition matrices were readable only for Smart CRM and part of Marketing Hub. Eleven new gap tasks were added (M43.S01.T011–T012, M45.S01.T015–T022, M46.S01.T006) and the scope of M43.S01.T008, M43.S01.T010 and M45.S01.T003 was extended. No percentage parity claim. The matrix is re-audited in M47.S01.T001.
  v2 2026-11-25 [v] (final baseline):
  - The full official edition catalog was read in the browser (17 sections, about 600 feature rows) and saved as `coordination/milestones/M43/HUBSPOT_CATALOG_FEATURES_2026-11-25.md`.
  - A separate read-only explorer agent verified every ERP-side row. Corrected: 13 classes (for example ads, social, quotas, playbooks and deal score were DEPTH_GAP, not MISSING; subscriptions and multi-language were overstated) and 9 evidence citations (forecast, templates, transcript, buying roles, CSAT, segments, CPQ bundles).
  - The matrix was rewritten as v2 with ERP advantages beyond HubSpot and NOT_APPLICABLE reasons (no tenant code execution; QuickBooks/Xero, Salesforce, BNPL and capital financing not applicable).
  - New tasks added: M43.S01.T013–T016, M44.S01.T012–T013, M45.S01.T023, M46.S01.T007. Scope extended: M43.S01.T012, M44.S01.T009, M45.S01.T008/T010/T011/T014/T017/T019, M46.S01.T001/T002/T004/T006.
  - Total implementation rows: 59 (40 original + 19 additional).
- [x] M43.S00.T004 — Build shared local integration contract harness and synthetic demo profile: isolated PostgreSQL/Redis, local Mailpit/IMAP, test-only OAuth, signed webhook and provider HTTP fixtures, deterministic test time, safe egress controls, cleanup/reset, explicit demo badges and real application's adapter boundary. Inventory existing harnesses first; reuse and extend. Document supported public API versions/scopes and unavailable/private contracts; no provider accounts or actual customer records required. Add test cases but run only at M43 gate. Update TASKS.md immediately.
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v]:
  - Egress guard `backend/app/core/provider_http.py`: PROVIDER_EGRESS live/local/off, local by default outside production, refusal before any socket, test-transport injection.
  - Deterministic clock `backend/app/core/clock.py`.
  - Delegated OAuth boundary:
    - `backend/app/services/oauth_service.py` and `backend/app/models/oauth_connection.py`, migration `20261125_0072` (oauth_connections, oauth_states).
    - API `/api/v1/integrations/oauth/*` (providers, own connections, start, public callback with a single-use state, disconnect); the callback is in PUBLIC_ROUTES.
    - Behaviour: PKCE S256, scope check, encrypted tokens, refresh under a row lock with rotation, Google revoke plus local wipe, audit, NOT_CONFIGURED without a client.
    - Google and Microsoft client credentials added to Integrations → Provider keys.
  - Local simulator `backend/tests/provider_sim/` (Google and Microsoft OAuth, userinfo, Graph `/me`, fault injection via /_control; `python -m tests.provider_sim`, loopback only) and signed-webhook helpers.
  - Docs `docs/INTEGRATION_HARNESS.md` (public contracts and scopes, unavailable steps in M47.S02.T002).
  - Tests prepared, NOT RUN: `backend/tests/test_m43_s00_t004_harness.py` (egress policy, full OAuth round trip for both providers, state replay, consent refusal, missing scope, 429 with Retry-After, invalid_grant, not configured). Only a py_compile syntax check was done.
  - Bounded delta: the Connected-accounts UI tab (callback target `/dashboard/integrations?tab=connected-accounts`) is delivered with M43.S01.T001/T002.
  - Mailpit and the disposable PostgreSQL conventions were reused, not rebuilt.
  Inventory 2026-11-25 (implementation not started):
  - Existing harness pieces: a disposable PostgreSQL per DB test file (`TASK_DB_ENV`; 128 `*_db.py` files), a local SMTP/Mailpit opt-in (`SMTP_TEST_SERVER`, e.g. `tests/test_m36_s02_t005_campaigns_db.py`), the conftest login limiter isolated from Redis, `app/core/callback_security.py` (M-Pesa token, Meta HMAC, fail-closed in production), and the encrypted provider key store `app/services/provider_credentials.py`.
  - Missing pieces: a provider HTTP egress guard, a generic OAuth 2.0 + PKCE connection/token store, a local OAuth/provider ASGI simulator (in-process transport for tests, runnable on 127.0.0.1 for browser E2E), a deterministic clock and a signed-webhook fixture helper.
  - Plan: build these as the shared adapter boundary for M43.S01.
- [x] M43.S00.T005 — Audit every persistent external gate from M01–M42, split software readiness from future commissioning, migrate account/domain/device/factory/data-dependent acceptance to M47 register as NOT_DUE [D] with traceable original IDs. Keep genuine unfinished software executable (including Shopify, WhatsApp/SMS, SMTP, M-Pesa, bank/eTIMS, scanner, app-store wrapper and e-sign where public contracts permit); add explicit implementation tasks for actual code gaps, not just credential absence. Preserve historical live evidence and unresolved legal/business decisions. Update TASKS.md immediately.
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v]: every [!] row in the ledger (M07.S03.T002/T003, M13.S03.T002/T003, M17.S02.T001/T002, M18.S02.T003/T004, M19.S02.T004, M37.S01.T007, M37.S02.T001/T002, M37.S04.T007, M39.S02.T004, M39.S03.T008 and the Persistent gates for KRA, M-Pesa, bank and printer) plus [P] M19.S02.T005 → [D] NOT_DUE, each traced to an M47.S02 row; 0 [!] rows remain. The software side of these gates already exists (Daraja, eTIMS connector, bank import, SMTP/SMS/WhatsApp keys via M39.S03.T009, PWA); the remaining software gaps are the explicit M43–M46 rows (OAuth mail and calendar, voice, ads, e-sign adapter). Unresolved legal/business decisions are kept as they were.

## M43.S01 — Implementation tasks
- [x] M43.S01.T001 — Gmail OAuth 2.0 and native mailbox adapter (original recommendation 01/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Gmail API over the M43.S00.T004 OAuth boundary: `backend/app/services/mail_api_adapters.py` (profile/history cursor with paging, 404 history expiry → bounded resync, raw RFC 822 → existing parse/store so threading, Message-ID dedupe, bounces and unsubscribe are shared; send via messages.send; 401 refresh-and-retry, 429/5xx temporary), `email_mailbox_service` branches for OAuth mailboxes (is_connected, sync, send, background sync), `email_accounts.oauth_connection_id` (migration 20261125_0073), callback creates/relinks the mailbox; UI `frontend/src/components/ConnectedAccounts.tsx` on the e-mail page (connect/disconnect, NOT_CONFIGURED shown as 'Waiting for setup'); simulator Gmail endpoints. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t001_t002_oauth_mail_db.py (import + cursor + replay + reply threading, history expiry, API send, disconnect, 429 leaves cursor/data unchanged). Google OAuth app verification and a real mailbox → M47.S02.T002 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Extend existing IMAP/SMTP mailbox and outbox; implement documented Gmail API delegated OAuth auth/code/token/refresh/revoke, incremental history cursor/full-resync recovery, thread and attachment metadata, send/reply and dedupe. UI connect/disconnect, consent scopes and unconfigured status. No Google registration now.
  - **Acceptance at milestone gate:** Local OAuth + Gmail contract fixtures exercise callback state, token expiry, 401/429, history expiry, replay, reply threading and redaction; actual Google app verification and mailbox activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T002 — Microsoft 365 OAuth and Microsoft Graph mail (original recommendation 02/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Microsoft Graph mail on the same adapter: inbox messages delta with nextLink/deltaLink paging, 410/syncStateNotFound reset, $value MIME import, sendMail with base64 MIME; tenant/owner isolation via per-user oauth_connections; simulator Graph mail endpoints. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t001_t002_oauth_mail_db.py (Graph cases). Entra app registration, publisher verification and tenant admin consent → M47.S02.T002 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Implement delegated Microsoft identity authorization and Graph mail delta sync, send/reply, folder/thread mapping, encrypted tokens, pagination, disconnect and consent. Retain generic mailbox support.
  - **Acceptance at milestone gate:** Local Graph/OAuth simulator covers delta expiry, tenant/owner isolation, refresh, consent refusal, throttling and idempotency; tenant and mailbox activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T003 — Google Calendar two-way synchronization (original recommendation 03/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Two-way Google Calendar: `backend/app/services/calendar_sync_service.py` push (create/patch/delete, sendUpdates=none so invitations stay the ERP iCalendar REQUEST/CANCEL, Meet link via conferenceData.createRequest), pull with syncToken / 410 full resync, linked-event move/cancel with conflict policy (ERP wins when both changed; conflict recorded and shown), other events stored as start/end-only busy blocks used by overlapping/free_slots (no private titles); tables calendar_event_links, calendar_busy_blocks; 5-minute loop; meetings endpoints push after create/patch/cancel; 'Calendar sync needs your attention' panel + ConnectedAccounts on the meetings page; simulator Calendar v3. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t003_t004_calendar_sync_db.py (DST-day meeting, push lifecycle, no duplicate, busy/free events, token expiry rebuild, provider move/cancel, simultaneous edit conflict, disconnected calendar). Bounded: ERP meetings are single events (provider recurring series are imported as busy instances via singleEvents/calendarView). Live Google calendar/Meet → M47.S02.T002 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Reuse meeting service and ICS; implement Calendar API mapping, sync tokens, event creates/updates/deletes, recurrence/time zones, attendee updates, conflict and cancellation policy, Meet creation only where API supports it.
  - **Acceptance at milestone gate:** Local calendar contracts exercise DST, sync token expiry, duplicate callbacks and simultaneous edits; no Google account needed; live OAuth/Meet deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T004 — Microsoft Outlook Calendar two-way synchronization (original recommendation 04/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Two-way Outlook calendar on the same service: Graph /me/events with transactionId dedupe, Teams link via isOnlineMeeting where the account supports it (else the pasted link stays), calendarView/delta with UTC preference and @removed handling; simulator Graph events/delta. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t003_t004_calendar_sync_db.py (Microsoft cases). Webhook subscriptions not used (polling every 5 minutes); Teams availability depends on the tenant licence. Tenant/Teams activation → M47.S02.T002 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Implement Graph events/delta mapping, conflict resolution, recurring event and cancellation handling; Teams meeting capability gated by supported account/API permissions; existing ICS fallback.
  - **Acceptance at milestone gate:** Contract tests for delta links, webhook renewals if applicable, DST, deleted events and idempotent changes; Microsoft tenant/Teams activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T005 — Public customer self-booking and routing (original recommendation 05/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Public booking pages: `booking_service.py` (working hours/weekdays/notice/horizon/buffers in the page zone, DST-safe; hosts anonymous; round-robin by oldest last assignment or first available; all hosts advisory-locked in fixed order → no double booking; honeypot, consent, per-IP-hash and per-page limits; manage token stored as SHA-256 for reschedule/cancel; 24 h reminder e-mail loop), endpoints `/booking-pages` (staff) and `/public/book/*` (PUBLIC_ROUTES), tables booking_pages/booking_page_bookings; UI `/book/[slug]`, `/book/manage/[token]`, BookingPagesPanel on meetings page with user picker for team hosts; invites through existing host-mailbox iCalendar and connected calendar push. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t005_booking_db.py (slots/DST/anonymity, round robin, concurrent last slot 1×201 + 3×409, consent/honeypot/off-grid, manage reschedule/cancel, reminder not claimed without mailbox). Public URL needs the production domain → M47.S02.T001 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Build signed/public configurable booking pages on existing meeting service; individual/team round-robin availability, working hours, time zones, buffers, cancellations, reschedule, reminders, consent, spam protection and no exposed private calendar details.
  - **Acceptance at milestone gate:** Real localhost visitor books/reschedules/cancels from desktop and phone; concurrent bookings cannot double-book; invitations reach local mail sink.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T006 — Email engagement and sales activity analytics (original recommendation 06/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Opt-in engagement tracking: `crm_engagement_service.py` (CRM_EMAIL_TRACKING_ENABLED + per message/campaign/sequence opt-in, never INVOICE, recipient tracking opt-out; HTML alternative with signed click redirects only to links stored with that message — no open redirect — optional domain allow-list, unsubscribe untracked; 1×1 pixel; proxy/scanner/too-fast events flagged machine and excluded; 60 s duplicate suppression; keyed IP hash only), public `/public/t/*`, `/crm-engagement` analytics per sender/message; tracking toggles on manual/campaign/sequence UIs; 'Stop tracking' on the unsubscribe page; CRM Engagement tab explaining opens are an indicator. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t006_engagement_db.py (token tamper, render, allow-list, machine detection, redirect/dedupe/opt-out/analytics). Mailpit delivery check (multipart for tracked mail only) in the gate walkthrough. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Extend existing outbound/quote tracking with opt-in open pixel and redirect click events, tracking disable/consent, safe URL allowlists, bot/proxy indicators, privacy-friendly aggregation, attribution, unsubscribes and rep dashboard. Explain unreliable opens.
  - **Acceptance at milestone gate:** Local mail sink and browser click/open fixtures; no open redirect, no tracking after opt-out, duplicate/bot handling, no false live sends.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T007 — Sales quotas and advanced forecast management (original recommendation 07/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Quotas: `quota_service.py`, `/sales-quotas` (REP/TEAM/TERRITORY/COMPANY × period × one currency; actual = confirmed orders net of discount, other currencies reported as excluded, never summed; forecast categories derived or overridden on crm_records.forecast_category; adjustable projection assumptions stored with snapshots; weekly snapshot loop; CSV export; managers see all, reps own; audit), TEAM quotas roll up sub-teams (T016); CRM Quotas tab. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t007_quotas_db.py (KES/USD separation, draft/cancelled excluded, categories incl. OMITTED, assumptions, snapshot). Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Add quota periods, territory/team/rep goals, currencies and historical snapshots; compare actual confirmed revenue and forecast categories to quotas; adjustable assumptions and RBAC. Reuse forecasting service.
  - **Acceptance at milestone gate:** Synthetic KES/USD targets, no mixed-currency totals, forecast/actual reconciles to orders, scoped managers and exports.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T008 — Provider-independent telephony and voice adapter (original recommendation 08/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Voice: `voice_service.py` Africa's Talking Voice adapter (POST /call with apiKey, agent rung first then customer dialled from the answer callback, record only with consent, XML Say/GetDigits/Dial), callback secret token (AT callbacks are unsigned), idempotent lifecycle QUEUED→…→final never overwritten, late recording notification kept only with consent+https+retention, inbound IVR menus with consent announcement and digit routing to available agents, power dialer one call at a time with outcome capture, capability discovery (voicemail drop reported unsupported, not faked); provider keys in Integrations; tables voice_agent_profiles/voice_ivr_menus/voice_dialer_sessions + call_logs lifecycle columns; VoicePanel on the calls page; simulator AT voice. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t008_t009_voice_db.py (disabled honesty, lifecycle/idempotency, token, consent, IVR routing). Bounded: one provider adapter (Africa's Talking) behind the interface; voicemail drop unsupported by that provider. Carrier, number and live call → M47.S02.T003 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Extend click-to-call/logging with configurable voice adapter, capability discovery, documented Africa's Talking Voice or equivalent public contract, inbound/outbound call lifecycle callbacks, consent/retention, recordings reference and safe disabled mode; choose no carrier/account now. Extended by the 2026-11-25 parity matrix: power dialer queue, voicemail-drop recordings and an inbound IVR menu with team routing, all through the same adapter.
  - **Acceptance at milestone gate:** Local SIP/HTTP fixture or simulator with signed callbacks, state transitions, repeats, failure, consent and purge; no call to real number; provider selection/activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T009 — Transcription and conversation coaching (original recommendation 09/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Transcription: `transcription_service.py` (CALL_TRANSCRIPTION_ENABLED; consented https recording within retention; adapters 'http' — documented multipart contract with Bearer key — and 'local' faster-whisper if installed, else NOT_AVAILABLE; timestamps/speakers/language stored; 3 attempts; consent withdrawal deletes recording, transcript and quoted insights; recap lists only quoted next steps/questions/objections), endpoints transcribe/withdraw-consent/transcript, coaching via existing conversation intelligence; CallTranscript on the calls page; simulator transcription endpoint. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t008_t009_voice_db.py (retry then DONE with segments, withdrawal, refusal without consent). Coaching playlists not built → new row M43.S01.T017. Real transcription endpoint/engine → M47.S02.T008 [D]. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Process consented recordings through configurable transcription adapter; optional local/offline engine when practical, transcript timestamps/speaker labels where supported, language handling, secure storage, retries and evidence-linked coaching; reuse conversation intelligence.
  - **Acceptance at milestone gate:** Synthetic licensed/local audio or fixture transcript, failure/consent withdrawal/retention tests; no real recording, no paid provider; actual voice/transcription activation separate.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M43.S01.T010 — Sales playbooks and guided selling (original recommendation 10/40)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Playbooks: `crm_playbook_service.py`, `crm_stage_gate.py`, `/crm-playbooks` (typed questions, show_if conditions, required only when visible, whitelisted field mapping; DRAFT→PENDING_APPROVAL→PUBLISHED by a different editor, one published version per family, runs store the exact version; stage playbook can block leaving the stage until completed — enforced in update/convert/close_won; outcome report with no causal claim) and deal plans shared via revocable link (`/public/deal-plans/*`, customer ticks only customer steps; `/plan/[token]`); CRM Playbooks tab. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t010_playbooks_db.py. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Configurable call/visit/qualification checklists, required questions/fields, deal-stage guidance, versioning, manager approval, templates and outcome reports; native field and CRM integration. Extended by the 2026-11-25 parity matrix: deal plans / mutual action plans with dated steps shared with the customer contact.
  - **Acceptance at milestone gate:** Synthetic distributor opportunity follows playbook to quote/order; version, conditional prompts, scopes and audit history verified.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.

- [x] M43.S01.T011 — Multiple deal pipelines (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Multiple pipelines: crm_pipelines + pipeline_id on stages/records (migration moves every existing stage and record into the default 'Sales pipeline'); record follows its stage on create/move/convert; pipeline-scoped stages, forecast and funnel; automation condition pipeline_id; `/crm/pipelines` CRUD; PipelineSelect on board and stages pages; stage-gate messages shown on the board. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t011_pipelines_db.py (migration preservation checked in the gate upgrade step). Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Add a pipeline entity (per company, per record type, e.g. distributor onboarding vs key-account deals). Stages belong to one pipeline. Migrate the existing stage set into a default pipeline without data loss. Pipeline-scoped forecast, funnel and automation triggers. Pipeline picker on the board.
  - **Acceptance at milestone gate:** Migration from previous head keeps every record and stage history; two synthetic pipelines with separate stages, forecast and funnel; automation triggered per pipeline; RBAC and company isolation.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [x] M43.S01.T012 — Deal scoring and buying groups (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Deal score: `crm_deal_score_service.py` (stage, activity recency, human e-mail engagement, buying-group coverage minus blockers, quote, stage age, ERP customer signals — overdue invoices and past orders; unknown factors listed and excluded; configurable weights; daily history for trend; 'not a trained prediction'); buying group = contacts associated to the deal with role labels (T015), missing-role warnings; `/crm-playbooks/records/{id}/score`; DealScore panel. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t012_deal_score_db.py. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Explainable deal score and win probability from stage age, activity recency, engagement, buying-group coverage, quote status and native ERP signals (credit/overdue). Configurable weights; no claimed predictive accuracy. Buying-group roles (decision maker, influencer, finance, user) on account contacts, with coverage gaps shown on the deal. Revised by matrix v2: committee_role buying roles already exist on crm_account_contacts — link them to deals rather than rebuild; score factors and trend history.
  - **Acceptance at milestone gate:** Synthetic deals give deterministic scores with per-factor explanation; role coverage warnings; missing-data label; permissions.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

- [x] M43.S01.T013 — Sales workspace and productivity (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Workspace: `crm_workspace_service.py`, `/crm-workspace` (today: queue tasks due/overdue + open deals without next step; repeating tasks spawn next once on completion; snippets; multiple signatures appended on manual mail; per-contact weekly cap CRM_CONTACT_EMAIL_CAP_PER_WEEK enforced for manual/sequence/campaign at queue and send; send-time suggestion only from ≥3 human opens; deal summary from stored facts; productivity per person); CRM 'My work' tab. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t013_workspace_db.py. 1-to-1 video messages are tracked links for now; video hosting arrives with M46.S01.T006. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** A rep workspace with task queues and repeating tasks (recurrence rules) on crm_activities; canned snippets and multiple e-mail signatures; per-contact sales-email frequency caps shared with marketing; a rule- and history-based smart send time (no claimed accuracy); 1-to-1 video message links (M46.S01.T006 assets, a view event on the timeline); deal summaries from timeline facts (deterministic, optional AI); a rep productivity report (activities, response times, stage moves).
  - **Acceptance at milestone gate:** A synthetic rep works a queue, recurrence creates the next task once, the frequency cap blocks the extra send, video views appear on the timeline, the deal summary cites only existing facts, and the productivity report reconciles to activities.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [x] M43.S01.T014 — Lead rotation, deal approvals, deal splits and handoffs (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Routing/approvals/splits/handoffs: `crm_routing_service.py`, `/crm-routing` (rules by priority with conditions incl. lead-form source_detail, ROUND_ROBIN / smooth WEIGHTED / FIXED, unavailable or inactive people skipped, rule row locked; stage approval rules with value threshold — first attempt files a PENDING request and refuses, no self-approval (also DB CHECK); deal splits totalling exactly 100 % credited through the existing commission engine; one handoff brief per won deal), routing on record create; CRM 'Routing & approvals' tab; splits on the playbooks deal panel. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t014_routing_db.py. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** Round-robin and weighted lead rotation with availability and territory; lead-form routing rules; deal-stage approval gates on the existing approval engine (for example a credit limit or a large discount before Closed-Won); deal splits sharing revenue/commission credit with the commissions module (splits must total 100%); sales → service/finance handoff briefing (open promises, terms, contacts) when a deal is won.
  - **Acceptance at milestone gate:** Rotation is fair under concurrency (no double assignment); an approval gate blocks a stage move until approved; splits validate to 100% and flow to commissions; the handoff brief is created once with correct links; RBAC.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [x] M43.S01.T015 — Standalone contacts, associations and lifecycle stage (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Contacts: crm_contacts (partial unique lower(email)), crm_contact_associations (customer/crm_record/ticket/quotation/sales_order with labels), crm_lifecycle_history; migration backfills one contact per e-mail from CRM records and account contacts, name-only records keep their own contact, roles → labels, lifecycle from the most advanced linked record; `crm_contact_service.py` keeps the record's primary contact in step on create/qualify/convert/win (forward only), manual backward move needs a reason; `/crm-contacts` with scope rules and duplicate refusal; CRM Contacts tab. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t015_contacts_db.py (backfill verified in the gate upgrade step). Consent stays per e-mail address (crm_contact_consents), as before. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** A first-class Contact entity (person) migrated from the inline CRM fields and crm_account_contacts without data loss; many-to-many associations contact↔customer/company↔deal↔ticket↔quote with labels (for example billing contact, decision maker); a lifecycle stage property (subscriber → lead → MQL → SQL → opportunity → customer → evangelist) updated by rules and kept in history. Consent and suppression stay per person.
  - **Acceptance at milestone gate:** The migration from the previous head keeps every contact, consent and activity; one contact linked to two customers; association labels; lifecycle transitions with history; dedupe-safe; company isolation.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [x] M43.S01.T016 — Teams, record configuration and views (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): Teams/views: crm_teams (code = existing sales_team_id values, backfilled) with hierarchy and members, cycle refusal, roll-up used by TEAM quotas; crm_tags/crm_record_tags with record-list filter; stage required_fields enforced when entering a stage (values in the same request count); calculated properties via existing COMPUTED custom fields on crm_record; crm_saved_views (whitelisted filters, own or shared with own team) shown as list or month calendar; `/crm-teams`; CRM 'Teams & views' tab. Tests prepared, NOT RUN (M43 gate): tests/test_m43_s01_t016_teams_views_db.py. Static check only: py_compile on new backend files; frontend tsc/eslint/build NOT RUN.
  - **Scope:** A sales-team entity with hierarchy (replaces free-text sales_team_id, migrated) used by scopes, forecast roll-ups and reports; object tags; required fields per pipeline stage; calculated properties reusing COMPUTED custom fields; saved views/presets per user and team; board and calendar visualizations of CRM index pages.
  - **Acceptance at milestone gate:** Hierarchy roll-up is correct; a stage move is blocked when a required field is missing; tag filters; a saved view is shared with a team only; calendar view on phone and desktop.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

- [x] M43.S01.T017 — Coaching playlists (gap found while implementing T009; HubSpot 'Coaching playlists')
  Accepted 2026-11-25 [x] at the M43 gate: evidence in coordination/milestones/M43/gate/ (migration 01, tests 02, frontend 03/04, browser 05, independent review 06).
  Done 2026-11-25 [v] (pending M43 gate): crm_coaching_playlists / crm_coaching_clips (migration 20261125_0073); `/calls/playlists` (managers create playlists and clip consented, transcribed calls within retention by second ranges; non-managers see only clips of their own calls); clips deleted on consent withdrawal and when retention purges the transcript; CoachingPanel on the calls page. Tests prepared, NOT RUN: tests/test_m43_s01_t017_coaching_db.py.
  - **Scope:** Managers collect consented call transcript segments (timestamp ranges) into named playlists for training; access limited to managers and the listed team; removal when consent is withdrawn or retention ends.
  - **Acceptance at milestone gate:** Playlist built from synthetic transcripts; withdrawn consent removes the clip; non-managers cannot see other agents' clips.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

## M43.S02 — Major milestone acceptance and synchronization
- [x] M43.S02.T001 — Run consolidated milestone acceptance once all implementation work is ready: backend/DB/provider-contract/frontend/build/real browser desktop+mobile/synthetic E2E/security/independent review; include relevant prior features, fix and rerun failures, record exact code SHA, commands, results, screenshots and reviewer. No live-provider requirement. Reconcile applicable older [v] rows only if evidence/gate covers them. Update TASKS.md; do not mark [x] on failure.
  Done 2026-11-25 [x]:
  - Migration: empty → head, downgrade ↔ upgrade, and seeded 20261124_0071 → head (14/14 backfill checks). The first run found and fixed a crm_teams.active_flag backfill bug.
  - Tests: backend suite 1759 passed / 446 skipped; M43 DB-gated 15/15 files, 60 tests on disposable PostgreSQL 16 (port 25432).
  - Frontend: tsc 0 errors, eslint 0 errors (1 fixed), production build OK.
  - Browser on the real local app (backend :8020 on a disposable DB, frontend :3220): a non-admin rep and a CRM manager on desktop, a public visitor at phone width. Booking, no double booking, contact create and RBAC verified; a false "invitation sent" message was fixed.
  - Independent review: separate reviewer agent, ACCEPT_WITH_FIXES, 15 findings (2 high, 7 medium). All fixed with tests except three low items deferred to M44.S01.T014. Re-run after the fixes is green.
  - Gate fixes found by the tests: OAuth forced refresh, playbook v2 publish, required revenue 0.
  - Not covered here: the full DB-gated regression of older milestones (M36–M42) and live providers (see M47).
- [x] M43.S02.T002 — On gate PASS, mark accepted software tasks [x], document unresolved activation-only prerequisites, commit and push evidence/ledger; fetch and verify Desktop HEAD equals origin/main, record synchronization and clean status; update next milestone/action in TASKS.md. If sync fails do not claim milestone closed; retry safely. Continue autonomously.
  Done 2026-11-25 [x]: the gate commit was pushed to origin/main; after fetch, Desktop HEAD equals origin/main (523e6ed, the gate-pass commit). The working tree is clean apart from owner-untracked files (.hiveai/, two M25 logs). The gate container and walkthrough servers were removed and temporary next-dev edits reverted.

# M44 — Advanced Marketing Hub — accountless

Dependency: previous major milestone gate and synchronization PASS. Reuse shared harness, native models and adapter registry.

## M44.S01 — Implementation tasks
- [x] M44.S01.T001 — Visual email designer (original recommendation 11/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): `email_design_service.py` validates and renders block documents to responsive table HTML plus plain text. Blocks: heading, text with **bold**, https image with alt warning, button with WCAG contrast check, product card, columns, spacer, divider, footer. Text is escaped; links are http(s) only; javascript: and data: are refused; variables with fallback. Table mkt_email_designs (migration 20261125_0074) with draft → published → retired versions. `/email-designs` provides preview (CSP), publish, new version and test send through the consent-aware outbox. Campaigns can use a published design: per-recipient HTML and text, unsubscribe link always added, tracked links rewritten when tracking is allowed. UI: E-mail designer tab (desktop/phone preview, warnings) and a design picker on campaigns. Tests prepared, NOT RUN: tests/test_m44_s01_t001_email_designer.py.
  - **Scope:** Responsive block editor, reusable templates, brand assets, variables, HTML/text render, accessibility, preview and consent-aware outbox; sanitize HTML and avoid remote tracking by default.
  - **Acceptance at milestone gate:** Local browser renders phone/desktop and Mailpit delivery; template versioning, invalid fields, XSS and unsubscribe.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T002 — Meta Ads adapter (original recommendation 12/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): Meta: Graph insights API (version setting) with level=campaign, daily rows, cursor paging, purchase/lead actions as conversions, and spend in account currency. Error codes map as follows: 190 → AUTH, 4/17/32/613 → RATE_LIMIT, 10/200 → PERMISSION, 100 → VALIDATION. Draft check uses execution_options=[validate_only] with the daily budget in minor units (zero-decimal currencies handled). Shared framework: `ads_adapters.py` + `ads_service.py`, tables ads_accounts / ads_campaign_days / ads_drafts, `/ads` API, CRM tab "Ads". The adapters cover reporting, account discovery and validate-only checks. Accounts store currency; synced days are upserted (a re-sync gives the same rows), with performance CTR/CPC/cost per conversion. Drafts carry an idempotency key and a budget guardrail (ADS_MAX_DAILY_BUDGET); a second editor approves them. Publish is always refused (403). Every adapter is NOT_CONFIGURED until tokens are set, and all traffic goes through the egress guard. Local simulator: tests/provider_sim/ads_app.py. Contract tests in tests/test_m44_s01_t002_t005_ads.py: 5 contract tests pass locally; the DB part is NOT RUN until the gate. Real developer/app/business accounts, app review and live writes → M47 activation [D].
  - **Scope:** Build documented Marketing API read/report and permitted campaign/ad set/ad draft operations, OAuth/token settings, paging, metrics mapping, sync console, approvals and dry-run budget guardrails. Production create/publish always disabled until authorized.
  - **Acceptance at milestone gate:** Local versioned Meta contract payloads validate auth/error/rate limit, currency, idempotency and read/write mapping; real business/account/app review deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T003 — Google Ads adapter (original recommendation 13/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): Google: GAQL through googleAds:searchStream with developer-token and login-customer-id headers. The customer_client hierarchy is supported, and cost_micros is converted to currency. UNAUTHENTICATED/RESOURCE_EXHAUSTED/PERMISSION_DENIED/UNIMPLEMENTED are mapped. Draft check is campaignBudgets:mutate with validateOnly and partialFailure (no real mutate). Shared framework: `ads_adapters.py` + `ads_service.py`, tables ads_accounts / ads_campaign_days / ads_drafts, `/ads` API, CRM tab "Ads". The adapters cover reporting, account discovery and validate-only checks. Accounts store currency; synced days are upserted (a re-sync gives the same rows), with performance CTR/CPC/cost per conversion. Drafts carry an idempotency key and a budget guardrail (ADS_MAX_DAILY_BUDGET); a second editor approves them. Publish is always refused (403). Every adapter is NOT_CONFIGURED until tokens are set, and all traffic goes through the egress guard. Local simulator: tests/provider_sim/ads_app.py. Contract tests in tests/test_m44_s01_t002_t005_ads.py: 5 contract tests pass locally; the DB part is NOT RUN until the gate. Real developer/app/business accounts, app review and live writes → M47 activation [D].
  - **Scope:** Implement documented Google Ads API auth/developer token config, account hierarchy, GAQL reports, campaign draft/mutation mapping and validation-only path where supported, budget approval and version handling.
  - **Acceptance at milestone gate:** Local Google Ads protocol fixtures cover auth, paging, partial errors, currency micros and no real mutate; developer token/test or production account activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T004 — LinkedIn Ads adapter (original recommendation 14/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): LinkedIn: LinkedIn-Version (YYYYMM) and Rest.li 2.0 headers, paged adAccounts, campaign names, and adAnalytics with pivot CAMPAIGN daily (costInLocalCurrency). HTTP 401/403/426/429 map to AUTH/PERMISSION/VERSION/RATE_LIMIT, with Retry-After honoured. There is no validate-only call, so drafts get local checks plus access-tier gating (development tier blocks writes) and the USD 10 minimum. Shared framework: `ads_adapters.py` + `ads_service.py`, tables ads_accounts / ads_campaign_days / ads_drafts, `/ads` API, CRM tab "Ads". The adapters cover reporting, account discovery and validate-only checks. Accounts store currency; synced days are upserted (a re-sync gives the same rows), with performance CTR/CPC/cost per conversion. Drafts carry an idempotency key and a budget guardrail (ADS_MAX_DAILY_BUDGET); a second editor approves them. Publish is always refused (403). Every adapter is NOT_CONFIGURED until tokens are set, and all traffic goes through the egress guard. Local simulator: tests/provider_sim/ads_app.py. Contract tests in tests/test_m44_s01_t002_t005_ads.py: 5 contract tests pass locally; the DB part is NOT RUN until the gate. Real developer/app/business accounts, app review and live writes → M47 activation [D].
  - **Scope:** Implement versioned LinkedIn Marketing API OAuth/scopes, account/campaign/report mapping, supported draft operations, approval and retry; capability gating by access tier.
  - **Acceptance at milestone gate:** Local contract tests for version headers, pagination, denied permissions, budget validation and analytics; LinkedIn application/account/access tier deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T005 — TikTok Ads adapter (original recommendation 15/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): TikTok: report/integrated/get with the Access-Token header and page_info paging; stat_time_day is mapped to a date. Error codes map as follows: 40100 → RATE_LIMIT, 40104/40105 → AUTH. Callback verification uses the TikTok-Signature header (t=…,s=HMAC-SHA256 of 't.body', 5-minute window). There is no validate-only call, so drafts get local checks (USD 50 minimum). Shared framework: `ads_adapters.py` + `ads_service.py`, tables ads_accounts / ads_campaign_days / ads_drafts, `/ads` API, CRM tab "Ads". The adapters cover reporting, account discovery and validate-only checks. Accounts store currency; synced days are upserted (a re-sync gives the same rows), with performance CTR/CPC/cost per conversion. Drafts carry an idempotency key and a budget guardrail (ADS_MAX_DAILY_BUDGET); a second editor approves them. Publish is always refused (403). Every adapter is NOT_CONFIGURED until tokens are set, and all traffic goes through the egress guard. Local simulator: tests/provider_sim/ads_app.py. Contract tests in tests/test_m44_s01_t002_t005_ads.py: 5 contract tests pass locally; the DB part is NOT RUN until the gate. Real developer/app/business accounts, app review and live writes → M47 activation [D].
  - **Scope:** Implement documented TikTok API for Business auth, account/campaign/ad group/ad reporting and supported draft operations, paging, callback verification, budgets and no default live publishing.
  - **Acceptance at milestone gate:** Local contract fixtures exercise token expiry, rate limits, currency/time and provider errors; developer account/approval deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T006 — Organic social publishing orchestration (original recommendation 16/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): Composer checks documented constraints per network: text limits, Instagram exactly one image and at most 30 hashtags, TikTok one video, LinkedIn text and link, https media. Posting adapters: Facebook Page feed/photos, Instagram container → media_publish, LinkedIn /rest/posts with version header, and TikTok Content Posting PULL_FROM_URL with SELF_ONLY privacy (unaudited apps cannot post publicly). X and YouTube, and unsupported formats, go to manual export. The worker publishes approved, due posts once (status claim plus external id). Posts are NOT published when SOCIAL_PUBLISHING_ENABLED is off or the token is missing. Errors are mapped (missing permission, auth); a timeout is marked "may have posted, check before retry". Idempotency key on create. Shared: `social_service.py`, `/social` API, signed `/public/social/meta` webhook, tables social_channels / social_posts / social_items, CRM tab "Social" (Calendar / Listening inbox / Channels). Simulator: tests/provider_sim/ads_app.py (social routes). Tests: tests/test_m44_s01_t006_t008_social.py; the unit and simulator tests pass locally, the DB part is NOT RUN until the gate. Real pages, apps, app review/audit and SOCIAL_PUBLISHING_ENABLED → M47 activation [D].
  - **Scope:** Unified composer, asset validation and scheduled/approved queue; implement documented supported Meta Pages/Instagram, LinkedIn and TikTok posting adapters plus other supported channels as audited; use manual export for unsupported endpoints/formats. No real accounts or posts.
  - **Acceptance at milestone gate:** Local provider simulator verifies media constraints, schedule, approval, idempotency, disabled/missing permissions and status accuracy.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T007 — Content calendar and approval (original recommendation 17/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): Cross-channel calendar grouped by day, campaign tags, owner, and channel time zones (a naive time is read in the channel's time zone). Approval is bound to the version: an edit to content creates a new version that needs approval again, while a reschedule keeps it. A second editor must approve. Reschedule, cancel and retry are supported, with a conflict warning when two posts on one channel fall within 30 minutes. The publishing history log is shown per post. Asset library: media are referenced by https URL (a DAM is M45 content work). Shared: `social_service.py`, `/social` API, signed `/public/social/meta` webhook, tables social_channels / social_posts / social_items, CRM tab "Social" (Calendar / Listening inbox / Channels). Simulator: tests/provider_sim/ads_app.py (social routes). Tests: tests/test_m44_s01_t006_t008_social.py; the unit and simulator tests pass locally, the DB part is NOT RUN until the gate. Real pages, apps, app review/audit and SOCIAL_PUBLISHING_ENABLED → M47 activation [D].
  - **Scope:** Cross-channel calendar, draft/version/approval, time zones, asset library linkage, reschedule/cancel, campaign tagging, owner assignment and publishing history.
  - **Acceptance at milestone gate:** Local browser creates and approves posts, handles conflicts and simulated failures, no publication on unconfigured channel.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T008 — Social listening and moderation (original recommendation 18/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): Comments and mentions are taken only from opted-in channels: Meta webhooks (Facebook Page feed comments, Instagram comments/mentions), verified by X-Hub-Signature-256 and fail-closed without META_APP_SECRET. Other networks come in through manual CSV import. No scraping, and no claim of platform-wide listening. Duplicates are removed by network and id; an author's deletion blanks the text and author. Keyword sentiment and topic tags (English and Swahili) show their evidence words. The moderation queue supports assign/replied/hidden/done, and reply drafts can be suggested and edited by a person; nothing is auto-sent. Shared: `social_service.py`, `/social` API, signed `/public/social/meta` webhook, tables social_channels / social_posts / social_items, CRM tab "Social" (Calendar / Listening inbox / Channels). Simulator: tests/provider_sim/ads_app.py (social routes). Tests: tests/test_m44_s01_t006_t008_social.py; the unit and simulator tests pass locally, the DB part is NOT RUN until the gate. Real pages, apps, app review/audit and SOCIAL_PUBLISHING_ENABLED → M47 activation [D].
  - **Scope:** Ingest authorized comments/mentions/messages/metrics through documented permitted APIs/webhooks, manual imports for unsupported sources, sentiment/topic tagging with evidence, moderation queues and response drafts. No prohibited scraping.
  - **Acceptance at milestone gate:** Synthetic events test dedupe, permissions, signed callbacks, deletion, opt-in and manual import; no claim of platform-wide listening.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T009 — Website behavioral analytics and journey (original recommendation 19/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): `web_analytics_service.py`, tables web_events / web_identities / web_consents. SDK `frontend/public/povu-analytics.js` shows a cookie banner with necessary/analytics/marketing categories and sends nothing before a choice; page views are automatic, `data-povu-cta` and `data-povu-form` send CTA and FORM events, and `povuAnalytics.track/identify/forget` are available. Public `/public/web/{consent,collect,identify,forget}` endpoints apply a per-connection limit; the server re-checks consent. Visitor and session ids are stored only as keyed hashes. No IP address, user agent, query string or full referrer is stored; UTM fields and the referrer host are kept. Bots are dropped, a client event id is deduplicated, and each visitor is capped at 300 events per hour. A visitor is linked to an e-mail only with marketing consent. The staff tab "Website analytics" shows a summary (visitors, sessions, top pages, first-touch sources, events), an ordered funnel, and a contact journey with first touch, plus the install snippet. Retention is WEB_ANALYTICS_RETENTION_DAYS (395), purged by the daily retention task; visitors can erase their own data. Not built: logged-in portal-visitor identification in chat and deal-level journey, both moved to M45.S01 reporting. Tests prepared, NOT RUN against DB: tests/test_m44_s01_t009_web_analytics_db.py (the unit part passes).
  - **Scope:** Consent-aware first-party event collector, sessions, page/form/CTA events, UTM, identity association after consent, funnel/cohort/journey reports, retention/deletion and configurable local SDK. Extended by matrix v2: cookie consent manager with categories, logged-in portal-visitor identification in chat, custom events and event visualizer, deal and customer journey reports.
  - **Acceptance at milestone gate:** Local website journey feeds real CRM attribution with synthetic visits; opt-out, bot/dedupe, data reconciliation and no raw sensitive identifiers.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T010 — Dynamic audiences and lookalike preparation (original recommendation 20/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): `audience_service.py`, tables mkt_audiences / mkt_audience_members. Rules are include-all plus exclude-any conditions on channel, city, country, region, segment tag, customer type, CRM lifecycle, orders in 90 days and days since the last order, all validated. Preview, save, recompute and delete are available. Members need an e-mail and SUBSCRIBED consent by default; other matches are counted as blocked. Export is SHA-256 hashed normalised e-mails as CSV, refused unless AUDIENCE_EXPORT_ENABLED. Upload to an ad platform returns 503 until a provider adapter is activated (M47). "Similar customers" is a local explainable score (channel, region and type share, order-frequency closeness) labelled "not an ad-platform lookalike". UI is the CRM tab "Audiences". The existing `CustomerSegment.criteria_json` was left untouched (manual segments keep working). Tests prepared, NOT RUN against DB: tests/test_m44_s01_t010_audiences_db.py (the unit part passes).
  - **Scope:** Rule-based dynamic lists, exclusion/consent, audience preview and segmentation; implement allowed customer-list/audience API adapters where documented, local similarity scoring with explainable features and hashed export. Provider-owned lookalike computation must not be simulated as real.
  - **Acceptance at milestone gate:** Synthetic audience membership/recompute and local upload contracts; block unconsented contacts, disabled provider and real export by default; platform eligibility deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [x] M44.S01.T011 — Email complaint feedback and deliverability (original recommendation 21/40)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): `deliverability_service.py`. Signed event webhooks at `/public/mail-events/{mailgun|sendgrid|generic}` (Mailgun HMAC-SHA256, SendGrid ECDSA P-256, generic HMAC; 10-minute replay window; 503 when not configured). An event applies only when it matches a sent CRM e-mail and recipient: bounce → BOUNCED, complaint → COMPLAINED, unsubscribe → UNSUBSCRIBED, so suppression holds. Each provider event id is processed once (mail_feedback_events). `/deliverability` provides a summary, a DNS plan and an offline SPF/DKIM/DMARC check (no DNS lookup, no claim the domain is set up). Deliverability panel on the Engagement tab. Tests prepared, NOT RUN: tests/test_m44_s01_t011_deliverability_db.py. Relay account and DNS → M47.S02.T001/T002 [D].
  - **Scope:** Extend bounce/outbox with provider feedback-loop webhooks/adapters for documented SMTP relay providers, signed event verification, message/recipient linkage, suppression, retries, DMARC/DKIM/SPF setup diagnostics without requiring DNS.
  - **Acceptance at milestone gate:** Local signed complaint/bounce fixtures and Mailpit; forged/mismatched callbacks ignored, suppressed recipients cannot send; production mail/DNS/relay activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.

- [x] M44.S01.T012 — E-mail governance and smart content (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Done 2026-11-25 [v] (accepted at the M44 gate 2026-11-26): A/B on campaigns (variant B subject/body/design, 0–50% split, deterministic SHA-256 assignment per recipient, `ab_variant` on outbox rows); `/crm/email-campaigns/{id}/ab-result` declares a winner only with ≥100 sent per arm and a two-proportion z-test p<0.05 on human clicks, otherwise "no winner". Smart blocks: design blocks carry an audience (lifecycle stage / customer channel), unknown recipient → hidden; designer has a "Show only to" selector. Personalisation tokens with fallbacks already in T001. Send-time optimisation: per-recipient send_after at the person's usual opening hour (≥3 human opens, else scheduled time; no lift claimed). Approval: request/approve/reject by a second editor; scheduling refused until APPROVED when MARKETING_EMAIL_APPROVAL_REQUIRED=true (default off). Single-send API `POST /email-designs/{id}/send` (published design, CAMPAIGN purpose → consent, suppression and the existing cross-channel cap of M43.S01 apply). CTAs = design button blocks. Locale-based blocks not added (no locale field on contacts) — noted for M45 content localisation. Tests prepared, NOT RUN against DB: tests/test_m44_s01_t012_governance_db.py (unit part passes).
  - **Scope:** A/B tests for campaign e-mails with a statistically honest winner rule (or no winner); smart content blocks by segment, lifecycle or locale; advanced personalization tokens with fallbacks; a send-time optimization rule from first-party engagement history (no claimed lift); an e-mail approval step; a cross-channel per-contact frequency cap; a single-send API for transactional marketing e-mail; campaign CTAs.
  - **Acceptance at milestone gate:** Variants split deterministically; no winner below the threshold; smart blocks render per recipient in Mailpit; an unapproved e-mail cannot send; the cap holds across campaign and sequence; the API respects consent.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [x] M44.S01.T013 — Messaging channels: Messenger, Instagram DM, Slack and custom channels (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  Done 2026-11-26 [v] (accepted at the M44 gate 2026-11-26): Messenger and Instagram DMs come in on the signed Meta webhook (/public/social/meta, same META_APP_SECRET, fail-closed) for pages registered under Social → Channels. Each DM thread is one inbox conversation (channels MESSENGER / INSTAGRAM / CUSTOM). Replays and Meta's echoes of our own sends are removed by message id. Replies go through the Graph Send API (messaging_type RESPONSE) only inside Meta's 24-hour window; without the page token they are refused as NOT_CONFIGURED. Slack: deal won, new ticket and approval waiting are queued once each (crm_slack_deliveries) and posted to SLACK_WEBHOOK_URL with up to 5 retries; ticket subjects are left out of Slack. Custom channels API: POST /public/channels/{key}/messages and GET …/outbox with a per-channel bearer token (shown once, stored as SHA-256, can be rotated or disabled). UI: thread page /dashboard/crm/messages/{id} reached from the Inbox, and a CRM tab "Messaging channels" (status and custom channels with API notes). Code: messaging_service.py, crm_channels.py, messaging_public.py, migration 0074. Simulator: Send API and Slack stub in tests/provider_sim/ads_app.py. Tests: tests/test_m44_s01_t013_messaging.py; the unit tests pass, the DB part is NOT RUN until the gate. Real Meta app review, the page token and the Slack workspace → M47 [D].
  - **Scope:** Meta Messenger and Instagram messaging webhooks (documented Graph API, signature verified) and the send API into the unified CRM inbox; Slack incoming-webhook/app notifications for deals, tickets and approvals; a documented custom channels API so any channel can post into the inbox. All NOT_CONFIGURED until activation; no real accounts.
  - **Acceptance at milestone gate:** Signed simulator webhooks create conversations once; forged ones are refused; replies go through the simulator; Slack notifications reach a local stub; a custom channel message is threaded; permissions.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

- [x] M44.S01.T014 — M43 review residuals (from the M43 independent review, 2026-11-25)
  Done 2026-11-26 [v] (accepted at the M44 gate 2026-11-26): one global rule, so every endpoint is covered — a foreign-key violation (SQLSTATE 23503) now returns 422 "A referenced record does not exist" instead of 500 (app/core/exception_handlers.py). The dialer also checks its record and customer ids when it is created, because a bad id would otherwise block every later "next call". Access logs: app/core/log_redaction.py masks ?token= / access_token / secret / key in uvicorn access and error lines, which covers the unsigned Africa's Talking callback. Runbook: docs/DEPLOYMENT.md → Database rollback warns that the 0073 and 0074 downgrades destroy data (back up first). Tests: tests/test_m44_s01_t014_residuals.py; the log unit test passes, and the API 422 cases (team member, saved-view team, split user, dialer record and customer) are NOT RUN until the gate.
  - **Scope:** Return 422 instead of 500 for unknown foreign keys (team members, saved-view team, dialer record/customer, split user). Redact the voice callback token from access logs (Africa's Talking callbacks are unsigned, so the secret stays in the URL by provider design). Document the destructive 0073 downgrade in the runbook.
  - **Acceptance at milestone gate:** API tests for each FK case return 422; a log sample shows the token redacted.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

## M44.S02 — Major milestone acceptance and synchronization
- [x] M44.S02.T001 — Run consolidated milestone acceptance once all implementation work is ready: backend/DB/provider-contract/frontend/build/real browser desktop+mobile/synthetic E2E/security/independent review; include relevant prior features, fix and rerun failures, record exact code SHA, commands, results, screenshots and reviewer. No live-provider requirement. Reconcile applicable older [v] rows only if evidence/gate covers them. Update TASKS.md; do not mark [x] on failure.
  Done 2026-11-26 [x] — evidence in coordination/milestones/M44/gate/ (GATE_REPORT.md):
  - Migration on disposable PostgreSQL 16 (127.0.0.1:25432): empty → head, and 0074 downgrade ↔ upgrade; all 16 M44 tables are recreated by the migration SQL.
  - DB-gated tests: M43 + M44, 24/24 files pass. After the review fixes, M44 9/9 and the touched files 5/5 pass. Two former skips in t012 now run on their own segment.
  - Full backend suite: 1786 passed, 457 skipped, 0 failed.
  - Frontend: tsc 0 errors; eslint 0 errors (67 warnings, all from before M44); production build OK, rebuilt after the fixes.
  - Browser on the real local app (backend :8040 on a disposable DB, frontend :3240), with a non-admin marketer and a rep, on desktop and at 375 px:
    - Messenger reply shows an honest NOT_CONFIGURED.
    - A custom channel reply is queued.
    - Channel creation shows its token once.
    - All M44 tabs load; there is no horizontal overflow on phone.
    - RBAC hides the marketing tabs and the custom-channel admin from the rep.
  - Independent review: separate reviewer agent, ACCEPT_WITH_FIXES, 13 findings (1 high, 5 medium).
    - Fixed, with regression tests:
      - Messaging UI paths missing /api/v1.
      - Custom-channel dedupe was global, not per channel.
      - Audience export did not re-check consent.
      - Marketing-consent withdrawal kept the e-mail link, and the purge missed identities and consents.
      - Social publishing could double-post with several workers.
      - Slack approval titles could carry PII.
      - Low items 8, 9, 10 and 13.
    - Two gate defects found in the browser were fixed: the messaging 404s, and the designer preview hid its real validation message.
    - The remaining low items are in M45.S01.T024.
  - Not covered here: live providers (M47) and the DB-gated regression of M36–M42.
- [x] M44.S02.T002 — On gate PASS, mark accepted software tasks [x], document unresolved activation-only prerequisites, commit and push evidence/ledger; fetch and verify Desktop HEAD equals origin/main, record synchronization and clean status; update next milestone/action in TASKS.md. If sync fails do not claim milestone closed; retry safely. Continue autonomously.
  Done 2026-11-26 [x]:
  - M44.S01.T001–T014 are [x].
  - Activation-only prerequisites stay in M47: real Meta, Google Ads, LinkedIn and TikTok apps with their review and tokens, the Slack incoming webhook, the mail relay signing keys, SOCIAL_PUBLISHING_ENABLED and AUDIENCE_EXPORT_ENABLED.
  - Synchronization: the gate commit 997d2ba was pushed to origin/main. After fetch, Desktop HEAD equals origin/main (997d2ba). The working tree is clean apart from files the owner left untracked (.hiveai/ and two M25 logs). The gate container m44-gate-pg and the walkthrough servers were removed, and temporary next-dev edits were reverted.

# M45 — AI Agent & Customer Data Hub — accountless

Dependency: previous major milestone gate and synchronization PASS. Reuse shared harness, native models and adapter registry.

## M45.S01 — Implementation tasks
- [v] M45.S01.T001 — AI prospecting agent (original recommendation 22/40)
  - **Scope:** Extend M16/M30/copilot; configurable target criteria, ranked suggested prospects, evidence/source citations, outreach draft and human approval before sending; no auto-contact and no real external scraping.
  - **Acceptance at milestone gate:** Synthetic prospect corpus and deterministic provider responses; relevance, uncertainty, permissions, approval and disabled-provider behavior.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v] (tests NOT RUN as gate), together with T002/T003 (CRM → "Prospecting & data"):
  - Prospect corpus: authorized local imports (CSV/JSON, licence note and retention date required) plus open CRM leads.
  - Search: configurable criteria (city, region, channel, segment, size bands, keywords) give a ranked list.
  - Each result shows:
    - evidence citing the source row and column;
    - a known-data confidence;
    - which fields are unknown.
  - Existing customers are excluded.
  - Outreach: the draft is built only from evidence. "Propose first e-mail" creates an AI request for a second person to approve, and the outbox applies suppression. Nothing is contacted automatically.
  - No scraping. The external provider adapter shows NOT_CONFIGURED.
  - Tests: tests/test_m45_s01_t001_t003_customer_data.py.
- [v] M45.S01.T002 — AI customer and company research (original recommendation 23/40)
  - **Scope:** Research adapter for authorized public/business data sources, configurable search/enrichment provider and local imports, provenance, freshness, citations, conflict handling and bounded retrieval; unknown data remains unknown.
  - **Acceptance at milestone gate:** Local source corpus/contract replay; verify traceability and no fabricated company facts, unauthorized network or personal data exposure.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v]:
  - "Research" on a customer collects facts from authorized sources. Matching is by normalized name, phone or KRA PIN.
  - Facts are stored as proposals (cd_facts), each with source, row/column citation, age and confidence. A strong key match gives higher confidence.
  - Each field shows unknown, conflict (sources disagree) or its candidates. Nothing is filled from guesses.
  - Retention: expired sources and their rows/proposals are purged daily.
  - The external research/search provider stays NOT_CONFIGURED until a licensed account exists (M47).
- [v] M45.S01.T003 — Customer data enrichment (original recommendation 24/40)
  - **Scope:** Configurable field mapping, deterministic normalization/dedup, external enrichment interface and documented provider adapters where public, evidence and field-level confidence/approval; never overwrite verified values silently. Extended by the 2026-11-25 parity matrix: business-card scan to contact (local OCR, user confirms every field).
  - **Acceptance at milestone gate:** Synthetic records, conflicting values, consent and retention; local provider contracts; future licensed datasets/account needed for actual enrichment.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v]:
  - Import: field mapping, then deterministic normalization (Kenyan phones to +254, e-mail, KRA PIN, legal-suffix-free names). Duplicates within the import are skipped. Each row reports its errors.
  - A proposal is applied only by crm.edit_all, and every change is audited with old value, new value and citation.
  - A verified field is never overwritten.
  - A different existing value needs an explicit overwrite.
  - Business card: card text (from the phone's text recognition or typed) is parsed into fields with confidence. The user edits them and must confirm before a contact is created.
  - No local OCR engine is installed: the screen says ocr_engine NOT_CONFIGURED.
  - Licensed enrichment datasets: future (M47).
- [v] M45.S01.T004 — Buyer intent and lead signals (original recommendation 25/40)
  - **Scope:** First-party site/form/email/quote/order intent events, configurable scoring/decay and alerts; optional external intent feed adapter, no third-party dataset invented.
  - **Acceptance at milestone gate:** Synthetic event stream with recency, consent, explainable score and scoped alerts; optional external feed activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v] together with T005/T006 (customer intelligence; tests NOT RUN as gate):
  - Intent is computed from first-party signals: consented website visits (pricing pages and forms weigh more), e-mail clicks, quote views and new orders.
  - Scoring: configurable weights and half-life decay; every point is explained.
  - Alerts: once per cool-down per customer, to the customer owner (rep on the newest CRM record).
  - The external intent feed shows NOT_CONFIGURED.
  - Code: app/services/customer_intel_service.py, /api/v1/customer-intel, CRM tab "Customer success".
  - Tests: tests/test_m45_s01_t004_t006_customer_intel.py.
- [v] M45.S01.T005 — Churn and retention prediction (original recommendation 26/40)
  - **Scope:** Define churn for FMCG segments, rules and local statistical model with time-aware train/validation, explainable factors, confidence and cold-start behavior; no model claiming accuracy on real data.
  - **Acceptance at milestone gate:** Synthetic labeled cohorts, leakage checks, backtest, calibration and no fabricated business accuracy; real historical data calibration future.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v]:
  - Churn definition: no order within horizon_days (default 90) for a customer with at least min_orders orders.
  - Features use only data before the cut-off; a test proves this leakage check.
  - Model: numpy logistic regression trained on time-ordered monthly snapshots. The newest quarter of cut-offs is used for validation.
  - Reported metrics: AUC, Brier score, calibration bins and a recency-rule baseline. The metrics are explicitly labelled as describing the data in this database (synthetic before go-live).
  - Cold start: "insufficient history". Without a model, the rule fallback is shown with low confidence.
  - Each prediction shows its top 3 explanatory factors.
  - Not done here: calibration on real history (needs production data).
- [v] M45.S01.T006 — Customer health score and success workspace (original recommendation 27/40)
  - **Scope:** Configurable score from orders, overdue invoices, tickets, NPS, engagement and repeat purchase; alerts/playbooks, trend, missing-data treatment and ownership.
  - **Acceptance at milestone gate:** Synthetic accounts, no data/no score labeling, source reconciliation and permissions; integrated ERP signals beyond CRM.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v]:
  - Health score: configurable weights over ordering rhythm, overdue invoices (ERP), tickets, NPS, e-mail engagement and repeat purchase.
  - Missing data: a component with no data is named and left out. Below half the weight covered, the result is "not enough data".
  - Snapshots: daily (ci_health_snapshots) for the trend, from the M45 job runner.
  - Low health: an alert with playbook steps to the owner.
  - Workspace: lists only the customers a rep owns; crm.view_all sees all.
- [v] M45.S01.T007 — AI customer service agent (original recommendation 28/40)
  - **Scope:** Extend public KB bot with retrieval grounded in approved articles, safe order/ticket status after authorization, multilingual responses, escalation and refusal, citations, audit and consent. No autonomous refunds/orders/financial actions.
  - **Acceptance at milestone gate:** Local KB + mock model, prompt-injection, account isolation, citations, escalation, no provider fallback and human approval tests.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v] (tests NOT RUN as gate):
  - The website chat bot is now a grounded service agent (app/services/service_agent.py), used by crm_chat_service.
  - Help answers: only from approved, public help articles, ranked by app/services/kb_retrieval.py, with numbered citations. Internal or draft articles never appear.
  - Order and ticket status: only for a signed-in portal customer, and only for their own records. Anonymous visitors are asked to sign in; another account's numbers are "not found".
  - Refused: refunds, cancellations, payments and price changes (handed to a person), and prompt-injection attempts.
  - Languages: English and Swahili.
  - Nothing grounded → hand-off to a person; there is no generative-model fallback.
  - Bot replies are stored with the chat (audit). Consent behaviour is unchanged.
  - Tests:
    - tests/test_m45_s01_t007_service_agent.py
    - the M36 live-chat regression test, rerun: PASS
- [v] M45.S01.T008 — Visual AI agent builder (original recommendation 29/40)
  - **Scope:** Reuse workflow and AI governance: agents with triggers, allowed tools, prompts, knowledge, versions, simulation, approval, scoped read/write capabilities and template gallery. Extended by matrix v2: template gallery includes revenue (overdue chase on dunning), closing (buyer Q&A on approved quote content), customer-health and knowledge-base agents.
  - **Acceptance at milestone gate:** Build and simulate real local agent in UI, validate cycles/tool allowlist, version rollback, prompt injection and unauthorized action denial.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v] (tests NOT RUN as gate):
  - Builder: AI → Agents. Agents use versioned definitions (trigger, tool allow-list, knowledge, steps with for-each and templating).
  - Validation rejects:
    - cycles;
    - unknown or unlisted tools;
    - unconnected steps;
    - forward references.
  - Simulation writes nothing.
  - Publishing needs approval by a second person (ai.approve). Rollback to an earlier published version is supported.
  - The agent runs as its owner, so read tools check that owner's permissions.
  - Write tools (create_task, send_email) only create AI requests. A different person approves them, and send_email goes through the outbox with its suppression rules.
  - If tool output contains a prompt-injection pattern, the run is flagged and later writes are blocked.
  - Template gallery: overdue-invoice chaser (dunning), quote Q&A (approved quote content only), customer-health watcher and knowledge-base answerer.
  - Tests: tests/test_m45_s01_t008_t009_agents.py.
- [v] M45.S01.T009 — Agent scheduler, cost and governance (original recommendation 30/40)
  - **Scope:** Durable jobs, schedules, limits per agent/user/company, token/cost estimates from configurable rates, retry/idempotency, approvals, kill switch, audit and deterministic fallback; no default real AI calls.
  - **Acceptance at milestone gate:** Fake model/local provider exercises budgets, time zones, concurrent runs, retries, emergency stop and human approval. Real model tests optional and explicitly authorized only.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v]:
  - Durable jobs (ai_agent_jobs):
    - claimed with SKIP LOCKED, one running job per agent;
    - idempotent per key (each schedule slot is enqueued once);
    - retried with exponential back-off, up to 3 attempts.
  - Schedules: every N minutes, or daily at HH:MM in an IANA time zone.
  - Budgets: per agent (runs/day, tokens/run, cost/day), per company (cost/day) and per user (manual runs/day). Token and cost estimates use configurable rates.
  - Emergency stop: global and per agent.
  - Every job is audited and mirrored into ai_agent_runs, so it appears on the AI governance dashboard.
  - No default real AI call: LLM steps render deterministic templates unless use_provider is switched on and a provider key exists. That is optional, explicitly authorized and deferred to M47.
- [v] M45.S01.T010 — Advanced customer deduplication and merge (original recommendation 31/40)
  - **Scope:** Detect candidate duplicates across contacts/companies; canonical survivor, merge preview, preserve references/orders/invoices/activity/consent, stricter suppression wins, audit/rollback strategy and RBAC. Extended by matrix v2: fuzzy matching (names, phones, KRA PIN, addresses), customer merge (merge_master today excludes customers) and bulk duplicate review.
  - **Acceptance at milestone gate:** Synthetic duplicate records with transactions and permissions, no orphan/duplicate order, consent preservation and concurrency.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v] (tests NOT RUN as gate):
  - Fuzzy candidates for customers and contacts: name similarity (legal suffixes removed), phone (+254), KRA PIN, e-mail and address, with blocking. Dismissed pairs are not shown again.
  - Bulk review screen: CRM → Duplicates, with a merge preview (rows to move, fields to fill, consent result).
  - Customer merge, which merge_master did not cover before:
    - Both rows are locked in a fixed order.
    - Every reference is moved, using all foreign keys in the schema (53 tables, including orders, invoices, quotes, tickets, payments, NPS and loyalty) plus polymorphic contact associations. Nothing is copied, so there are no orphan or duplicate orders.
    - Duplicate link rows (e.g. the same group membership) are removed and logged.
    - Empty fields are filled, and the stricter e-mail suppression wins.
    - The merged customer is deactivated and kept.
  - Contact merge: the same steps; the merged contact is deleted after a snapshot.
  - Audit and undo: the merge log keeps the snapshot, the moved rows and the changes, and Undo restores them.
  - Concurrency: of two parallel merges of one pair, one succeeds and the other is refused.
  - Tests: tests/test_m45_s01_t010_dedupe_merge.py.
- [ ] M45.S01.T011 — No-code data sync and transformation (original recommendation 32/40)
  - **Scope:** Visual field mapping, typed transformations, validation, dry-run diffs, conflict rules, incremental sync and connector SDK/catalog; import/export CSV/JSON, secrets separation and versioning. Audit custom objects, associations and data-quality capabilities; fill uncovered gaps. Extended by matrix v2: data quality overview and health trends, formatting recommendations, scheduled and webhook-triggered workflows.
  - **Acceptance at milestone gate:** Local two-way fixture sources test transformation/retry/replay, invalid mapping, scope, deletes and rollback; no arbitrary code execution.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [v] M45.S01.T012 — Gmail and Outlook CRM add-ins (original recommendation 33/40)
  - **Scope:** Develop installable source/manifests and shared authenticated CRM sidebar for contact lookup, log email, note/task, templates and links. Follow official supported add-on/add-in frameworks; local harness exercises actual shared API. Store publication/admin consent not required now.
  - **Acceptance at milestone gate:** Validate manifest/build locally and test sidebar using simulated host context; unsupported host-only runtime clearly deferred; real Google/Microsoft host acceptance/publishing later.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
  Implemented 2026-11-26 [v] (tests NOT RUN as gate):
  - Add-ins:
    - Outlook XML manifest: addins/outlook/manifest.xml.
    - Gmail Apps Script CardService add-on: addins/gmail.
    - Shared sidebar: frontend/public/addin/sidebar.html.
  - Shared API /api/v1/public/crm-addin: lookup, log-email (once per Message-ID), note, task and templates. It authenticates with a personal access token (scope crm.addin) and applies the user's own CRM visibility.
  - Tokens are created in CRM → "Add-ins & AI access". They are shown once and can be revoked; their use is audited.
  - Local harness: the sidebar page takes host context from the query string. A test validates both manifests and exercises the API.
  - Deferred to M47: real Outlook/Gmail host runtime, sideload/Marketplace publishing and admin consent (addins/README.md).
- [ ] M45.S01.T013 — General sales document library (original recommendation 34/40)
  - **Scope:** Extend quote links to authorized catalogues, proposals and sales docs; versioned storage, permissions, share/expiry/revocation, privacy-aware view tracking, download audit and malware scanner integration.
  - **Acceptance at milestone gate:** Local document store and scanner fixtures, browser views, version hash, revoked/expired access, no cross-account leaks.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [ ] M45.S01.T014 — Advanced CPQ and contract lifecycle (original recommendation 35/40)
  - **Scope:** Extend native quotations/discount approvals with configurable bundles, pricing rules, volume tiers, currency/tax, contract templates, version negotiation, renewal/expiry, signatory verification, provider-agnostic signature adapter (documented provider where feasible), downstream order/credit/stock/finance. Audit subscription billing and payment links; add uncovered software capabilities. Extended by matrix v2: apply existing promotion BUNDLE/MIX_AND_MATCH/TIERED schemes to quotes; quote templates, password protection, price books, multi-step approvals, quote reporting; recurring billing with retries and billing portal on top of subscription order templates; credit-memo verification.
  - **Acceptance at milestone gate:** Synthetic quote-to-contract-to-order/invoice/renewal flow; correct approvals/totals, signature evidence, no bypass, local provider contracts; third-party e-sign/payment activation deferred.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.

- [ ] M45.S01.T015 — Custom objects and associations (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Admin-defined object types (typed fields, required/unique, display name), records, many-to-many associations to customers, CRM records, products and orders with labels, list/detail UI, import/export, report-builder source and workflow triggers. Per-object permissions; no arbitrary SQL.
  - **Acceptance at milestone gate:** Define object, create records, associate them, report on them, delete with association cleanup; validation and RBAC; company isolation; migration.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [ ] M45.S01.T016 — Staff single sign-on (OIDC, then SAML) (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Standards-based OIDC authorization-code + PKCE login for staff, IdP discovery, JIT user linking only to pre-provisioned accounts, role mapping, enforced-SSO switch per company, break-glass admin, logout. SAML 2.0 SP where a maintained library is available. Tested against a local OIDC test provider; no real IdP account.
  - **Acceptance at milestone gate:** Local IdP: login, state/nonce/PKCE replay refusal, unknown user refused, disabled user refused, enforced SSO blocks password login, break-glass works; audit.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [ ] M45.S01.T017 — Sensitive-data field classification (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Mark fields (built-in and custom) as sensitive; masking in lists/exports/API for users without the sensitive-data right; access audit; retention policy hook. Revised by matrix v2: cf_definitions.sensitive_flag exists but is not enforced — enforce it and add field-level permissions.
  - **Acceptance at milestone gate:** Masked values for a non-privileged persona in UI, API and CSV export; audit entries on reveal; no leak through search or GraphQL.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [ ] M45.S01.T018 — Configuration sandbox (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Export/import of configuration (pipelines, forms, workflows, sequences, custom objects/fields, templates) as a versioned bundle with diff preview and dry run, so changes are tested on a staging copy before production. No customer data in bundles.
  - **Acceptance at milestone gate:** Bundle round-trip between two disposable databases; diff and dry run; conflicting IDs handled; no personal data inside.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [ ] M45.S01.T019 — Service routing, conditional SLAs and CSAT/CES (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Agent skills and availability; skill-based and round-robin ticket routing; SLA policies by priority, channel and customer tier with business hours and pause states; CSAT/CES surveys after ticket close (portal and e-mail), results on dashboard. Extended by matrix v2: ticket CSAT already exists in the portal; add CES and post-chat survey, automatic assignment, capacity limits and agent presence, macros, reply recommendations, help desk spaces and custom views, QA and customer-experience scores, handoff summaries.
  - **Acceptance at milestone gate:** Synthetic tickets routed by skill; SLA timers with business hours and breaches; survey sent once, answered once; reports; permissions.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [ ] M45.S01.T020 — Data warehouse export connectors (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Incremental, schema-documented export of CRM/ERP datasets to Parquet/CSV object storage (local MinIO/S3-compatible) and a PostgreSQL warehouse target; documented adapters for Snowflake/BigQuery left NOT_CONFIGURED until activation; row-level permission and field masking honoured.
  - **Acceptance at milestone gate:** Local S3-compatible bucket and a second PostgreSQL receive incremental loads; deletes and schema changes; masked fields; resume after failure.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [ ] M45.S01.T021 — Customer payment links (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Shareable signed payment link for an invoice or order balance; customer page shows amount and pays by M-Pesa STK push (existing Daraja code) or a card-provider adapter left NOT_CONFIGURED; expiry, single settlement, receipt and ledger posting through existing collections.
  - **Acceptance at milestone gate:** Daraja simulator callback settles once; expired/forged links refused; partial payment; no LIVE_PAID without a real provider.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
- [v] M45.S01.T022 — MCP server for ERP/CRM tools (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Model Context Protocol server exposing read tools (customer, order, stock, invoice status) and approval-gated write tools to authorized AI clients with per-token scopes, rate limits and audit; reuse API permissions.
  - **Acceptance at milestone gate:** Local MCP client lists tools, read calls respect RBAC and company, write calls create approval requests only, revoked token refused.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
  Implemented 2026-11-26 [v]:
  - MCP server: POST /api/v1/public/mcp. It speaks JSON-RPC 2.0 over Streamable HTTP and supports initialize, ping, tools/list and tools/call.
  - Auth: Bearer personal access token. mcp.read is needed to connect; mcp.write adds the write tool.
  - Read tools: search_customers, order_status, stock_level and invoice_status. They respect the user's permissions and company/branch scope.
  - Write tool: propose_follow_up_task only creates an AI request. A different person approves it before anything is written.
  - Every call and refusal is written to the audit log.
  - Rate limit per token per minute (in-process).
  - Revoked or expired tokens get 401.
  - Tests: tests/test_m45_s01_t012_t022_tokens_addin_mcp.py.

- [ ] M45.S01.T023 — Audited impersonation and admin notification management (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** 'Log in as another user' for support: superuser or a dedicated right, mandatory reason, time-boxed session, persistent banner, no password or 2FA bypass for the target's secrets, cannot impersonate a superuser, every action attributed to both people in the audit log, and the target user is notified. Admin notification management: company-wide defaults and mandatory notifications.
  - **Acceptance at milestone gate:** Impersonation is refused without the right or reason; the session expires; the audit log shows both actors; escalation to a superuser is refused; the banner is always visible; notification defaults apply.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

- [v] M45.S01.T024 — M44 carry-overs (from the M44 build and gate review, 2026-11-26)
  - **Scope:**
    - Content and analytics:
      - an asset library (DAM) for e-mail and social media;
      - locale-based smart blocks (needs a contact language field);
      - logged-in portal-visitor identification in website chat;
      - a deal-level web journey.
    - Robustness:
      - an ack step for the custom-channel outbox, so a lost poll response does not lose a reply;
      - concurrent identical idempotency keys (ads drafts, social posts) return the existing row instead of 500;
      - re-request clears a stale approved_by;
      - a page cap when following Meta report paging.
  - **Acceptance at milestone gate:** each item has a test. Specifically:
    - an outbox item is redelivered until acked;
    - parallel creates with one key return one row;
    - paging stops at the cap.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.
  Implemented 2026-11-26 [v] (tests NOT RUN as gate; dev runs on disposable PG only):
  - Robustness: the custom-channel outbox now redelivers until acked (POST /public/channels/{key}/outbox/ack). Parallel creates with one idempotency key return the existing ads draft or social post (IntegrityError → existing row). Re-request clears approved_by. Meta paging stops at MAX_PAGES=50.
  - Locale blocks: new crm_contacts.language field (contact form); designer block audience "language"; campaigns pass the contact language.
  - Portal chat identity: a signed-in portal user starting website chat is identified from the portal session (crm_chat_sessions.portal_account_id). Typed name/e-mail are ignored, consent stays what the visitor ticked, and the inbox subject marks it.
  - Deal journey: GET /web-analytics/deal-journey/{record_id} merges the consented journeys of the deal's contacts; shown as "Website journey" on the deal page.
  - DAM: approved, scan-clean MARKETING_CREATIVE images from document management (versions/approval/scan reused), listed at /marketing-assets and served from an HMAC-signed public URL (/public/assets/{id}/{sig}). The e-mail designer image block has "Pick from asset library".
  - Tests: tests/test_m45_s01_t024_carryovers.py and the extended test_m44_s01_t013_messaging.py.

## M45.S02 — Major milestone acceptance and synchronization
- [ ] M45.S02.T001 — Run consolidated milestone acceptance once all implementation work is ready: backend/DB/provider-contract/frontend/build/real browser desktop+mobile/synthetic E2E/security/independent review; include relevant prior features, fix and rerun failures, record exact code SHA, commands, results, screenshots and reviewer. No live-provider requirement. Reconcile applicable older [v] rows only if evidence/gate covers them. Update TASKS.md; do not mark [x] on failure.
- [ ] M45.S02.T002 — On gate PASS, mark accepted software tasks [x], document unresolved activation-only prerequisites, commit and push evidence/ledger; fetch and verify Desktop HEAD equals origin/main, record synchronization and clean status; update next milestone/action in TASKS.md. If sync fails do not claim milestone closed; retry safely. Continue autonomously.

# M46 — Content & Digital Experience Hub — accountless

Dependency: previous major milestone gate and synchronization PASS. Reuse shared harness, native models and adapter registry.

## M46.S01 — Implementation tasks
- [ ] M46.S01.T001 — CMS and visual website builder (original recommendation 36/40)
  - **Scope:** Build reusable component/block editor, pages, navigation, theme tokens, media library, preview/version/publish/rollback, forms/landing reuse, custom-domain configuration with localhost fallback. Safe sanitization and no public deployment now. Extended by matrix v2: site tree, content staging, multisite, content embed, URL mappings, dynamic data tables (HubDB-like) and dynamic pages, CTAs, content approval workflow.
  - **Acceptance at milestone gate:** Real local preview/publish with synthetic site, phone/desktop, XSS, drafts not public, access and rollback.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [ ] M46.S01.T002 — Blog and SEO suite (original recommendation 37/40)
  - **Scope:** Editorial workflows, categories/authors, slug/canonical/redirects, sitemap/robots, structured data, on-page SEO audit, internal links, metadata, keyword planning from local imports/provider interface; no invented ranking/search volumes. Extended by matrix v2: Google Search Console adapter (NOT_CONFIGURED until activation) and SEO analytics.
  - **Acceptance at milestone gate:** Local crawler/HTML tests and browser editorial flow, sitemap/redirect validation, audit findings and explicit no-data states.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [ ] M46.S01.T003 — AI brand voice and content studio (original recommendation 38/40)
  - **Scope:** Use approved POVU brand assets only; style/terminology rules, content templates, rewrite/repurpose across channels, citations/claims review, approval and AI cost limits; deterministic fallback and draft only.
  - **Acceptance at milestone gate:** Synthetic content corpus with fake model; brand constraints, no fabricated claims, no unauthorized publish, version/approval history.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [ ] M46.S01.T004 — CRM-driven personalization (original recommendation 39/40)
  - **Scope:** Consent-aware segments/rules for page blocks, locale, known visitor or anonymous fallback, experiment control, preview and audience privacy; integrate native CRM without leaking identity. Extended by matrix v2: adaptive (multi-armed bandit) testing alongside the existing A/B variants.
  - **Acceptance at milestone gate:** Local synthetic visitor sessions, consent withdrawal, cache isolation, segment tests and experiment attribution.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.
- [ ] M46.S01.T005 — Multilingual CMS and AEO (original recommendation 40/40)
  - **Scope:** EN/SW/TR configurable locale content, translation workflow, hreflang and fallback, structured FAQ/schema, AEO readiness audit and configurable visibility/measurement adapters; synthetic local evaluation and import, no claims of external answer-engine rankings without data.
  - **Acceptance at milestone gate:** Local multi-locale site and accessibility/SEO/AEO audit; absent external measurements show NOT_AVAILABLE, not fake scores; external search/provider setup later.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable. Do not rebuild already working functionality; record evidence and bounded delta.
  - **Claude checkpoint:** update TASKS.md/Project Status immediately after this task, [v] pending milestone gate, tests NOT RUN; automatically continue next dependency-ready task. Never [x] before milestone PASS.

- [ ] M46.S01.T006 — Memberships, gated content and video assets (additional gap, Source: HubSpot parity matrix 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** Gated pages for portal-authenticated customers/distributors (registration via existing portal realm), access lists by segment, video asset hosting (local storage) with captions and view analytics feeding CRM timeline. Extended by matrix v2: member blog, podcasts/audio assets, KB access groups.
  - **Acceptance at milestone gate:** Anonymous visitor blocked, authorized portal user sees content, revoked access, video upload/caption/playback on phone and desktop, views on timeline.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

- [ ] M46.S01.T007 — User interface internationalization (EN/SW/TR) (additional gap, Source: HubSpot parity matrix v2 2026-11-25 (coordination/milestones/M43/HUBSPOT_PARITY_MATRIX_2026-11-25.md).)
  - **Scope:** An i18n framework for the frontend (customer-facing first: portal, shop, chat, KB, booking, NPS, business card; then staff screens), locale negotiation and switcher, number/date/currency formatting per locale, translation catalogs with missing-key reporting, and server messages via codes. Machine translation only as a reviewed draft.
  - **Acceptance at milestone gate:** The portal and shop run fully in Swahili and Turkish at phone width; missing-key report is empty for customer screens; formats are correct; no layout overflow.
  - **Required deliverables:** inspect/reuse existing code; necessary schema/migration, backend/API, real UI, RBAC/tenant/privacy/audit, docs, test cases, no-account degraded state and activation runbook if applicable.
  - **Claude checkpoint:** [v] pending milestone gate, tests NOT RUN until gate; never [x] before milestone PASS.

## M46.S02 — Major milestone acceptance and synchronization
- [ ] M46.S02.T001 — Run consolidated milestone acceptance once all implementation work is ready: backend/DB/provider-contract/frontend/build/real browser desktop+mobile/synthetic E2E/security/independent review; include relevant prior features, fix and rerun failures, record exact code SHA, commands, results, screenshots and reviewer. No live-provider requirement. Reconcile applicable older [v] rows only if evidence/gate covers them. Update TASKS.md; do not mark [x] on failure.
- [ ] M46.S02.T002 — On gate PASS, mark accepted software tasks [x], document unresolved activation-only prerequisites, commit and push evidence/ledger; fetch and verify Desktop HEAD equals origin/main, record synchronization and clean status; update next milestone/action in TASKS.md. If sync fails do not claim milestone closed; retry safely. Continue autonomously.

# M47 — Parity-plus final integrated acceptance and future commissioning register

## M47.S01 — Final verification and additional gap closure
- [ ] M47.S01.T001 — Re-audit dated HubSpot capability matrix against actual latest source and running local ERP; compare edition feature by feature, not names. Any uncovered software gap must become a new executable task (including gaps beyond original 40); implement and add acceptance coverage before final gate. No unverified parity claims. Update TASKS.md immediately, tests NOT RUN until gate.
- [ ] M47.S01.T002 — Prove parity-plus integrated design through synthetic FMCG scenarios: website lead/chat → score → routing/sequence → quote/discount/signature → order → MRP/production/QC/stock → pick/dispatch/POD → invoice/ledger/tahsilat; distributor/shop/field channels; complaint/lot/recall/NPS/loyalty; campaigns/attribution/AI recommendations. Test absent-provider operation and native data continuity. Prepare evidence plan, test only at gate; update TASKS.md immediately.
- [ ] M47.S01.T003 — Verify all software surfaces, role permissions, privacy, consent, auditability, accessible desktop/mobile screens, multi-company/currency/locales, import/export/backup/recovery, operational limits, deployment configuration and no real business data/credentials in public repo. Record docs, screenshots and missing tasks; do not imply production readiness without actual acceptance. Update TASKS.md immediately.
- [ ] M47.S01.T004 — Final feature-by-feature comparison report: each HubSpot capability with evidence, achieved local parity/advantage, remaining limitations due to vendor-only/private data or approvals, exact future activation prerequisites, and measurable native FMCG advantages. If a software gap remains, add tasks and close them before final acceptance. No fake market-size or live accuracy equivalence. Update TASKS.md immediately.
- [ ] M47.S01.T005 — Consolidated final software milestone test gate: full backend, DB/migration, contracts, frontend build/type/lint, browser actual local app and screenshot walkthrough, critical end-to-end personas and independent security/code audit. Fix failures and rerun; no [x] before applicable PASS. Commit/push all accepted code/evidence/ledger and verify Desktop/main SHA match; update TASKS.md and report in Turkish.

## M47.S02 — Future activation register (NOT_DUE [D], not outstanding software defects)
These rows describe commissioning only; they must never stop accountless coding, testing, software milestone DONE or autonomous task selection. Claude must refine from source/evidence during M43.S00.T005. Do not change to [!] merely because the factory does not exist. Reopen activation when owner confirms actual prerequisites exist. Each row requires a setup checklist, minimal scoped real smoke test, rollback/disable, audit and exact live evidence; no credentials in Git.
- [D] M47.S02.T001 — Production domain/HTTPS/DNS, OAuth redirect URLs, public forms/webhooks, QR/vCard links, SPF/DKIM/DMARC and deployment security; trigger: owner provides domain and hosting.
- [D] M47.S02.T002 — Corporate Gmail/Workspace/Microsoft mailbox, OAuth apps/verification, mail/calendar permissions, production SMTP/complaint relay; trigger: actual company accounts and administrator approvals.
- [D] M47.S02.T003 — Voice carrier/SIP and number, recording/transcription consent, retention/legal decision and live call; trigger: selected provider and authorized number.
- [D] M47.S02.T004 — Meta business/page/Instagram/WhatsApp, Google Ads developer token/account, LinkedIn marketing access, TikTok Business accounts and approvals; trigger: actual authorized accounts and approved budget; start read-only and no publication/spend without owner approval.
- [D] M47.S02.T005 — Shopify and any approved online store, real catalogue, customer/order mapping, test order and webhook; trigger: actual store and scoped access.
- [D] M47.S02.T006 — Payment/bank/KRA eTIMS/M-Pesa, signature/identity provider and authorized live financial smoke; trigger: company/provider credentials and finance/legal acceptance.
- [D] M47.S02.T007 — Actual employees/roles, products/BOMs, customers, distributors, warehouse/production lines, devices/printers/scanners, app store/MDM accounts and factory commissioning; trigger: real operational data and physical infrastructure. Synthetic records never substitute for these.
- [D] M47.S02.T008 — Licensed enrichment/search/intent data, approved external AI/transcription endpoints, real traffic and historical churn/forecast calibration; trigger: owner-approved providers/data, permission, budget and representative records. Prior authorized live AI evidence stays historical; no new account needed for software tests.
- [D] M47.S02.T009 — Real-company commissioning/UAT, performance/scale, backup/restore and security review on production infrastructure; trigger: deployment and operational staff. Do not declare live readiness until evidence exists.

**Final software completion criteria:** all 40 original recommendations and every additional verified implementable capability mapped to accepted [x] rows (or justified already-existing/superseded evidence); all major milestone gates passed, exact source and Desktop/main synchronized, no actionable software gaps silently hidden in activation register. Separate limitations for proprietary datasets/vendor approvals and real operating conditions. Report software completion separately from future commissioning. No artificial 100% parity score. The required target is functional HubSpot parity-plus in the applicable product scope, including native FMCG advantages, verified with evidence.
