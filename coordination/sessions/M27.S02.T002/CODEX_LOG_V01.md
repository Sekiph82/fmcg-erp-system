# M27.S02.T002 — Codex implementation evidence

**Acceptance source:** the root `TASKS.md` row `M27.S02.T002 — Production release/in-process gate` is authoritative. No task-specific acceptance document was linked. Reviewed `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md`; the existing QMS already models production orders, IN_PROCESS inspections, QC templates, and versioned quality-gate definitions, so this task connects those configured controls to the production lifecycle without inventing facility data.

## Implemented

- Configured mandatory `production / ON_PRODUCTION_RELEASE` gates are checked before a planned order changes to RELEASED.
- Configured mandatory `production / ON_IN_PROCESS` gates are checked before completion can close downtime, consume materials, or receive finished goods.
- Both checks require an accepted, passed, mandatory inspection linked to the exact production order and required template, with progression/release blocking enabled. With no active mandatory gate configured, existing production behavior remains unchanged.
- IN_PROCESS inspections derive product, batch, and warehouse identity from the saved production order. The legacy order-inspection route also derives and authorizes the order warehouse before creating an inspection; caller-supplied warehouse mismatches are rejected in both the route and service.
- A process-only inspection cannot be created while an order is planned or released. Completion also requires its qualifying inspection's creation timestamp to be at or after the order's recorded production start, preventing earlier release-stage QC from satisfying a later process gate.
- Gate QC result specifications are sourced from the linked active template. ACCEPT requires a recorded result for every template parameter; user-supplied specifications cannot override template limits or criticality.
- Production gate scopes are serialized against gate-definition changes. Gate module/event inputs are normalized before persistence so case/whitespace variants resolve to the canonical gate scope.

## Validation evidence

- Focused and regression suite: **42 passed, 12 skipped** (`test_m27_s02_t002_production_gate.py`, receiving-gate regression, production/QC regression; the 12 skips are tests guarded for disposable PostgreSQL).
- Fresh PostgreSQL 16 disposable database migrated from the repository baseline through `20261029_0031`; production-gate database test: **1 passed**. It used synthetic-only product, warehouse, recipe, order, gates, and inspections on a random database bound to loopback, and the runner removed the task-owned container afterward.
- `python -m compileall -q` on changed application and test modules: passed.
- `git diff --check`: passed.
- Independent read-only review: **no remaining material findings**. The reviewer identified and the implementation fixed (1) a warehouse-scope bypass in the legacy order-inspection route and (2) acceptance of pre-start QC for an in-process gate.
- No GitHub Actions were run.
