# M26.S02.T002 — CODEX implementation log

## Implemented

- Added authenticated, machine-specific runtime KPI endpoint and a date-filtered panel on Machine Runtime and Performance.
- Aggregated recorded activity by activity type from source runtime-log timestamps, clipped cross-midnight intervals to the selected UTC dates, and returned per-activity source IDs.
- Open or invalid intervals are listed as unavailable rather than counted. Overlapping source logs remain separate log durations and are not presented as machine availability/utilization.
- Removed the hard-coded 480-minute planning assumption from snapshot recomputation. Without an authoritative machine schedule, availability/utilization/OEE remain unavailable; machine/labor/energy costs remain blank until M26.S02.T003 establishes attribution.
- The machine-ops router requires broad production view for this aggregate; scoped-only users are denied by the existing default-deny authorization helper.

## Checks performed

- Focused M26 S02 tests: 4 passed across T001 and T002; includes cross-midnight clipping, source lineage, incomplete intervals, mixed-UOM allocation, and scoped-only access denial.
- Targeted Python compileall, Ruff `F821`, and `git diff --check`: passed.
- PostgreSQL/migration, frontend/type/lint, E2E, regression, and consolidated M26 code/security review remain pending at M26.S03.T004.

