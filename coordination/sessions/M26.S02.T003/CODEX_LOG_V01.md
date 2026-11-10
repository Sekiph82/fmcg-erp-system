# M26.S02.T003 — CODEX implementation log

## Implemented

- Reworked production-order cost attribution to calculate each machine separately from its own recorded runtime intervals and configured rates; removed cross-machine average-rate multiplication.
- Labor estimates now use each approved labor log's captured rate and duration. Unapproved, unpriced, overlapping, or incomplete inputs are identified; incomplete totals are returned as unavailable.
- Machine estimates use current configured rates and are explicitly labeled estimates because rate history is not stored. The UI no longer asserts KES because these rate records carry no currency code.
- Machine-specific costing returns only that machine's cost basis and does not allocate order labor without a machine-level labor link.
- Snapshot recomputation leaves actual-cost fields unavailable; the previous labor formula mixed unrelated machine/operator rates and is replaced by this task's explicit attribution.

## Checks performed

- Focused M26 S02 tests: 7 passed across T001–T003, including per-machine rate math, per-log labor math, approval/rate gates, interval overlap handling, UTC clipping, source lineage, and aggregate-view denial.
- Targeted Python compileall, Ruff `F821`, route/service import, SQLAlchemy mapper configuration, and `git diff --check`: passed.
- PostgreSQL/migration, frontend/type/lint, E2E, broader regression, and consolidated M26 code/security review remain pending at M26.S03.T004.

