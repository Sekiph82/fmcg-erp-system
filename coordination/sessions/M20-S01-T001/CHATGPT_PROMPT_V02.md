# M20-S01-T001 — Claude Remediation Prompt V02

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Local workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`

## Objective

Close the complete frozen finding set in:

`coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md`

Do not expand into M20.S02/S03/S04 or redesign the MPS subsystem. Reuse current architecture and existing domain truth.

## Mandatory pre-work

1. Safely synchronize the local workspace with GitHub `main`.
2. Preserve all pre-existing local tracked/untracked work. No force push, destructive reset, clean, or restore that discards owner work.
3. Read:
   - `AGENTS.md`
   - root `TASKS.md` as read-only
   - `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md`
   - this prompt
   - relevant MPS/MRP/Recipe/Warehouse/Product/ProductionOrder/RBAC/migration source and existing tests
4. Do not modify `TASKS.md` or `TASKS_HISTORY.md`.
5. Do not recreate `.hiveai` as a live tracker.

## Required remediation

### 1. Real auth/RBAC negative proof

Keep the current MPS RBAC implementation, but replace/augment source-inspection-only proof with real request/dependency-level tests that demonstrate:
- unauthenticated MPS access fails,
- authenticated user without the required permission cannot perform a critical mutation,
- authorized user can reach the protected path.

Use the repository's existing test/auth fixtures and permission patterns. Do not invent a second auth mechanism.

### 2. MRP run context integrity

Inspect the actual current `MRPRun`, `MPSPlan`, warehouse/plant and related planning fields.

Enforce every deterministic context match that the current schema supports before generating MPS lines. At minimum, an unrelated completed MRP run must not be silently accepted when existing fields allow mismatch detection.

Do not add broad new planning schema in this task. If a context relation genuinely does not exist, document the exact limitation in the V02 log.

### 3. Validate target warehouse before release

Before creating any ProductionOrder:
- verify the target Warehouse exists,
- honor any existing active/status/plant/company constraints already represented by the model/architecture,
- fail before creating orders if the warehouse is invalid.

### 4. Deterministic lifecycle-correct recipe selection

Inspect the current Recipe model/service conventions.

Replace `is_active == True + limit(1)` arbitrary selection with the strongest existing lifecycle rule supported by the repository, including approval/status/effective/current/version truth where those fields exist.

Selection must be deterministic. Do not invent a parallel recipe lifecycle.

### 5. Remove hard-coded `uom="KG"`

Derive ProductionOrder UOM from the existing authoritative product/recipe/master-data contract.

Do not introduce a duplicate conversion system or hard-coded product-family exceptions.

### 6. Truthful release state

A plan must not become fully `RELEASED` when release is incomplete or creates zero orders because of unresolved required lines, missing recipes, invalid references, or other fail-closed conditions.

Use the current state model. Do not invent a broad new workflow state unless absolutely required and already compatible with architecture.

The result must truthfully distinguish created orders and unresolved/skipped conditions. Preserve APPROVED or otherwise fail closed when full release requirements are not satisfied.

Ensure partial exceptions cannot leave a misleading final lifecycle state.

### 7. Behavioral repeated-release test

Add an actual service-level behavioral test that executes release and then attempts release again.

Prove no duplicate ProductionOrder can be created. Do not use source-string counting as the primary proof.

### 8. Migration ownership proof

Do not blindly add a migration.

Identify the exact migration revision/file responsible for creating all six MPS tables on a fresh database.

If a squashed baseline uses `Base.metadata.create_all()`, prove from source that the MPS model tables are imported into `Base.metadata` at migration execution time.

Run/check Alembic single-head. Only create a migration if actual fresh-database ownership is missing.

### 9. Regression verification

Run focused tests covering at least:
- MPS hardening/remediation,
- MRP lineage,
- ProductionOrder release behavior,
- auth/RBAC/module registry,
- recipe/warehouse/UOM release rules,
- repeated release.

Also run compile/import checks and `git diff --check`.

If any relevant existing tests fail, investigate rather than labeling them unrelated. If a failure is demonstrably pre-existing, record before/after or isolated-main evidence.

If frontend files are changed, run frontend type-check/build.

Do not delete, disable, loosen, or rewrite strict tests merely to get green.

## Scope boundary

Do not implement:
- full demand/supply coupling for M20.S02,
- enterprise capacity/calendar/changeover work for M20.S03/M32,
- full what-if simulator for M20.S04,
- new BOM/APS architecture,
- unrelated module cleanup.

## Mandatory output

After implementation and tests:

1. Commit and push all authorized implementation changes to GitHub `main`.
2. Create exactly:

`coordination/sessions/M20-S01-T001/CLAUDE_LOG_V02.md`

3. The log must contain factual evidence only:
   - synchronized starting GitHub SHA,
   - implementation commit SHA(s),
   - exact changed files,
   - exact commands executed,
   - exact test results,
   - failures encountered and corrections made,
   - migration ownership evidence,
   - deviations/blockers,
   - remaining technical risks,
   - explicit confirmation that `TASKS.md` and `TASKS_HISTORY.md` were not modified.
4. Do not assign PASS/FAIL or audit yourself.
5. Do not create `CHATGPT_AUDIT_V02.md`.
6. Commit and push `CLAUDE_LOG_V02.md` to `main`.
7. Final response should contain only `AWAITING_AUDIT`, the implementation/log commit SHA(s), and the GitHub log link.
