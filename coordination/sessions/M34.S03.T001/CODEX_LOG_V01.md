# M34.S03.T001 — OTIF, quality, price, and responsiveness KPIs

## Scope and source material

- Implemented the exact current task from root `TASKS.md`: `M34.S03.T001 — OTIF/quality/price responsiveness KPIs`.
- Reviewed `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md`, `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_SCHEMA_DESIGN.md`, and `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_IMPLEMENTATION_NOTES.md`.
- No task-specific acceptance file is linked in the task row. The implementation extends existing supplier, PO, posted GRN, and `SupplierEvaluation` records; it adds no sample or owner data.

## Implementation

- Added a rolling 365-calendar-day OTIF rate to the supplier dashboard. Its denominator is sent, due, non-cancelled POs with lines; its numerator requires each PO line's quantity to be present on posted GRNs received by the expected date. Receipt rows must match the PO-line ID, material ID, product ID, and unit. Draft receipts, late receipts, empty orders, and non-sent statuses do not increase OTIF.
- Exposed recorded evaluation averages for delivery, quality, price competitiveness, responsiveness, and overall score with a visible evaluation count. Missing scores remain blank rather than becoming zero.
- Updated the suppliers dashboard labels and explained the metric window and evaluation source.
- Required a procurement-view permission for the KPI endpoint. Scoped users receive only POs and evaluations they can view; the averages and counts use those filtered records, all-scope `performance_score` is hidden, and empty scoped supplier rows are omitted.
- No migration was required; the implementation uses existing PO, GRN, and supplier-evaluation fields.

## Verification

See `verification-V01.md` for exact commands and results. The focused KPI tests passed 4/4; Python compilation, frontend type-check, targeted ESLint, and `git diff --check` completed successfully. An independent read-only reviewer found no remaining findings and did not run tests.

## Boundaries

- No database, production data, external service, deployment, GitHub Actions, or publication was used.
- This records builder implementation and local verification only; it is not owner acceptance or production approval.
