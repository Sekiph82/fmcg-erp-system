# fmcg-erp-system — Canonical H!veAI Task Ledger

This root `TASKS.md` is the single authoritative current project-status tracker consumed by H!veAI for `Sekiph82/fmcg-erp-system`.

The previous detailed tracker remains preserved as immutable/reference evidence in `TASKS_HISTORY.md`. Historical Done states remain accepted for migration purposes. `PLANS.md` is architecture/strategy reference only.

---

## Project Status

- **Current Milestone:** M20 — Master Production Scheduling
- **Current Sprint:** M20.S01 — Reconciled Remaining Scope
- **Current Task:** M20.S01.T001 — Verify and close remaining MPS gaps from M00 reconciliation
- **Current Task Status:** READY
- **Next Task/Action:** Begin M20 only against the bounded PARTIAL items identified by M00; do not rebuild capabilities already present.
- **Required Actor:** BUILDER
- **Tracking Repository:** Sekiph82/fmcg-erp-system
- **Tracking Branch:** main
- **M00 Gate:** COMPLETE — source-level audit/reconciliation complete; runtime/provider/live-DB findings are explicitly carried forward below.

## Status Legend

- `[x]` DONE — task/audit completed
- `[~]` IN_PROGRESS — active work
- `[ ]` PLANNED — planned but not started
- `[!]` BLOCKED — external dependency/credential/environment/decision required
- `[-]` SUPERSEDED — retained history replaced by later work
- `[P]` PARTIAL — capability exists but bounded scope remains
- `[D]` DEFERRED — intentionally postponed

## Reconciliation Classification

- `ALREADY_DONE` — repository evidence substantially satisfies the intended capability
- `PARTIAL` — substantive implementation exists but remaining gaps are identified
- `MISSING` — no substantive implementation established
- `SUPERSEDED` — replaced by later architecture
- `NOT_APPLICABLE` — intentionally outside project scope

---

# M00 — Governance & Repository Baseline

**Status: DONE**

M00 reconciled historical accepted state, current source structure, repository history, tests/CI evidence, M01-M19 baseline domains and M20-M35 enhancement scope. It was an audit/reconciliation milestone, not a feature-remediation milestone. No existing production code was rewritten merely to make an audit green.

## M00.S01 — Canonical Tracker Migration & Historical Reclassification

- [x] M00.S01.T001 — Preserve previous canonical tracker as `TASKS_HISTORY.md`
- [x] M00.S01.T002 — Establish root `TASKS.md` as canonical H!veAI ledger
- [x] M00.S01.T003 — Establish repository/current-plan comparison framework
- [x] M00.S01.T004 — Inventory/migrate historical TASK-001 through TASK-027 families
- [x] M00.S01.T005 — Preserve Manual/Help/Push/Local-Staging/Data-Cleanup/blocked/manual families

## M00.S02 — Repository Capability Inventory

- [x] M00.S02.T001 — Backend architecture/module inventory
- [x] M00.S02.T002 — Frontend routes/pages/components inventory
- [x] M00.S02.T003 — Database models/migrations/schema inventory
- [x] M00.S02.T004 — API/router/service inventory
- [x] M00.S02.T005 — Jobs/queues/schedulers/event mechanisms inventory
- [x] M00.S02.T006 — CSV/import/export/reporting inventory
- [x] M00.S02.T007 — Integration provider/capability inventory
- [x] M00.S02.T008 — Tests/CI/Docker/deployment/environment inventory
- [x] M00.S02.T009 — Documentation/reference inventory

### Inventory conclusions

- FastAPI + async SQLAlchemy/Alembic backend and Next.js App Router frontend are broad, modular and production-oriented.
- Repository contains large model/API/service/UI coverage across manufacturing, inventory/WMS, procurement, sales, finance, HR, utilities, quality, maintenance, AI and integrations.
- CI/test history includes successful backend suites up to 482/482, frontend type-check/build, Playwright 52/52 smoke, route/action-card audits and Docker validation. These are historical evidence, not a claim that M00 re-ran the suites.
- External-provider/live-environment readiness remains distinct from source implementation readiness.

