# M20-S01-T001 — Claude Remediation Prompt V03

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Local workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`

## Objective

Close only the frozen V02 finding set in:

`coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V02.md`

Do not broaden into later M20 work or unrelated cleanup.

## Mandatory pre-work

1. Safely synchronize the local workspace with GitHub `main`.
2. Preserve all pre-existing tracked/untracked owner work. No force push, destructive reset, clean, or restore that discards owner work.
3. Read:
   - `AGENTS.md`
   - root `TASKS.md` as read-only
   - `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V02.md`
   - this prompt
   - current MPS service/API/models/tests and relevant Product/UOM/ProductionOrder transaction patterns.
4. Do not modify `TASKS.md` or `TASKS_HISTORY.md`.
5. Do not audit your own work and do not create `CHATGPT_AUDIT_V03.md`.

## Required remediation

### 1. Whole-plan release truth

Fix the current `release_complete = created > 0` semantics.

The plan must not become fully `RELEASED` when release-required FEASIBLE lines remain unresolved or fail order creation.

Define the completion law explicitly from current architecture. At minimum:
- one created PO plus one FEASIBLE line skipped for missing/invalid recipe/master data must NOT produce full RELEASED status;
- zero-order release remains fail-closed;
- return payload must expose created/skipped/unresolved counts and completion truthfully.

Do not invent a broad new state unless the existing state model requires it.

Add a behavioral mixed-partial-release test.

### 2. Remove local KG fallback

Current code still contains:

`uom=product.uom.value if product and product.uom else "KG"`

Remove this local fallback.

If Product cannot be loaded, fail closed before creating the ProductionOrder.
If Product UOM is absent/invalid, follow the repository's existing authoritative validation/default semantics; do not invent a local default.

Add behavioral tests for missing Product and missing/invalid UOM.

### 3. Prove transaction rollback on later-line failure

Create an endpoint- or transaction-bound behavioral test that exercises a release where:
- an early line reaches PO creation/flush,
- a later line fails due to a required integrity error,
- the surrounding transaction rolls back,
- no partial persisted ProductionOrder/linkage survives,
- the plan does not remain misleadingly RELEASED.

Use the strongest existing DB/test infrastructure available. Do not treat source inspection alone as proof. Do not add service-level commits.

If a real PostgreSQL-backed test cannot be executed in this environment, implement the strongest architecture-consistent transaction test possible and state the exact remaining limitation in `CLAUDE_LOG_V03.md`; do not falsely claim persistence rollback proof.

### 4. Regression comparison evidence

Re-run the relevant regression command.

If the same three module-registry failures remain, prove the exact same three failures exist on the V03 base commit (the synchronized main SHA before your implementation) using an isolated worktree/temporary checkout or equivalent non-destructive method. Do not modify or rewrite unrelated tests merely to obtain green.

Also run:
- focused V01/V02/V03 MPS tests,
- compile/import checks,
- `python -m alembic heads`,
- `git diff --check`.

No frontend work is required unless you change frontend files.

## Scope boundary

Do not implement M20.S02/S03/S04, new workflow states, new UOM conversion architecture, new planning schema, or unrelated module-registry cleanup unless directly proven necessary by the frozen findings.

## Mandatory output

1. Commit and push all authorized implementation/test changes to GitHub `main`.
2. Create exactly:

`coordination/sessions/M20-S01-T001/CLAUDE_LOG_V03.md`

3. The log must contain factual evidence only:
   - synchronized starting GitHub SHA,
   - implementation commit SHA(s),
   - exact changed files,
   - exact commands and results,
   - failures/corrections,
   - exact transaction-test evidence and limitations,
   - exact base-vs-head regression comparison evidence,
   - blockers/remaining risks,
   - confirmation `TASKS.md` and `TASKS_HISTORY.md` were not modified.
4. Do not assign PASS/FAIL.
5. Commit and push `CLAUDE_LOG_V03.md` to `main`.
6. Final response should contain only `AWAITING_AUDIT`, implementation/log commit SHA(s), and the GitHub log link.
