# M20-S01-T001 — ChatGPT Strict Audit V02

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Audited implementation commit: `826891b92e731c14b87c5e574831cd334aeea4e5`
Claude log: `coordination/sessions/M20-S01-T001/CLAUDE_LOG_V02.md`
Audit criteria: `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V02.md`

## Verdict

**CHANGES_REQUIRED**

V02 materially improves the implementation, but M20.S01.T001 is not yet safe to close. The Claude log was treated only as an evidence pointer. Source, commit diff, tests, prompt and audit criteria were independently inspected.

## What was independently verified

- MPS RBAC remains wired through `require_permission(...)` and V02 adds request-level 401/403/200 tests rather than relying only on source inspection.
- `MRPResult.run_id` is the real FK field and the prior `MRPResult.mrp_run_id` reference was corrected.
- target Warehouse existence and `is_active` are now checked before release work.
- recipe selection is now deterministic and uses existing `APPROVED`, active and effective-date fields.
- release UOM is normally derived from `Product.uom` rather than unconditionally set to KG.
- a zero-order release no longer sets the plan to RELEASED.
- repeated release now has a behavioral service-level test.
- the squashed baseline migration `20260517_0000_squashed_baseline.py` imports `app.models` and executes `Base.metadata.create_all(...)`; `backend/app/models/__init__.py` imports all six MPS ORM models, so static migration ownership is now sufficiently established for this task. No new migration is required by the V02 code changes.

## Frozen V02 findings

### F-V02-001 — P1 — Partial release still falsely transitions the whole MPS plan to RELEASED

`release_mps_plan()` currently computes:

```python
release_complete = created > 0
if release_complete:
    plan.status = MPSStatus.RELEASED
```

This means a plan with 10 FEASIBLE lines can create 1 order, skip 9 because no approved/effective recipe exists, and still become fully `RELEASED`. Likewise, the presence of unresolved non-FEASIBLE lines does not prevent RELEASED once at least one order is created.

This directly violates V02 criteria `M20S01-V02-050`, `052`, and the V02 execution prompt requirement: a plan must not become fully RELEASED when release is incomplete or unresolved required lines remain.

Required correction:
- define completion from the whole release set, not `created > 0`;
- if any required eligible line cannot create its ProductionOrder, remain `APPROVED` and return truthful unresolved counts;
- decide explicitly, from existing MPS semantics, whether non-FEASIBLE lines are outside the current release set or are blockers to whole-plan RELEASED. The code/test contract must make that rule unambiguous;
- add a mixed partial-release test: at least one PO created + at least one eligible FEASIBLE line skipped -> plan must not be RELEASED.

### F-V02-002 — P1 — Missing Product silently falls back to hard-coded `KG`

Current code:

```python
product = await db.get(Product, line.product_id)
...
uom=product.uom.value if product and product.uom else "KG"
```

This still contains a hard-coded `KG` fallback and converts broken master-data integrity into a plausible but potentially false ProductionOrder. That contradicts criteria `M20S01-V02-040` and the prompt requirement to derive UOM from authoritative master data.

A missing Product for an MPS line is an invalid reference and should fail closed, not silently create a KG order. If the authoritative Product exists but its UOM can legally be null, the task must follow the repository's existing explicit default/validation semantics rather than inventing KG locally.

Required correction:
- fail before creating the PO when Product cannot be loaded;
- derive UOM only from authoritative existing data;
- remove local hard-coded KG fallback unless a repository-wide authoritative default is explicitly proven and reused;
- add behavioral tests for missing Product and missing/invalid UOM.

### F-V02-003 — P1 — Partial exception atomicity is not proven

The endpoint wraps the service in `async with db.begin()`, but the service itself creates and flushes POs one by one. V02 does not prove that an exception after one PO is flushed cannot be committed or leave an in-memory lifecycle/linkage state inconsistent with the intended all-or-fail release contract.

For a critical release path, relying only on an assumed outer transaction is insufficient evidence. Criterion `M20S01-V02-053` explicitly requires partial failure not to leave a misleading lifecycle state.

Required correction/proof:
- add an endpoint- or transaction-bound behavioral test where first line succeeds and a later line raises; prove the transaction rolls back and the plan is not RELEASED and no persistent PO/linkage survives;
- do not add manual commits inside the service;
- if the repository test environment cannot run a real DB transaction, use the strongest existing transactional fixture or a purpose-built PostgreSQL test path. A pure source assertion is insufficient for this criterion.

### F-V02-004 — P2 — Relevant regression set is still not fully green

The V02 log reports `169 passed, 3 failed`. Although the same three module-registry failures were previously observed, criterion `M20S01-V02-084` requires before/after or isolated-main evidence for unrelated failures. V01 did isolate one representative failure before the MPS changes, but V02 did not establish the full 3-failure set against the exact V02 base (`598741a`) or current main.

This does not by itself imply the MPS code caused them, but closure evidence remains incomplete.

Required proof:
- reproduce the same relevant regression command against the V02 base commit or otherwise provide a deterministic comparison demonstrating the exact same three failures existed before `826891b`;
- alternatively fix the failures only if source inspection proves V02 changed their behavior. Do not broaden into unrelated cleanup without evidence.

## Criteria status summary

- Governance: PASS based on GitHub diff/log evidence.
- Auth/RBAC request proof: PASS.
- MRP lineage within current schema: PASS for this task boundary.
- Warehouse validation: PASS.
- Recipe lifecycle/determinism: PASS.
- UOM semantics: **FAIL** due hard-coded fallback on missing/invalid Product UOM.
- Truthful release lifecycle: **FAIL** due partial release becoming RELEASED.
- Behavioral idempotency: PASS.
- Migration ownership: PASS at static source level for this task.
- Regression evidence: PARTIAL / NOT YET SUFFICIENT.
- Partial-failure transactional proof: **NOT PROVEN**.

## Closure decision

M20.S01.T001 remains open. `TASKS.md` must not be advanced to DONE.

The complete remediation set for the next revision is frozen above as F-V02-001 through F-V02-004. V03 must address only this frozen set plus directly necessary tests/evidence, then return a factual `CLAUDE_LOG_V03.md` for independent audit.
