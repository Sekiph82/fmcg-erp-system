# Claude Work Order — M20.S01.T001 MPS Domain Reconciliation + Critical Invariant Hardening

## 0. Authority and communication contract

Repository: `https://github.com/Sekiph82/fmcg-erp-system`  
Tracked branch: `main`  
Local execution workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`  
Canonical tracker: `https://github.com/Sekiph82/fmcg-erp-system/blob/main/TASKS.md`  
Strict audit: `https://github.com/Sekiph82/fmcg-erp-system/blob/main/docs/hiveai/audits/M20_S01_T001_STRICT_AUDIT.md`

This is a GitHub-mediated workflow between ChatGPT (auditor/tracker owner) and Claude (builder).

### Non-negotiable tracker rule

**DO NOT EDIT `TASKS.md`.**  
**DO NOT EDIT `TASKS_HISTORY.md`.**  
Do not create or revive a competing tracker. ChatGPT will independently audit your GitHub work and update `TASKS.md` afterward.

The top of `AGENTS.md` contains legacy `.hiveai` adapter wording that conflicts with the current root-tracker contract. For this run, treat the following as authoritative:

1. the user's explicit instruction in this work order,
2. root `TASKS.md` as the only current tracker,
3. bottom `AGENTS.md` GitHub-tracking section,
4. `TASKS_HISTORY.md` as immutable history only.

Do **not** update `.hiveai/TASKS.md` or `.hiveai/EVENTS.jsonl`.

---

# 1. Mandatory pre-work synchronization

Before examining or changing implementation, synchronize the local workspace with GitHub safely.

Run from PowerShell or equivalent:

```powershell
cd C:\Users\sekip\Desktop\fmcg-erp-system
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
git fetch origin --prune
git rev-parse origin/main
git rev-list --left-right --count HEAD...origin/main
```

## Sync safety rules

### If the working tree is clean and local `main` is only behind `origin/main`

```powershell
git switch main
git pull --ff-only origin main
```

### If uncommitted local changes exist

- Do not delete, reset, clean, or overwrite them.
- Record `git status --short` in the execution log.
- Preserve them reversibly using a clearly named stash, for example:

```powershell
git stash push -u -m "claude-pre-sync-M20-S01-T001-<timestamp>"
```

- Do not drop the stash.
- Continue from synchronized `main` only after preservation.
- Record the stash name in the final log.

### If local commits are ahead/diverged from `origin/main`

- Do not rebase shared history.
- Do not force push.
- Do not hard-reset and lose the local state.
- Create a safety reference/branch pointing at the original local HEAD, record it, then base task work on latest `origin/main` in a clean task branch or safe fast-forward-compatible state.
- Never silently overwrite user work.

### Required pre-edit condition

Before editing, record:

- local starting SHA,
- `origin/main` starting SHA,
- active branch,
- whether a stash/safety branch was needed,
- confirmation that task work is based on latest GitHub `main`.

GitHub is source-of-truth; the local directory is an execution workspace.

---

# 2. Mandatory reading before code changes

Read in this order:

1. `AGENTS.md`
2. `TASKS.md` — READ ONLY
3. `docs/hiveai/audits/M20_S01_T001_STRICT_AUDIT.md`
4. this work order
5. relevant MPS/MRP/production/RBAC source and tests

At minimum inspect:

### MPS
- `backend/app/models/mps.py`
- `backend/app/schemas/mps.py`
- `backend/app/api/v1/endpoints/mps.py`
- `backend/app/services/mps_service.py`
- `backend/app/services/mps_capacity_service.py`
- `backend/app/services/mps_campaign_service.py`
- `backend/app/services/mps_whatif_service.py`
- `backend/app/services/mps_ai_service.py`
- `frontend/src/lib/mps.ts`
- `frontend/src/app/dashboard/mps/page.tsx`
- `frontend/src/app/dashboard/mps/planning-board/page.tsx`
- `frontend/src/app/dashboard/mps/capacity/page.tsx`
- `frontend/src/app/dashboard/mps/campaigns/page.tsx`
- `frontend/src/app/dashboard/mps/whatif/page.tsx`

