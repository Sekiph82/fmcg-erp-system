# M34.S03.T002 — Supplier scorecard

## Scope and source material

- Implemented the exact current task in root `TASKS.md`: `M34.S03.T002 — Supplier scorecard`.
- Reviewed `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md` and the linked GAP-009 supplier schema/implementation notes. No T002-specific acceptance document is linked in the task row.
- The audit calls for a supplier scorecard rollup across delivery, quality, price, responsiveness, ESG, and food-safety signals.

## Implementation

- Extended the existing supplier dashboard into a dimension-level scorecard: actual rolling 365-day OTIF; recorded delivery, quality, price-competitiveness, responsiveness, and overall evaluation averages; latest active linked ESG assessment; and latest linked QMS food-safety record per certificate type.
- ESG records are linked by supplier UUID and selected only when active and their assessment period has ended. QMS records are linked by the exact supplier UUID string; ambiguous supplier-name-only records are not joined.
- Food-safety rows display recorded status, audit score, and expiry. Expired, conditional, rejected, and suspended statuses are not represented as approved. An approval without an expiry date has unknown current validity; no default score or approval is invented.
- Users with broad procurement view can see the supplier-wide ESG and QMS signals. Scoped users receive an explicit restricted marker because those source records do not carry procurement scope fields. Procurement evaluation and OTIF metrics continue to use the viewer's accessible procurement rows.
- The scorecard shows independent dimensions and no new composite weight/rank. The accepted records do not define weights for combining six distinct signals, so applying an arbitrary weighting would misstate supplier performance.
- No migration or data was added; only existing records are read.

## Verification

See `verification-V01.md`. The focused T001+T002 KPI/scorecard suite passed 6/6; Python compilation, frontend type-check/targeted ESLint, and diff checks completed successfully. Independent read-only review found no remaining concrete findings and did not run tests.

## Boundaries

- No integration database, production data, deployment, GitHub Actions, external service, or publication was used.
- This is implementation/build evidence, not owner approval or production acceptance.