## M00.S03 — Existing-System Audit M01-M19

- [x] **M00.S03.T001 — M01 Platform / Infrastructure — PARTIAL**
  - ALREADY_DONE: modular API/router architecture, async DB/Alembic discipline, Docker dev/prod topology, CI, health/readiness/metrics, centralized config, workspace shell, approval workflow, custom fields, chatter/activity, import/report/help infrastructure.
  - PARTIAL: document binary storage/upload pipeline, always-running event dispatch worker proof, live migration ownership verification, deliberately deferred local staging.

- [x] **M00.S03.T002 — M02 Authentication / RBAC — PARTIAL**
  - ALREADY_DONE: cookie JWT auth, bcrypt, JTI/logout revocation, login lockout, audit events, password policy, TOTP/email/SMS 2FA, recovery codes, role/permission model, broad AccessScope model, backend permission/scope helpers and frontend permission/scope gating.
  - PARTIAL: refresh-token rotation/inactivity lifecycle not established; user-wide already-issued-session revocation semantics not proven end-to-end; privileged-role mandatory 2FA/live tenant isolation/CSRF posture require deployment-level verification.

- [x] **M00.S03.T003 — M03 Master Data — PARTIAL**
  - ALREADY_DONE: company/organizational structures, reusable custom fields/values/validation/layout/workflow rules, bulk import framework, audit/permission infrastructure and broad entity registries.
  - PARTIAL: cross-master duplicate/merge/version/effective-date governance is inconsistent by entity; enterprise-wide master-data stewardship and live referential-integrity validation remain audit/remediation targets.

- [x] **M00.S03.T004 — M04 Product / Material / Supplier Master — ALREADY_DONE**
  - Products, materials, suppliers and warehouses have models/API/UI/import paths; product editing and guarded deletion exist; bulk CSV support and FMCG-specific seeded catalogs/formulation references exist.
  - Future enterprise enhancements must extend, not replace, these masters.

- [x] **M00.S03.T005 — M05 Warehouse & Inventory — PARTIAL**
  - ALREADY_DONE: lots/stock/movements, warehouses, WMS zones/locations, cycle counts, shelf-life/FEFO features, trace events, demand/MRP support and operational UI.
  - PARTIAL: M33-level license-plate/GS1 depth, reservation/allocation orchestration, advanced putaway/replenishment/wave execution and end-to-end live transaction integrity require reconciliation/hardening.

- [x] **M00.S03.T006 — M06 Procurement — PARTIAL**
  - ALREADY_DONE: procurement workspace, suppliers, PR/PO/RFQ/deliveries, blanket/reorder concepts, procurement suggestions, subcontracting, supplier portal, invoice matching and landed-cost-related surfaces.
  - PARTIAL: M34 strategic sourcing/tender/split-award depth, supplier governance analytics and fully verified three-way-match/landed-cost accounting chain remain enhancement work.

- [x] **M00.S03.T007 — M07 Sales / Distributor Operations — PARTIAL**
  - ALREADY_DONE: sales orders, customers, invoices, quotes, shipments, collections/returns, pricing, van/field/distributor/secondary sales, commissions, recurring billing, loyalty and customer analytics/NPS surfaces.
  - PARTIAL: live provider/payment/tax dependencies and full order-to-cash transaction/accounting verification remain environment-dependent.

- [x] **M00.S03.T008 — M08 Production Core — PARTIAL**
  - ALREADY_DONE: advanced production models/APIs/UI for work orders, scheduling, batch lots, labor/shifts, routing, work centers, time tracking, OEE, downtime, waste/yield and execution/shop-floor surfaces.
  - PARTIAL: M22-M24 enterprise workflow depth, strict state-transition/transaction-integrity verification and cross-module material/QC/finance closure remain enhancement/hardening work.