### Upstream/downstream patterns
- `backend/app/core/deps.py`
- `backend/app/core/access_control.py`
- `backend/app/core/module_registry.py`
- `backend/app/api/v1/endpoints/mrp.py`
- `backend/app/models/mrp.py`
- `backend/app/services/mrp_service.py`
- `backend/app/models/production.py`
- `backend/app/models/production_advanced.py`
- existing audit logging patterns in analogous approval/release modules
- relevant permission seed logic/tests
- Alembic revisions that own MPS tables

Do not assume the audit is exhaustive. Verify every finding against the synchronized current source before changing it.

---

# 3. Task objective

Execute **M20.S01.T001** as a real domain reconciliation task, while fixing only the critical invariants that make the current MPS baseline unsafe or misleading.

The purpose is **not** to rebuild MPS or implement all M20 now.

The purpose is to leave MPS with:

- trustworthy actor identity,
- proper authorization,
- correct release lifecycle,
- correct release eligibility,
- protected engine-controlled feasibility state,
- validated MRP source run,
- honest what-if capability exposure,
- focused regression coverage,
- exact architecture/evidence log for ChatGPT's follow-up audit.

Preserve existing working MPS dashboard/planning-board/capacity/campaign/what-if features.

---

# 4. Findings to verify and remediate

## F1 — Fixed `_SYSTEM_USER` and missing MPS auth/RBAC

Current audit found `backend/app/api/v1/endpoints/mps.py` using a fixed UUID instead of authenticated user identity, with no normal MPS permission dependencies.

### Required

- Replace fixed user attribution with `get_current_user`.
- Apply permission checks consistently to read and mutation routes.
- Use the existing RBAC/module registry/permission seeding architecture.
- Do not invent a parallel auth system.

### Permission design requirement

Before editing, inspect how route-only endpoint modules receive permission codes and how module permissions are seeded.

Preferred semantic actions for MPS are likely to require at least:

- `view`
- `create`
- `edit`
- `approve`
- `release`
- possibly `calculate` / `simulate` / `ai`

Do not blindly create all of these if existing conventions dictate another shape. Choose the smallest internally consistent permission contract that protects:

- viewing plans/lines/capacity/campaigns/scenarios/recommendations,
- creating/generating/running calculations,
- editing planner overrides,
- approving,
- releasing,
- AI recommendation review.

If `mps` must be promoted to `MODULE_DEFINITIONS` to seed permissions correctly, do it narrowly and ensure `/mps` is not registered twice. Remove/adjust the old endpoint registration only if needed to avoid duplicate routes.

Add focused tests proving unauthorized/underprivileged operations fail and permitted operations pass.

## F2 — DRAFT plan can currently be released

The service message and business contract say the plan must be APPROVED, but current condition accepts DRAFT.

### Required

- `release_mps_plan()` must require `MPSStatus.APPROVED`.
- Add regression test proving DRAFT release is rejected.
- Add regression test proving APPROVED release can proceed subject to line eligibility and recipe/warehouse validity.

## F3 — Non-FEASIBLE lines currently qualify for production-order creation

The service docstring/UI say release creates orders for feasible lines, but the current query does not filter feasibility.

### Required

- Release only lines with `feasibility_status == FEASIBLE`.
- PENDING, OVERLOADED, MATERIAL_SHORT, INFEASIBLE and ON_HOLD must not create production orders through the normal release path.
- Return useful deterministic result counts so skipped/ineligible lines are visible.
- Preserve idempotency: already-linked lines must never create duplicate production orders.
- Add tests for mixed feasibility states.

Do not create a hidden bypass in this task. An override, if ever needed, belongs to an explicit audited workflow.

## F4 — Generic line PATCH can forge feasibility

`MPSLineUpdate` currently exposes engine-controlled `feasibility_status` and `is_locked`, and service assignment is generic.

### Required

- Normal planner edit must not directly set engine-controlled feasibility state.
- Normal planner edit must not arbitrarily unlock a line if that undermines regeneration protection.
- Preserve planner-editable operational fields such as quantity, work center, dates, priority, remarks as appropriate.
- A manual edit should continue to lock the line unless a dedicated, permission-controlled unlock operation already exists or is narrowly added with clear audit semantics.
- Add tests that attempted feasibility forgery is rejected/ignored according to the chosen API contract.

Do not broadly redesign all MPS state management.

## F5 — Source MRP run validation

`generate_mps_from_mrp()` currently uses requested results but does not establish source-run completion.

### Required now

