# M20.S01.T001 — Strict Audit: Existing MPS Domain Mapping

**Repository:** `Sekiph82/fmcg-erp-system`  
**Branch:** `main`  
**Canonical tracker:** `/TASKS.md`  
**Audit owner:** ChatGPT / H!veAI Auditor  
**Execution owner for next step:** Claude  
**Tracker ownership:** ChatGPT only for this workflow. Claude MUST NOT edit `TASKS.md`.

---

## 1. Audit Purpose

This audit establishes the real current state of the Master Production Scheduling domain before implementation begins. The active canonical task is:

`M20.S01.T001 — Map existing MPS models/APIs/UI/services to enterprise requirements`

M20 must extend the current implementation. It must not replace working MPS, MRP, production, planning, BOM, inventory, or frontend architecture.

This audit is source-based. Historical test results are supporting evidence only. Claude must run current focused verification before claiming completion.

---

## 2. Existing MPS Capability Map

### 2.1 Persistence / domain model

Current source: `backend/app/models/mps.py`

Existing persistent MPS entities:

- `MPSPlan`
  - planning horizon
  - planning mode: MANUAL / ASSISTED / AUTO / AI
  - capacity mode: FINITE / INFINITE
  - lifecycle: DRAFT / APPROVED / RELEASED / CLOSED
  - MRP run linkage
  - counters
  - created/approved user linkage
  - approval/release timestamps
- `MPSLine`
  - product and MRP-result linkage
  - period boundaries
  - confirmed demand / forecast / safety stock / net requirement decomposition
  - planned quantity / batch size / batch count
  - work-center and schedule dates
  - required hours
  - campaign linkage
  - feasibility status
  - manual lock
  - production-order linkage
- `MPSCampaign`
- `MPSCapacitySlot`
- `MPSWhatIfScenario`
- `MPSAIRecommendation`

Existing enums already anticipate enterprise concepts including `MATERIAL_SHORT`, `INFEASIBLE`, `ON_HOLD`, SPLIT/MERGE/SHIFT_ADD, AI recommendation review and persistent what-if scenarios.

### 2.2 MRP / demand foundation

Current sources:

- `backend/app/models/mrp.py`
- `backend/app/services/mrp_service.py`
- `backend/app/api/v1/endpoints/mrp.py`

MRP already contains meaningful upstream inputs required by M20:

- confirmed sales-order demand
- demand forecasting
- safety stock
- current product/material stock
- incoming purchase orders
- incoming production supply
- BOM explosion
- net requirement calculation
- material shortage flags/exceptions
- procurement/production suggestions
- forecast override audit trail

Therefore M20.S02 must couple MPS to the existing MRP truth rather than inventing another demand/supply engine.

### 2.3 MPS core orchestration

Current source: `backend/app/services/mps_service.py`

Existing operations:

- create/list/get plans
- create MPS lines from MRP results
- preserve manually locked lines while regenerating non-locked lines
- manual line override locking
- plan approval
- plan release into `ProductionOrder`
- dashboard KPI aggregation

### 2.4 Capacity scheduling

Current source: `backend/app/services/mps_capacity_service.py`

Implemented:

- FINITE and INFINITE modes
- planned quantity → required hours calculation
- daily capacity slots
- overload diagnostics
- heatmap aggregation
- reschedule suggestion

### 2.5 Campaign planning

Current source: `backend/app/services/mps_campaign_service.py`

Implemented:

- automated grouping
- campaign persistence
- line assignment
- sequence ordering
- estimated setup/changeover hours
- production/changeover efficiency metrics

### 2.6 What-if scenarios

Current source: `backend/app/services/mps_whatif_service.py`

Implemented:

- persistent scenarios
- immutable live-plan behavior during simulation
- DELAY / BATCH_SIZE / QTY_ADJUST / LINE_CHANGE / SPLIT handling
- service-level impact
- delayed-line count
- cost delta estimate

### 2.7 AI recommendations

Current source: `backend/app/services/mps_ai_service.py`

Implemented rule/data-driven agents:

- optimizer
- capacity risk
- late-delivery risk
- MRP material-shortage risk
- urgent unscheduled line risk
- recommendation persistence
- planner accept/reject state

Important: this is not proof of an autonomous optimizer. Accepted recommendations are not shown to automatically mutate the MPS plan, which is safer than silently applying AI decisions.

