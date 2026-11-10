# M29.S03.T001 — Standardize availability/performance/quality calculation

## Status

Implemented; pending M29.S04 consolidated test, migration, frontend, and independent review acceptance.

## Evidence and implementation

- Added one Decimal-based OEE calculator shared by production-order OEE, advanced-production OEE records, and machine-operator performance snapshots. Stored values are 0–1 ratios; UI surfaces format them as percentages.
- Availability derives from planned time and recorded downtime, bounded by recorded run time when it exists. Performance requires an actual run-time fact, a positive ideal cycle/rated speed, and total output. Quality requires positive total output and a valid good-output count. OEE stays unknown unless all three components are known; missing source values are not replaced with perfect scores.
- OEE record create/update schemas accept source facts only, validate impossible time/count combinations, and calculate stored KPIs in CRUD. API output includes the ideal cycle input, and the summary preserves valid zero values.
- Production-order OEE uses its recorded time interval less recorded downtime. Since the order model does not provide an ideal cycle and accepted-good output counts, unavailable components remain unknown.
- Machine-operation snapshots reuse the calculator. Their current compute route has no authoritative planned schedule, so availability and OEE remain unknown while performance/quality can be derived only from the recorded runtime/output facts.
- Added migration `20261108_0024` to recalculate existing stored OEE and machine-performance derived columns from their unchanged source facts. It does not invent or rewrite production inputs.
- Updated production OEE UI formatting, null display, threshold presentation, and calculation explanation. Updated client types to allow nullable metrics.
- No M29-specific acceptance document was linked from the T001 row. Relevant current audits read: GAP-007 APS capacity planning, GAP-022 machine streaming, and GAP-023 predictive maintenance.

## Lightweight checks performed

- `python -m py_compile` for the changed calculation, production, schema, CRUD, endpoint, and migration modules — passed.
- Focused Python imports for OEE calculator, schemas, and production metrics — passed.
- `python -m alembic heads` — sole head `20261108_0024`.
- Focused ESLint for the OEE, production report/order pages, and production client types — passed.
- Scoped `git diff --check` — passed. Git emitted informational LF-to-CRLF notices for existing working files.

Comprehensive tests, database migration execution, frontend type/build validation, and consolidated independent code/security review are intentionally deferred to M29.S04. No database-backed acceptance is claimed.
