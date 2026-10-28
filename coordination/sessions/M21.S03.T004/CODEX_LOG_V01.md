# M21.S03.T004 — BOM explosion integrity tests

## Findings and changes

The flattened explosion aggregated leaf requirements using only `item_id` (or the display name) and UOM. Product and material records can have the same UUID in their separate identity spaces, and a reused display name can refer to multiple items with different codes. Those cases could silently combine distinct requirements. A leaf with no usable ID, code, or name also produced an ambiguous aggregate row.

Leaf aggregation now keys by item type, component type, identity kind/value, and normalized UOM. It prefers a stable master ID, then item code, then a normalized name. Missing all identity fields fails closed with `BOMExplosionError`. The flattened result includes `item_type`; the TypeScript contract and explosion table display item type alongside component type.

## Verification evidence

- Focused backend regression: `43 passed, 1 skipped` across `test_bom_explosion_nested.py`, `test_m20_remaining_engine.py`, and `test_bom_explosion_nested_db.py`. The skipped test requires the task-owned disposable PostgreSQL runner; the executed suite covers the nested engine and M20 material-explosion regressions.
- Python compilation passed for the modified explosion service and test module.
- Frontend `npm.cmd run type-check` passed.
- `git diff --check` passed.
- Independent read-only review found no blocker. It checked identity partitioning, response compatibility, and the new negative/positive cases.

## Scope limits

- This task prevents distinct leaf identities from being merged in the explosion result; it does not verify that every free-text or UUID candidate exists in master data.
- Substitute approval semantics remain blocked under `M21.S03.T003` until Şekip defines the policy and authorization lifecycle. Co-product/by-product cost allocation remains blocked under `M21.S03.T002` until its costing rule is supplied. No approvals or accounting rules were inferred here.
- The disposable PostgreSQL test was skipped in this run; no database acceptance is claimed for the newly added identity partition cases.
