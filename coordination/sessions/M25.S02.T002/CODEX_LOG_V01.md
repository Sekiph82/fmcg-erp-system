# M25.S02.T002 — Allocation methods by value/weight/volume/quantity

## Scope delivered

- New receipt lines may record the accepted goods volume in cubic metres. The field is optional, positive-only, and bounded to six decimal places; volume is captured on the receipt rather than inferred from quantity or weight.
- Landed-cost allocation supports quantity, item weight, accepted volume, PO-backed base purchase value, and equal split. Weight works for material and product receipt lines.
- Missing or non-positive selected bases fail closed. Value allocation requires each accepted line to have a positive PO-backed base value.
- Four-decimal currency allocations reconcile to the landed-cost source amount. Allocation results expose the basis used; volume is retained at six decimal places.
- The new-document API and UI no longer offer the unimplemented custom/manual allocation option. Historical allocation labels remain readable.
- Migration `20261029_0038` adds the optional receipt volume with an exact positive-or-null constraint and safely widens allocation volume precision. Downgrade refuses to discard entered volume or reduce precision when sub-three-decimal values exist.

## Decisions and boundaries

- Accepted receipt volume is the explicit basis for `BY_VOLUME`; no dimensions or volume are fabricated from another unit.
- Historical receipts without a recorded volume remain usable for other methods. They fail closed for `BY_VOLUME` and are not backfilled.
- This task calculates allocation only. It makes no claim that accounting journals, inventory valuation, freight invoices, or customs records are independently verified.

## Verification

- `python -m pytest tests/test_m25_s02_t002_allocation_basis.py -q`: 18 passed.
- Task-owned disposable PostgreSQL 16 migration runner: 19 passed, including all allocation-basis tests and the migration schema test.
- The PostgreSQL runner upgraded a loopback-only, synthetic database to `20261029_0037`, simulated the pre-task schema (removed the baseline-created volume field and restored allocation `received_volume` to precision 3), then upgraded to head. The migration added the field, exact check, and precision-6 allocation volume. The randomly named database/container were `fmcg_m25_s02_t002_3a74a0197add46bea1f2` / `codex-m25-s02-t002-3a74a0197add46bea1f2`; the script stopped the task-labeled container after the run.
- Frontend `npm run type-check`: passed.
- Targeted frontend ESLint on the procurement receipt and landed-cost pages/types: passed.
- Python `compileall` for changed backend modules, migration, and tests: passed.
- `git diff --check`: passed; Git reported only its existing `TASKS.md` LF-to-CRLF normalization warning.
- Independent read-only review: final review found no remaining blockers. It caught an allocation-volume precision mismatch and migration-shape guard gaps during review; both were corrected and the final checks above were rerun.

## Limitations

- No live receipt, PO price, material weight, supplier document, customs amount, accounting journal, or factory data was used.
- An old receipt cannot use volume allocation unless its volume is entered through an authorized data-correction process; this task does not create that correction workflow.