- [x] **M00.S03.T009 — M09 Recipes / BOM — PARTIAL**
  - ALREADY_DONE: recipe and BOM masters, BOM types/lifecycle, BOM items/process parameters, CSV import, draft constraints and manufacturing UI/API coverage.
  - PARTIAL: M21 fluid-to-unit conversion profiles, nested/multi-output governance, yield/loss/spillage and effective-date/version semantics require focused reconciliation.

- [x] **M00.S03.T010 — M10 Quality — PARTIAL**
  - ALREADY_DONE: QC parameters/inspections, QMS surfaces, HACCP PDCA/audit scheduling, allergen/compliance features, complaint/recall domain, quality UI and cross-module utility/QC links.
  - PARTIAL: M27/M35 configurable gate enforcement, sampling/AQL/SPC breadth, CAPA/NCR/deviation closure semantics and live hold/release transaction enforcement require hardening.

- [x] **M00.S03.T011 — M11 Maintenance — PARTIAL**
  - ALREADY_DONE: asset register, breakdowns, PM plans/work orders, predictive maintenance, spare parts, MTBF/MTTR/downtime reporting and utility-alarm-to-maintenance integration.
  - PARTIAL: M29 production-schedule/OEE/calibration/predictive feedback loop and runtime validation remain.

- [x] **M00.S03.T012 — M12 Utilities — ALREADY_DONE**
  - Electricity, water/soft-water, steam/boiler, compressed air, solar, chemical treatment, assets/devices/readings/transactions, alarms/anomaly detection, KPI/reporting and cross-module integration are substantively implemented.
  - Provider/device telemetry realism remains deployment work, not a missing ERP module.

- [x] **M00.S03.T013 — M13 Finance / Costing — PARTIAL**
  - ALREADY_DONE: accounting/GL structures, chart of accounts/cost centers/fiscal periods, cashbook/receivables/budget, bank reconciliation/API surfaces, fixed assets, payroll, expenses/contracts, production costing and tax/eTIMS integration surfaces.
  - PARTIAL: live bank/eTIMS/provider verification, full landed-cost posting chain and live-DB posting/reconciliation controls remain.

- [x] **M00.S03.T014 — M14 HR / Operator / Shift — PARTIAL**
  - ALREADY_DONE: employees, attendance, leave, payroll, shifts, recruitment/ESS, appraisals/training, timesheets/expenses and production labor/operator concepts.
  - PARTIAL: M26 qualification/operator-machine intelligence depth and production-skill enforcement require enhancement.

- [x] **M00.S03.T015 — M15 Reporting / Analytics — ALREADY_DONE**
  - Report Builder, notification center, dashboards/KPIs, module reports, analytics and scheduled/report infrastructure are substantive.
  - Individual report correctness remains subject to domain transaction-quality tests.

- [x] **M00.S03.T016 — M16 AI — PARTIAL**
  - ALREADY_DONE: Anthropic/OpenAI/Gemini provider architecture, auto-detection/fallback, local Holt-Winters forecasting, AI models/services and module-specific recommendations/agents.
  - PARTIAL: real-key/live-provider acceptance, M30 decision/simulation governance, confidence/explainability, autonomy/risk tiers and outcome-learning loop remain.

- [x] **M00.S03.T017 — M17 Integrations — PARTIAL**
  - ALREADY_DONE: capability registry, M-Pesa, WhatsApp, eTIMS, AI and webhook/event implementations.
  - PARTIAL/BLOCKED: IoT/CRM/e-commerce/GraphQL remain stub-classified; bank API is simulated; physical printer execution is stub-only; live provider credentials are external blockers.

- [x] **M00.S03.T018 — M18 Kenya Localization — PARTIAL**
  - ALREADY_DONE: Kenya go-live/admin documentation, KRA/eTIMS surfaces, M-Pesa, Kenya payroll/tax-related UI, Turkey→Kenya logistics/customs workflow and localization-oriented training.
  - PARTIAL/BLOCKED: live KRA/eTIMS/M-Pesa/provider credentials and production acceptance cannot be proven from repository source alone.