### 2.8 API

Current source: `backend/app/api/v1/endpoints/mps.py`

Existing surface includes:

- dashboard
- plan CRUD subset
- MRP generation
- capacity scheduling
- campaign grouping
- AI run/review
- approve/release
- line list/edit
- capacity heatmap/reschedule suggestion
- campaign list
- what-if create/list/detail

The MPS router is registered at `/api/v1/mps` through the central endpoint registry.

### 2.9 Frontend

Current sources include:

- `frontend/src/lib/mps.ts`
- `frontend/src/app/dashboard/mps/page.tsx`
- `frontend/src/app/dashboard/mps/planning-board/page.tsx`
- `frontend/src/app/dashboard/mps/capacity/page.tsx`
- `frontend/src/app/dashboard/mps/campaigns/page.tsx`
- `frontend/src/app/dashboard/mps/whatif/page.tsx`

Implemented screens:

- MPS dashboard
- planning board
- capacity heatmap
- campaign planning
- what-if simulator

Historical route-recovery work also confirms these are intended as real operational pages, not redirect stubs.

---

## 3. Strict Findings

### P1-M20-001 — MPS API bypasses real user identity and permission enforcement

**Severity:** P1  
**Files:**
- `backend/app/api/v1/endpoints/mps.py`
- compare with `backend/app/core/deps.py`

The MPS API currently declares:

```python
_SYSTEM_USER = uuid.UUID("00000000-0000-0000-0000-000000000001")

def _get_current_user_id() -> uuid.UUID:
    return _SYSTEM_USER
```

Create/approve/release/what-if/recommendation-review operations use this fixed UUID instead of the authenticated user.

The endpoints also do not use the established `get_current_user` / `require_permission(...)` authorization pattern.

Consequences:

1. actor attribution is false,
2. MPS privileged mutations are not protected at module/action level,
3. approval/release auditability is unreliable,
4. user foreign keys may point to a UUID that is not guaranteed to exist,
5. this contradicts repository-wide RBAC conventions.

**Required next-step behavior:** Claude must replace fixed-system-user mutation attribution with authenticated user identity and add consistent MPS permissions using the repository's existing RBAC pattern. Do not invent a second auth system.

Because MPS is currently an endpoint-registry route, not a `MODULE_DEFINITIONS` module, Claude must first inspect the dominant permission-seeding/module-registration pattern and choose the smallest architecture-consistent solution. If promoting `mps` into `MODULE_DEFINITIONS` is necessary to ensure seeded permissions, do so narrowly and test route uniqueness. Otherwise use an existing appropriate planning permission only if repository semantics clearly support it. Do not silently reuse unrelated permissions.

### P1-M20-002 — Release lifecycle guard contradicts its own contract

**Severity:** P1  
**File:** `backend/app/services/mps_service.py`

`release_mps_plan()` states:

```python
"""Release: create ProductionOrders for all FEASIBLE non-released lines."""
```

and raises the message:

```python
"Plan must be APPROVED before release"
```

but its condition allows both:

```python
MPSStatus.APPROVED, MPSStatus.DRAFT
```

Therefore a DRAFT plan can be released directly.

**Required:** release must require `APPROVED` unless an explicit, documented business rule in current repository proves otherwise. No such rule was established by this audit.

### P1-M20-003 — Release does not restrict creation to FEASIBLE lines

**Severity:** P1  
**File:** `backend/app/services/mps_service.py`

The release query filters:

- MPS id
- no production order yet
- planned quantity > 0

It does **not** filter `feasibility_status == FEASIBLE` despite the service contract and UI language saying it does.

Possible current result: PENDING, OVERLOADED, MATERIAL_SHORT, INFEASIBLE or ON_HOLD lines can produce production orders.

**Required:** only enterprise-eligible lines may release. For this task the minimum safe invariant is `FEASIBLE`. Claude should not invent bypass rules. If a legitimate override exists elsewhere, document it and implement explicit audited override rather than implicit release.

### P1-M20-004 — MPS line update can mutate workflow-controlled fields directly

**Severity:** P1/P2 boundary, treat as P1 for this task  
**Files:**
- `backend/app/schemas/mps.py`
- `backend/app/services/mps_service.py`