- MRP run must exist.
- MRP run must be `COMPLETED`.
- Generated MPS lines must come from that run only.
- MPS plan must remain DRAFT for generation.
- Preserve locked lines behavior.
- Store/confirm the plan's MRP run linkage consistently.

### Conditional

If the current data model provides an unambiguous warehouse/plant compatibility rule, enforce it. If it does not, document the missing data contract in the execution log for `M20.S02`; do not invent relational fields in this task.

## F6 — Period phasing conservation

Audit found the fixed period-fraction algorithm may not conserve total MRP net requirement on partial horizons.

### Required

- Write a deterministic focused test for daily/weekly/monthly phasing and partial final period.
- Ensure the sum of generated `net_requirement_qty` per MRP result matches the original net requirement within accepted decimal rounding tolerance.
- Use actual period day counts for the last partial period or an equivalent deterministic conservation strategy.
- Avoid introducing complex forecast phasing not supported by current data.

## F7 — Honest what-if capability

Declared change types and UI choices are ahead of actual simulation behavior.

### Required

- Verify each current `MPSChangeType` against `_apply_change()`.
- Do not present MERGE/SHIFT_ADD or any other unsupported change as if it is computed.
- Choose one of these safe outcomes:
  1. implement the missing behavior correctly using existing MPS primitives and test it, **only if narrowly feasible**, or
  2. reject unsupported types in backend validation and hide/disable them in UI, with comments/log notes that they belong to later M20/M32 scope.
- SPLIT must not claim to be a true two-line finite-capacity simulation if it only modifies one snapshot. Either make the semantics explicit or defer it honestly.
- Label proxy/estimated cost impact as estimated where appropriate.

Do not build a full APS simulation engine here.

## F8 — Migration ownership

### Required investigation

Locally inspect Alembic history and revision contents for:

- `mps_plans`
- `mps_lines`
- `mps_campaigns`
- `mps_capacity_slots`
- `mps_whatif_scenarios`
- `mps_ai_recommendations`

Commands may include:

```powershell
cd backend
python -m alembic heads
python -m alembic history
rg -n "mps_plans|mps_lines|mps_campaigns|mps_capacity_slots|mps_whatif_scenarios|mps_ai_recommendations" alembic app
```

If migration ownership exists, record exact revision(s) in the log and make no duplicate migration.

If tables genuinely lack migration ownership, add a migration only after proving absence and reviewing current head/branch structure. Never blindly autogenerate against an unknown local DB state.

## F9 — Capacity and campaign limitations

Audit confirmed these are real later-sprint gaps:

- fixed 8h Mon-Sat capacity calendar,
- `capacity_uom` not validated,
- first work center fallback,
- no routing compatibility proof,
- no shift/resource-calendar/downtime integration,
- campaign family based on product-code prefix,
- no full changeover/CIP/allergen matrix.

### Required for this task

- Do not expand into M20.S03/M32 wholesale.
- Add tests/guards only where necessary to prevent clearly invalid behavior caused by your T001 changes.
- Record these as confirmed follow-up findings in the Claude log.

---

# 5. Audit trail expectations

MPS approve/release and AI recommendation review are business-critical state changes.

Inspect existing repository audit-event patterns. If MPS currently lacks audit logging for these critical actions, add the smallest architecture-consistent audit events/log calls needed for:

- plan creation if normal convention requires it,
- plan approval,
- plan release,
- manual line override,
- AI recommendation accept/reject.

Do not build a new audit framework. Reuse the existing one.

If adding new `AuditEvent` enum values requires migration or broad blast radius, use the existing generic audit pattern supported by the repository, or document why a follow-up is required. Do not fake audit evidence.

---

# 6. Tests and verification

Create a focused MPS regression suite under the repository's existing test conventions.

At minimum prove:

1. authenticated permission enforcement for read/mutation classes,
2. real user id is used for created/approved/released/reviewed attribution,
3. DRAFT cannot release,
4. APPROVED can release,
5. only FEASIBLE lines create production orders,
6. already-released lines are idempotently skipped,
7. no-active-recipe lines are skipped predictably,
8. generic line edit cannot forge feasibility,
9. MRP generation rejects missing/non-COMPLETED run,
10. phasing conserves net requirement,
11. locked lines are preserved on regeneration,
12. unsupported what-if types are rejected/hidden or correctly implemented,
13. existing capacity/campaign/what-if read paths still function under authentication.

Run the narrow tests first, then the strongest practical regression available.