- [x] **M00.S03.T019 — M19 Security / Deployment / Hardening — PARTIAL**
  - ALREADY_DONE: production config guards, restricted CORS, request timeout, Docker production topology, Redis auth, migration advisory lock, dependency/compile/import/migration/pytest/type-check/build CI and substantial security tests.
  - PARTIAL: live production penetration/isolation checks, session-lifecycle gaps from M02, provider secret deployment, staging/live DB migration rehearsal and residual repository anomaly cleanup remain.

## M00.S04 — M20-M35 Existing-vs-Planned Reconciliation

All enhancement milestones were compared against current source/history. None should be rebuilt from zero.

- [x] **M00.S04.T001 — M20 Master Production Scheduling — PARTIAL**
  - Existing MPS engine includes capacity scheduling, campaigns, what-if simulation, AI agents and dedicated planning-board/capacity/campaign/what-if UI. Remaining work: validate demand/material/capacity coupling, approval/release semantics and production-grade scenario persistence/metrics.
- [x] **M00.S04.T002 — M21 Advanced BOM / Fluid-to-Unit — PARTIAL**
  - Existing BOM/recipe lifecycle is strong. Remaining: explicit bulk-fluid→pack conversion profiles, yield/loss/spillage, nested/multi-output and effective-date/version governance.
- [x] **M00.S04.T003 — M22 Production Order / Work Order — PARTIAL**
  - Existing work-order/routing/work-center/execution architecture present. Remaining: enterprise split/merge/backorder/rework/subcontracting dependency/state integrity.
- [x] **M00.S04.T004 — M23 Shop Floor Execution — PARTIAL**
  - Existing shop-floor/execution UI and production tracking present. Remaining: operator/tablet UX hardening, offline/mobile justification, strict QC gates and execution transaction tests.
- [x] **M00.S04.T005 — M24 Material Flow — PARTIAL**
  - Material-flow/inventory/production linkage exists. Remaining: staged WIP/issue/consume/return/FG receipt orchestration, reservation/pick-list semantics and genealogy closure.
- [x] **M00.S04.T006 — M25 Cross-Border / Landed Cost — PARTIAL**
  - Turkey→Kenya logistics/customs and landed-cost surfaces exist. Remaining: in-transit ownership/valuation and fully verified accounting allocation/posting.
- [x] **M00.S04.T007 — M26 Machine & Operator Intelligence — PARTIAL**
  - Machine/operator/performance/OEE/labor concepts exist. Remaining: qualification enforcement, richer runtime/operator cost intelligence and anomaly feedback.
- [x] **M00.S04.T008 — M27 Quality Gates — PARTIAL**
  - Quality/QMS/HACCP/inspection infrastructure exists. Remaining: configurable mandatory gate engine tied transactionally to receive/release/production/dispatch.
- [x] **M00.S04.T009 — M28 Full Traceability — PARTIAL**
  - Lot trace events, shelf-life and recall/complaint domain exist. Remaining: complete forward/backward genealogy, packaging/pallet hierarchy and recall execution proof.
- [x] **M00.S04.T010 — M29 Maintenance / OEE Upgrade — PARTIAL**
  - Maintenance/OEE foundation is substantive. Remaining: calibration, production scheduling coupling and predictive closed loop.
- [x] **M00.S04.T011 — M30 AI Decision & Simulation — PARTIAL**
  - AI/forecast/agent/scenario foundations exist. Remaining: governed observe→decide→simulate→approve→execute→learn lifecycle with explainability/rollback/outcome tracking.
- [x] **M00.S04.T012 — M31 API / Event Architecture — PARTIAL**
  - API portal and persistent webhook/event/subscription/delivery/retry/dead-letter concepts exist. Remaining: prove always-running dispatch, partner credential/OAuth/API-key governance, idempotency and observability end-to-end.
- [x] **M00.S04.T013 — M32 Advanced Production Planning — PARTIAL**
  - MPS/MRP/capacity/scenario/planning surfaces exist. Remaining: finite-capacity constraint engine across changeover/CIP/tank/utility/QC/material, freeze horizons and KPI validation.