`MPSLineUpdate` exposes `feasibility_status` and `is_locked` to generic line PATCH. `update_mps_line()` blindly assigns every supplied field, then sets `is_locked=True`.

This permits a client to set an overloaded/material-short/infeasible line to FEASIBLE without running the authoritative feasibility processes.

**Required:** distinguish planner-editable fields from engine-controlled fields. Normal line edit must not be able to forge feasibility. If unlock functionality is needed, it should be explicit and permission/audit controlled rather than a generic PATCH field.

### P1-M20-005 — MRP run linkage is not strongly validated before MPS generation

**Severity:** P1/P2 boundary  
**Files:**
- `backend/app/services/mps_service.py`
- `backend/app/models/mrp.py`

`generate_mps_from_mrp()` queries MRP results using the requested run id, but the audit did not find enforcement that:

- the MRP run exists,
- it is `COMPLETED`,
- its warehouse/planning context is compatible with the MPS plan,
- plan `mrp_run_id` and request `mrp_run_id` are consistent by business rule.

The file imports `MRPRun` and `MRPRunStatus` but does not use them in this path.

**Required:** validate source-run existence and COMPLETED state now. Warehouse/context matching should be implemented only where existing fields make it deterministic; otherwise log as a bounded M20.S02 follow-up instead of inventing data.

### P2-M20-006 — Period proration can over/under-allocate net requirement

**Severity:** P2  
**File:** `backend/app/services/mps_service.py`

Current logic computes each period fraction from fixed `period_days / horizon`, including the last partial period. This can make total generated demand differ from the original MRP net requirement, particularly for partial final periods and the horizon boundary.

The loop also uses `while cursor < plan.end_date`, which deserves boundary tests for one-day and short horizons.

**Required for T001:** do not redesign demand phasing unless needed to make current invariants/test dataset coherent. Add tests that expose the current behavior and, if a small deterministic correction is safe, make total phased net requirement conserve the original MRP net requirement. Otherwise record precisely for M20.S02.

### P2-M20-007 — Capacity logic ignores important available source data

**Severity:** P2 / expected later-sprint work  
**File:** `backend/app/services/mps_capacity_service.py`

The current scheduler:

- uses a fixed `8h/day`, Mon-Sat calendar,
- assigns the first loaded work center when none is specified,
- treats `WorkCenter.capacity` as units/hour while explicitly not checking `capacity_uom`,
- does not use shift templates/resource calendars/downtime in available hours,
- does not prove product-routing compatibility for a selected work center.

This is consistent with why M20.S03 and M32 exist. Do not attempt a large APS rewrite inside T001.

**Required for T001:** add guardrails/tests around obvious unit/compatibility assumptions if they can be done narrowly; otherwise document them as confirmed M20.S03/M32 scope.

### P2-M20-008 — Campaign grouping is heuristic, not formula compatibility

**Severity:** P2 / later-sprint work  
**File:** `backend/app/services/mps_campaign_service.py`

Campaign family is based primarily on the first six characters of product code. The comment assumes this likely means same base formula. This is not a safe enterprise invariant.

Changeover is based on one setup-time value, not changeover matrix/formula/allergen/cleaning/CIP rules.

**Required for T001:** preserve existing feature, document heuristic nature, and create regression coverage. Do not replace it with the full M32 changeover engine here.

### P2-M20-009 — What-if service has declared change types not fully executed

**Severity:** P2  
**Files:**
- `backend/app/models/mps.py`
- `backend/app/services/mps_whatif_service.py`
- frontend what-if page

Enum contains `MERGE` and `SHIFT_ADD`; `_apply_change()` does not implement them. Frontend presents MERGE as a selectable change. SPLIT only halves the simulated quantity in one snapshot; it does not simulate a true second line. Capacity effects are not recalculated from the scheduling engine after LINE_CHANGE / SPLIT / SHIFT_ADD.

**Required for T001:** make unsupported scenario actions impossible to falsely present as computed behavior. Either implement a minimal correct simulation using existing primitives or remove/disable unsupported UI/API choices and explicitly defer full behavior to M20.S04/M32. Prefer truthfulness over pretend capability.

### P2-M20-010 — What-if KPI math is a proxy, not a full simulation

**Severity:** P2 / later-sprint scope  
**File:** `backend/app/services/mps_whatif_service.py`

