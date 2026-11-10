# M29.S01.T002 — Capacity impact of maintenance downtime

## Scope implemented

- Added a read-only maintenance capacity-impact report for active preventive-maintenance windows and breakdown records.
- Compares explicitly linked assets/work centers with planned, confirmed, or in-progress production schedule intervals within a UTC date range.
- Reports scheduled minutes at risk, overlapping schedule IDs, and affected production-order IDs. Overlapping intervals are unioned per work center so one machine-minute is not counted repeatedly.
- Open breakdowns are measured only through the report snapshot time. Missing work-center links, invalid intervals, and timezone-naive legacy records remain visible as unavailable rather than generating a false zero-impact result.
- Added a capacity-risk panel to the breakdown UI and invalidates the report after maintenance records or work-center links change.
- No production schedule or `ResourceCalendar` row is mutated. No lost-unit amount is estimated without a verified product/work-center throughput basis.

## Evidence

- Python syntax compilation and endpoint/schema import check passed.
- Focused ESLint passed for the maintenance breakdown, PM plan, asset pages and API client.
- `git diff --check` passed for the scoped task files.
- Independent read-only review found one mixed naive/aware datetime sort issue. It was corrected by normalizing aware timestamps for ordering and assigning a deterministic ordering key to naive records, which remain unavailable for impact calculation. The reviewer confirmed the fix and found no further blocker.
- Automated tests were not run; consolidated M29 testing is deferred to M29.S04 as requested.

## Boundaries

- This report measures scheduled time overlap, not lost production quantity or financial impact.
- It uses existing maintenance records and production schedules; it does not synthesize factory records or predict future repair duration.
- The endpoint requires both `maintenance.view` and `production.view` and leaves existing APS capacity calculations unchanged.
- Database migration execution and end-to-end runtime acceptance remain pending M29.S04.