- [x] **M00.S04.T014 — M33 Warehouse / Inventory Enterprise Upgrade — PARTIAL**
  - WMS/FEFO/shelf-life/cycle-count/traceability foundations exist. Remaining: license plates, GS1 execution depth, advanced allocation/putaway/replenishment/waves and cross-module transaction proof.
- [x] **M00.S04.T015 — M34 Strategic Procurement Upgrade — PARTIAL**
  - PR/PO/RFQ/supplier/portal/suggestions/subcontracting/invoice-match foundations exist. Remaining: tender/blanket/split-award governance, supplier scorecard depth and fully verified three-way-match/landed-cost chain.
- [x] **M00.S04.T016 — M35 QC / QA Enterprise Upgrade — PARTIAL**
  - QC/QMS/HACCP/allergen/complaint/recall foundations exist. Remaining: unified specs/QCP/sampling/AQL/SPC, NCR/CAPA/deviation, COA/retain sample, audits/change-control/training dependency enforcement.

## M00.S05 — Strict Pre-Enhancement Full System Audit

The strict audit was completed as a **repository/source/history audit**. It did not fabricate runtime results. Items requiring live DB, credentials, devices or production provider access are recorded as findings rather than falsely marked as runtime-verified.

- [x] M00.S05.T001 — Full backend architecture audit
- [x] M00.S05.T002 — Full frontend architecture audit
- [x] M00.S05.T003 — Database/schema/migration integrity audit
- [x] M00.S05.T004 — API contracts/routes/service-boundary audit
- [x] M00.S05.T005 — Authentication/RBAC/security audit
- [x] M00.S05.T006 — Master-data integrity audit
- [x] M00.S05.T007 — Warehouse/inventory transaction-integrity audit
- [x] M00.S05.T008 — Procurement workflow audit
- [x] M00.S05.T009 — Sales/distributor/order-to-cash audit
- [x] M00.S05.T010 — Production/BOM/planning/execution audit
- [x] M00.S05.T011 — QC/QA/traceability audit
- [x] M00.S05.T012 — Maintenance/utilities/asset integration audit
- [x] M00.S05.T013 — Finance/costing/accounting audit
- [x] M00.S05.T014 — HR/operator/shift/payroll integration audit
- [x] M00.S05.T015 — AI grounding/safety/explainability/execution audit
- [x] M00.S05.T016 — External integrations/provider-readiness audit
- [x] M00.S05.T017 — CSV/template/import/export/report audit
- [x] M00.S05.T018 — Jobs/queues/events/retry/DLQ/idempotency audit
- [x] M00.S05.T019 — Tests/CI/deployment/observability audit
- [x] M00.S05.T020 — P0/P1/P2/P3 finding register and remediation plan

### Strict Audit Finding Register

#### P0 — release-blocking source-proven defects

- **None established by this source-level M00 audit.** This is not equivalent to a penetration test or live production certification.

#### P1 — must be closed or explicitly accepted before production-critical rollout

1. **AUTH-SESSION-001:** implement/verify inactivity timeout and refresh-token rotation; access-token-only 8-hour session model is insufficiently reconciled with configured refresh/inactivity settings.
2. **AUTH-REVOKE-002:** prove user-wide revocation of already-issued sessions end-to-end, not only per-token logout blocklisting.
3. **SEC-TENANT-003:** execute live-DB cross-user/cross-supplier/cross-scope isolation tests for portal and scoped records.
4. **EVENT-WORKER-004:** prove persistent webhook/event delivery has an always-running production dispatch path with retry/DLQ/idempotency behavior under failure.
5. **DB-MIGRATION-005:** run fresh-DB and representative-upgrade migration rehearsals against production-like PostgreSQL and verify a single Alembic head/schema ownership.
6. **DOC-STORAGE-006:** complete/verify binary document storage/upload adapter before treating Documents/KB/e-sign as fully production-complete.
7. **FIN-LIVE-007:** verify eTIMS/bank/M-Pesa/landed-cost posting/reconciliation with real provider sandboxes/live credentials before financial go-live.

#### P2 — enterprise enhancement/hardening

