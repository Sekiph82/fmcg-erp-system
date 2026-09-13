# M20-S01-T001 V01 — MPS Domain Reconciliation + Critical Invariant Hardening

You are Claude, the implementer/test runner. ChatGPT is the independent auditor and sole tracker writer.

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Local workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`
Canonical tracker: root `TASKS.md` (READ ONLY for Claude)
Matching evidence log: `coordination/sessions/M20-S01-T001/CLAUDE_LOG_V01.md`

Mandatory audit criteria:
`coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V01.md`

Historical pre-session source audit for context:
`docs/hiveai/audits/M20_S01_T001_STRICT_AUDIT.md`

## 0. Safe synchronization first

Before edits:

1. Confirm repository, `main`, remotes and `git status --short`.
2. Fetch `origin` and safely reconcile local `main` with `origin/main`.
3. GitHub `main` is current-state authority.
4. Preserve every pre-existing tracked/untracked owner/local change. Do not reset, clean, restore or overwrite it merely for cleanliness.
5. Never force push.
6. If local work prevents safe reconciliation, stop as `BLOCKED` and record the exact state in the log.

Read before implementation:

1. `AGENTS.md`
2. root `TASKS.md` (READ ONLY)
3. `coordination/AUDIT_POLICY.md`
4. `coordination/AUDIT_INDEX.md`
5. `coordination/SESSION_PROTOCOL.md`
6. `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V01.md`
7. `docs/hiveai/audits/M20_S01_T001_STRICT_AUDIT.md`
8. this prompt
9. relevant MPS/MRP/production/auth/migration/tests/frontend source.

Do not modify `TASKS.md`, `TASKS_HISTORY.md`, or revive `.hiveai` as a competing tracker.

## 1. Objective

Execute M20.S01.T001 as a reconciliation/hardening pass, not a rewrite. Preserve the existing MPS dashboard, planning board, capacity, campaigns, what-if and AI recommendation architecture.

Map what already exists, then make only the smallest changes needed to close unsafe or misleading baseline invariants required by the V01 criteria.

## 2. Required hardening

### Authentication / RBAC / actor identity

Current MPS routes use a fixed `_SYSTEM_USER` instead of the real authenticated actor.

- Replace fixed attribution with repository-standard `get_current_user` / permission dependencies.
- Reuse existing RBAC/module permission architecture.
- Protect reads and privileged mutations consistently.
- Do not invent a parallel auth system.

### Plan lifecycle

- Enforce real `DRAFT -> APPROVED -> RELEASED` semantics.
- DRAFT must not release.
- Repeated release must not duplicate production orders.

### Release eligibility

- Normal release creates production orders only for explicitly eligible lines.
- FEASIBLE-only is the current intended law unless synchronized source proves another canonical contract.
- PENDING, OVERLOADED, MATERIAL_SHORT, INFEASIBLE and ON_HOLD must not silently create orders.
- Return truthful deterministic release/skipped results.

### System-owned line state

- Generic planner PATCH must not forge engine-owned feasibility state.
- Normal planner edit must not casually defeat line-lock semantics.
- Keep planner-editable fields narrow and architecture-consistent.

### MRP generation lineage

- Referenced MRP run must exist and be `COMPLETED`.
- Generated lines must come from that exact run.
- Plan must be DRAFT.
- Preserve locked lines.
- Keep plan/source-run linkage truthful.
- Do not create a second demand engine; MRP already owns sales-order/forecast/safety-stock/supply consolidation.

### Period phasing conservation

Add focused proof that generated MPS net requirements conserve each source MRP net requirement across daily/weekly/monthly periods, including a partial final period, within intentional Decimal rounding.

### Honest what-if exposure

Reconcile declared `MPSChangeType` values with actual computation.

Unsupported types must not be presented as genuinely simulated. Either implement a narrow correct behavior with tests or reject/hide the unsupported behavior. Do not build a full APS engine in this task.

### Production-order integrity

Verify and harden, where required by existing domain contracts:

- warehouse/reference validity;
- recipe lifecycle selection;
- product/recipe/UOM consistency;
- one MPS line -> at most one created production order;
- truthful behavior on skipped/ineligible/no-recipe lines;
- transaction outcome must not mark the plan successfully released in a materially misleading state.

### Migration ownership

Inspect Alembic history for all current MPS tables/columns.

- Do not add duplicate migrations.
- If schema change is genuinely required, preserve single-head migration discipline.
- If no schema delta is needed, record that conclusion and exact evidence in the log.

## 3. Scope boundaries

Do not expand this task into:

- M20.S02 full demand/supply roadmap;
- M20.S03 full shift/calendar/CIP/changeover optimization;
- M20.S04 full scenario KPI engine;
- M21+ roadmap implementation;
- M32 APS rewrite;
- unrelated module cleanup/refactors.

Known later gaps such as fixed 8-hour capacity assumptions, work-center compatibility depth, campaign-family/changeover/CIP sophistication and richer scenario KPIs should be logged as bounded follow-up evidence unless they cause a direct correctness defect in this task.

## 4. Tests

Create focused tests that directly prove the V01 criteria, especially:

- authentication/permission enforcement and real actor attribution;
- DRAFT release rejection;
- APPROVED release eligibility;
- non-FEASIBLE lines never create production orders;
- repeated release cannot duplicate orders;
- generic line edit cannot forge protected state;
- missing/non-COMPLETED MRP run rejection;
- phasing conservation;
- locked-line preservation;
- unsupported what-if behavior is rejected/hidden or correctly implemented;
- existing MPS capacity/campaign/what-if read paths remain functional.

Tests must be load-bearing. Arrange negative cases so unrelated earlier failures cannot make them green.

Run focused tests first, then the strongest practical regression available. Also run relevant backend import/compile/Alembic checks. If frontend files are changed, run the repository's frontend type-check/build validations.

If an environment dependency prevents a required command, record the exact command/error and do not claim PASS for that check.

## 5. Git and evidence discipline

Before commit verify:

- `TASKS.md` diff is empty;
- `TASKS_HISTORY.md` diff is empty;
- only authorized task files are staged;
- `git diff --check` is clean.

Commit and push authorized implementation safely to `origin/main` without force.

Then create and push:

`coordination/sessions/M20-S01-T001/CLAUDE_LOG_V01.md`

The log must contain:

- prompt + criteria references;
- synchronized starting HEAD / origin main;
- preserved owner/local work;
- existing-capability map;
- exact changed files;
- implementation decisions;
- required criteria/invariant evidence;
- exact commands and actual results;
- expected failure condition for material negative tests;
- failures encountered and fixes;
- migration ownership conclusion;
- implementation commit SHA(s) and final pushed remote state;
- blockers/unverified assumptions;
- explicit confirmation that `TASKS.md` and `TASKS_HISTORY.md` were read but not modified.

Do not create `CHATGPT_AUDIT_*` files and do not self-assign an audit verdict.

Final response must be exactly:

```text
AWAITING_AUDIT
https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/sessions/M20-S01-T001/CLAUDE_LOG_V01.md
```

If safe synchronization or an unavoidable out-of-scope contract blocks work, stop rather than improvising and return:

```text
BLOCKED
https://github.com/Sekiph82/fmcg-erp-system/blob/main/coordination/sessions/M20-S01-T001/CLAUDE_LOG_V01.md
```