Cost delta defaults to a `KES 1000/unit` proxy when no WC cost/capacity is available. Service level is based on planned end vs period end and does not recompute material or capacity feasibility.

**Required:** label/document estimates clearly and prevent UI wording from implying finite-capacity simulation when it is only proxy impact. Full scenario comparison belongs in M20.S04/M32.

### P2-M20-011 — MPS-specific focused regression suite was not established by repository search

**Severity:** P2  
**Area:** `backend/tests`, frontend E2E/unit tests

Historical full-suite passes exist, but repository search during this audit did not establish a dedicated current MPS service/API regression file covering lifecycle, permissions, feasibility release, MRP generation, capacity, campaigns and what-if invariants.

**Required:** add focused tests for every change made in this execution. T001 should leave a concrete MPS regression foundation, not rely only on unrelated global historical passes.

### P2-M20-012 — MPS migration provenance requires live/current verification

**Severity:** P2 / schema verification  

Historical MPS implementation notes said a migration was needed. Current model registry imports MPS models and the repository has extensive later Alembic history, but this GitHub source audit did not establish a clearly named dedicated MPS migration from filename search.

**Required:** Claude must inspect Alembic history locally (`alembic history`, search revisions for MPS table names) and report exactly which revision owns the six MPS tables. If current DB/model migration ownership is missing, create a proper migration only after proving it is genuinely absent. Do not autogenerate an unsafe duplicate migration.

---

## 4. Architecture Constraints for Claude

Claude must preserve all existing enterprise modules and patterns.

### Mandatory

- GitHub `main` is source-of-truth.
- Local workspace is only an execution workspace.
- Read `AGENTS.md`, `TASKS.md`, this audit, and the execution prompt before editing.
- `TASKS.md` is **READ ONLY** for Claude in this workflow.
- `TASKS_HISTORY.md` is **READ ONLY**.
- Do not resurrect `.hiveai/TASKS.md`, `.hiveai/EVENTS.jsonl`, or any deprecated tracker as active state even though the top of `AGENTS.md` still contains a contradictory legacy adapter paragraph. The bottom `AGENTS.md` H!veAI GitHub tracking contract and the user's explicit instruction govern this run.
- Do not remove current MPS pages or features.
- Do not rewrite MPS into a new architecture.
- Do not implement M21+ scope.
- Do not perform broad APS/M32 changes inside T001.
- Do not force-push, rebase shared history, use destructive clean/reset, or discard local user changes.

### Strong preference

T001 should produce:

1. exact source map,
2. focused tests,
3. narrow fixes for critical invariants discovered above,
4. a machine-reviewable Claude execution log,
5. one or more normal commits pushed to GitHub.

---

## 5. Definition of Done for Claude Execution

Claude's implementation is ready for ChatGPT audit only when all of the following are true:

- [ ] Local workspace safely synchronized against latest `origin/main` before changes.
- [ ] Starting GitHub SHA recorded in execution log.
- [ ] `TASKS.md` unchanged byte-for-byte by Claude.
- [ ] Fixed-system-user MPS mutation pattern removed.
- [ ] MPS endpoints require authentication and appropriate permissions.
- [ ] Release requires APPROVED state.
- [ ] Release only creates production orders for eligible/FEASIBLE lines.
- [ ] Normal line PATCH cannot forge engine-controlled feasibility state.
- [ ] MRP generation validates the source MRP run and completion state.
- [ ] Existing MPS dashboard/planning/capacity/campaign/what-if surfaces remain functional.
- [ ] Unsupported what-if actions are not falsely advertised as valid computation.
- [ ] Focused backend tests cover authorization/lifecycle/release/MRP-generation invariants.
- [ ] Relevant frontend type-check/build or focused UI validation passes.
- [ ] Migration ownership for all MPS tables is identified and logged; no duplicate migration created blindly.
- [ ] Broader P2 findings that properly belong to later M20 sprints are logged, not overbuilt.
- [ ] Implementation commit(s) pushed to GitHub.
- [ ] Claude execution log created at the exact required path and pushed to GitHub.
- [ ] Final response contains only GitHub-visible evidence: branch, commit SHA(s), changed files, tests, log URL, blockers.

ChatGPT will independently audit the resulting GitHub commits/log and only then update canonical `TASKS.md`.