Recommended verification, adjusted to repository tooling actually present:

```powershell
cd C:\Users\sekip\Desktop\fmcg-erp-system\backend
python -m pytest <focused MPS test paths> -q
python -m pytest -q
python -m alembic heads
```

Frontend:

```powershell
cd C:\Users\sekip\Desktop\fmcg-erp-system\frontend
npm run type-check
npm run build
```

If full suites cannot run because of an environment dependency, do not claim PASS. Record exact command, failure reason, and what narrower evidence passed.

Do not modify tests merely to weaken assertions and make failures disappear.

---

# 7. Scope boundaries

## In scope

- M20.S01.T001 source mapping
- critical MPS identity/RBAC/lifecycle/release integrity fixes from this audit
- focused MPS tests
- small API/schema/frontend corrections required to keep capability truthful
- migration ownership verification
- implementation/evidence documentation in the required Claude log

## Out of scope for this execution

Do NOT fully implement:

- M20.S02 complete demand/supply coupling roadmap
- M20.S03 shift/resource-calendar/CIP/changeover optimization
- M20.S04 full scenario KPI engine
- M21 fluid-to-unit BOM work
- M22 work-order lifecycle redesign
- M23 shop-floor expansion
- M24 material-flow redesign
- M32 APS rewrite
- unrelated modules/refactors

When you discover adjacent gaps, log them with file/line evidence instead of expanding scope.

---

# 8. Git discipline

- No force push.
- No rebase of shared history.
- No destructive `git reset --hard` on user work.
- No `git clean -fd` against user workspace.
- No broad formatting/refactor commits.
- Never modify `TASKS.md`.
- Never modify `TASKS_HISTORY.md`.

Before commit:

```powershell
git status --short
git diff -- TASKS.md TASKS_HISTORY.md
```

The diff for both tracker files must be empty.

Commit implementation with a clear message, e.g.:

```text
fix(mps): harden domain reconciliation invariants
```

Push the implementation commit to GitHub.

---

# 9. Mandatory Claude execution log

After implementation/tests are complete and the implementation commit has been pushed, create:

`docs/hiveai/claude-logs/M20_S01_T001_CLAUDE_EXECUTION_LOG.md`

This log is the handoff from Claude to ChatGPT and must be sufficiently detailed for an independent audit.

## Required log structure

```markdown
# M20.S01.T001 Claude Execution Log

## Run identity
- Date/time
- Local workspace
- GitHub repository
- Branch
- Starting local SHA
- Starting origin/main SHA
- Sync method
- Safety stash/branch, if any

## Instructions read
- AGENTS.md
- TASKS.md (read-only)
- strict audit URL/path
- execution prompt URL/path

## Pre-change findings
- Exact findings confirmed/not confirmed
- Additional findings with severity

## Changes made
For each changed file:
- path
- why
- behavior before
- behavior after

## Database / migration ownership
- alembic heads
- exact revision(s) owning MPS tables
- migrations added, if any, with justification

## Commands executed
Chronological list of meaningful commands.

## Tests / verification
For every command:
- exact command
- PASS/FAIL/BLOCKED
- counts / important output
- failure reason if not passing

## Scope not implemented
List later-sprint findings intentionally deferred.

## Tracker integrity
- TASKS.md changed: NO
- TASKS_HISTORY.md changed: NO
- deprecated .hiveai tracker files changed: NO

## Git evidence
- implementation commit SHA
- implementation commit URL
- files in implementation commit
- final branch
- push result

## Blockers / risks
- remaining blockers
- assumptions made

## Handoff to ChatGPT
- what ChatGPT should audit next
- suggested tracker status only as prose; DO NOT edit tracker
```

Commit this log in a second commit, for example:

```text
docs(hiveai): record M20 S01 T001 Claude execution
```

Push it to GitHub.

The log commit should reference the implementation commit SHA.

---

# 10. Final response contract

At the end, do not dump local-file chatter. Report GitHub-visible results only:

- synchronization outcome,
- implementation commit SHA + GitHub URL,
- execution-log commit SHA + GitHub URL,
- execution-log file URL,
- tests passed/failed/blocked,
- any blocker,
- explicit statement: `TASKS.md was not modified.`

Do not claim the task accepted/Done. ChatGPT is the auditor and tracker owner and will decide that after reviewing your GitHub commits and log.
