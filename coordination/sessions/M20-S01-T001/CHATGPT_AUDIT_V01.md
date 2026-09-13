# M20-S01-T001 — ChatGPT Independent Audit V01

Repository: `Sekiph82/fmcg-erp-system`
Branch: `main`
Audited implementation commits: `04c359e00eb20187f7033d1aaefca8b446fedc51`, `ea3d82d0f0925713917b85ec82c1b91530bae4a8`
Claude evidence log: `coordination/sessions/M20-S01-T001/CLAUDE_LOG_V01.md`
Audit criteria: `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V01.md`

## Verdict

**CHANGES_REQUIRED**

The Claude log was treated only as an evidence claim. The verdict below is based on independent inspection of the GitHub commits and current source on `main`.

## What V01 did correctly

- Removed the hard-coded MPS system actor and wired authenticated user identity into create/approve/release/what-if/AI-review mutation paths.
- Added MPS permission registration and removed the previous duplicate bare route registration.
- Enforced APPROVED-only release at the service layer.
- Restricted release candidates to FEASIBLE lines.
- Removed `feasibility_status` and `is_locked` from generic `MPSLineUpdate`.
- Added MRP-run existence and COMPLETED-status checks.
- Corrected period boundary/proration logic.
- Stopped silently advertising MERGE/SHIFT_ADD as simulated behavior and relabeled SPLIT/cost output as approximate.
- Preserved `TASKS.md` / `TASKS_HISTORY.md` ownership outside Claude.

These are useful hardening changes, but they are not sufficient for closure.

## Frozen V01 finding set

### F-V01-001 — No real unauthorized/unauthenticated endpoint test
**Severity:** P1
**Criteria:** M20S01-V01-020, 057

The new auth/RBAC tests inspect source text. They do not exercise the FastAPI dependency chain with an unauthenticated or unauthorized caller and prove the intended 401/403 behavior. Source-inspection is not load-bearing authorization evidence.

**Required V02 closure:** add real endpoint/dependency-level negative tests for at least one read path and critical mutations (approve/release or equivalent), proving the request fails for the authorization reason if credentials/permission are absent.

### F-V01-002 — MRP lineage is only status-validated, not context-validated
**Severity:** P1
**Criteria:** M20S01-V01-033, 034, 035

`generate_mps_from_mrp()` verifies that the requested `MRPRun` exists and is COMPLETED, but does not prove that the run belongs to the appropriate plant/warehouse/planning context for the target MPS plan or that an unrelated completed run cannot be attached.

**Required V02 closure:** inspect actual MRPRun/MPSPlan fields and enforce every deterministic context invariant that the current schema can support. Where the schema genuinely lacks a relation, document the exact limitation and add a bounded follow-up rather than silently treating any completed run as valid.

### F-V01-003 — Target warehouse is not validated before ProductionOrder creation
**Severity:** P1
**Criteria:** M20S01-V01-041

`release_mps_plan()` accepts `target_warehouse_id` and writes it directly into each ProductionOrder. The imported `Warehouse` model is not queried for existence/validity before release.

**Required V02 closure:** validate target warehouse existence and any existing active/status/plant rule available in the current model before creating any order; fail before partial creation.

### F-V01-004 — Recipe selection is nondeterministic and weaker than lifecycle truth
**Severity:** P1
**Criteria:** M20S01-V01-042

Release currently selects `Recipe` using only `product_id` + `is_active == True` + `limit(1)`, with no deterministic ordering and no approval/effective-date/version rule. If multiple active recipes exist, selection is arbitrary.

**Required V02 closure:** inspect the existing Recipe lifecycle fields and use the strongest already-existing approved/effective/current selection contract. If the data model cannot represent a stronger rule, make the selection deterministic and explicitly document the bounded limitation.

### F-V01-005 — ProductionOrder UOM is hard-coded to `KG`
**Severity:** P1
**Criteria:** M20S01-V01-043

`release_mps_plan()` creates every ProductionOrder with `uom="KG"`. This is an unproven cross-product assumption and can violate product/recipe/master-data semantics.

**Required V02 closure:** derive UOM from the authoritative existing product/recipe/BOM contract. Do not introduce a second UOM rule.

### F-V01-006 — Release can mark a plan RELEASED even when release is incomplete or zero-order
**Severity:** P1
**Criteria:** M20S01-V01-027, 044

After iterating lines, the service unconditionally sets `plan.status = RELEASED`. This occurs even if all FEASIBLE candidates were skipped because no recipe exists, or if there are ineligible lines still unresolved. The return payload reports skips, but the lifecycle state can still communicate successful final release.

**Required V02 closure:** define and enforce truthful release semantics. A plan must not become fully RELEASED while required lines remain unresolved/skipped unless an explicit existing partial-release state/contract supports that result. Fail closed or preserve APPROVED with explicit actionable result when release cannot complete truthfully.

### F-V01-007 — Repeated-release proof is source-counting, not behavioral idempotency evidence
**Severity:** P2
**Criteria:** M20S01-V01-028, 059

The added test asserts that the source string contains `MPSLine.production_order_id == None` twice. This does not execute repeated release and does not prove duplicate-order prevention under service behavior. The state guard likely fails closed after RELEASED, but the explicit criterion required behavioral proof.

**Required V02 closure:** add an actual service-level repeated-release test that executes the release transition twice (or otherwise exercises the state machine) and verifies no second ProductionOrder is created.

### F-V01-008 — Full relevant regression evidence is incomplete
**Severity:** P2
**Criteria:** M20S01-V01-060, 061, 062, 067

The log reports focused MPS tests passing, but a broader selected backend run produced 3 failures and the full backend suite did not complete. The failures may be pre-existing, but V01 does not provide enough independent evidence to claim the relevant regression gate is clean. Frontend validation was started and claimed in the log but the canonical audit evidence is incomplete in the retrieved record.

**Required V02 closure:** run a bounded but meaningful regression set that covers MPS + MRP + production-order creation + module registry/auth dependencies, and record exact results. If known unrelated tests fail, prove baseline equivalence with before/after or current-main isolation; do not merely label failures pre-existing.

### F-V01-009 — Migration ownership statement is not sufficiently proven
**Severity:** P2
**Criteria:** M20S01-V01-050, 053

The implementation commit claims all six MPS tables are owned by a squashed-baseline migration via `Base.metadata.create_all()`, while the log also states no explicit `create_table` exists for the six MPS tables in the scanned migration files. This is a material schema-ownership claim and must be proven from the actual baseline migration path, not inferred.

**Required V02 closure:** identify the exact migration revision/file and exact code path that creates the MPS tables on a fresh database. If the baseline relies on metadata-driven table creation, prove that MPS models are imported into that metadata at migration execution time. Do not add a duplicate migration unless fresh-DB proof shows the tables are missing.

## Additional observations

- The V01 work stayed reasonably bounded and did not rebuild MPS architecture.
- The current period phasing correction is directionally sound, but quantity rounding/conservation should be verified at the aggregate quantity level, not only fraction-sum level, because per-period `_R(..., 3)` can introduce small total drift.
- The current generic line edit still auto-locks every manual update. That is acceptable for now only if the lock has the intended audit meaning; V02 should avoid broadening this behavior.

## Closure decision

M20.S01.T001 remains **OPEN / CHANGES_REQUIRED**.

`TASKS.md` must not be marked DONE from V01.

The complete frozen correction scope is F-V01-001 through F-V01-009. V02 must address this frozen set without expanding into M20.S02/S03/S04 or rebuilding the planning engine.