- CSRF posture review against final deployment/origin policy.
- Privileged-role mandatory 2FA policy decision/enforcement.
- Advanced M21-M35 capabilities identified as PARTIAL in S04.
- IoT/CRM/e-commerce/GraphQL stub-provider decisions and physical printer execution.
- Device/utility telemetry realism and offline/shop-floor behavior where required.
- Remaining master-data version/merge/effective-date governance.

#### P3 — cleanup/operational polish

- Classify/remove residual repository anomalies such as `backend/=2.9.0` if still present.
- Continue documentation/manual refresh only when functional changes warrant it.
- Keep local staging deferred until owner chooses to provision it.

### M00 acceptance decision

- M00 audit/reconciliation itself is **DONE**.
- No source-proven P0 finding blocks roadmap continuation.
- P1 findings are now explicit backlog gates and must not be silently forgotten.
- M20-M35 are unlocked for implementation, but each milestone must consume the reconciliation above and avoid duplicate/replacement work.
- Live/provider/environment checks must be recorded as such when they become executable; historical tests are evidence, not a substitute for future production acceptance.

---

# M20-M35 Reconciled Roadmap

- [P] **M20 Master Production Scheduling** — existing MPS engine; close bounded demand/material/capacity/approval/scenario gaps.
- [P] **M21 Advanced BOM / Fluid-to-Unit** — extend current BOM/recipe with conversion/yield/version depth.
- [P] **M22 Production Order / Work Order** — harden current work-order lifecycle/dependencies/rework/subcontracting.
- [P] **M23 Shop Floor Execution** — harden operator execution/QC/offline/mobile/transaction integrity.
- [P] **M24 Material Flow** — close staging/WIP/reservation/consumption/receipt/genealogy orchestration.
- [P] **M25 Cross-Border / Landed Cost** — close in-transit valuation/allocation/accounting verification.
- [P] **M26 Machine & Operator Intelligence** — close qualifications/operator-machine intelligence/cost/anomaly depth.
- [P] **M27 Quality Gates** — implement transactional configurable receive/process/release/dispatch gates.
- [P] **M28 Full Traceability** — close full genealogy/pack hierarchy/recall execution.
- [P] **M29 Maintenance / OEE Upgrade** — close calibration/scheduling/predictive loop.
- [P] **M30 AI Decision & Simulation** — add governed decision lifecycle/explainability/rollback/outcome learning.
- [P] **M31 API / Event Architecture** — close worker/partner auth/idempotency/observability.
- [P] **M32 Advanced Production Planning** — close finite-capacity multi-constraint/freeze-horizon/KPI depth.
- [P] **M33 Warehouse / Inventory Enterprise Upgrade** — close license-plate/GS1/allocation/putaway/replenishment/wave depth.
- [P] **M34 Strategic Procurement Upgrade** — close tender/split-award/scorecard/three-way-match governance.
- [P] **M35 QC / QA Enterprise Upgrade** — close unified QCP/sampling/SPC/NCR/CAPA/COA/audit/change-control depth.

---

# Preserved Historical Deferred / Blocked Work

- [D] Historical TASK-012 — Local staging environment setup.
- [P] Historical TASK-019 — Document Management / Knowledge Base / E-Sign hardening; binary storage and live migration verification remain.
- [!] Historical TASK-020 — Integration credentials/provider enablement; external/manual blockers remain where applicable.
- [P] Historical TASK-021 — Push/checkpoint/staging verification family; preserve historical semantics.
- [P] Historical TASK-022 — Data cleanup/local production-data normalization; do not run destructive cleanup silently.

---

# H!veAI Current State

- **M00:** COMPLETE
- **Completed in this audit sequence:** M00.S03 M01-M19, M00.S04 M20-M35 reconciliation, M00.S05 strict source-level audit and finding register.
- **Current roadmap position:** M20 Master Production Scheduling.
- **Immediate rule:** implement only reconciled remaining scope; preserve existing working MPS and enterprise modules.
- **Standing production gates:** P1 findings AUTH-SESSION-001 through FIN-LIVE-007.
