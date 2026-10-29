# M06.S03.T003 — Supplier performance data completeness criteria V01

## Authority and scope

The exact task is `M06.S03.T003 — Verify supplier performance data completeness` in root `TASKS.md`. The applicable source audit is `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md`, especially its finding that supplier evaluations, delivery, price, ESG and food-safety signals are fragmented and that the scorecard rollup is missing or unclear.

This is a baseline verification task. Verify the existing supplier evaluation data path and repair only a demonstrated in-scope inconsistency. Do not build a new cross-module scorecard or generate supplier business data.

## Required verification

1. Trace evaluation fields from `SupplierEvaluation` through the create/read schemas, procurement API, persistence helper and supplier dashboard. Confirm which fields are required and which provenance/scope links are optional.
2. Preserve the existing four-dimension arithmetic mean because that is what the current persistence helper and UI preview calculate. Do not add weights, thresholds, coverage periods, freshness rules, or supplier counts as business policy; the audit does not define them.
3. Resolve the proven mismatch where `Supplier.performance_score` is documented as a rolling average but is overwritten with only the newest evaluation. The stored field is `Numeric(5,2)`; use the same two-decimal database rounding for the historical mean in the supplier master and dashboard.
4. Add a task-specific, strictly guarded PostgreSQL integration test using only synthetic supplier/user/evaluation rows. Cover required metric persistence, first evaluation, multiple evaluations, and agreement between the supplier master aggregate and dashboard's all-evaluations aggregate, including a half-cent average that must round consistently to two decimals.
5. Run the test only against a fresh loopback disposable PostgreSQL database with no password, task-specific name and opt-in guard. Run relevant focused regressions, Python compile and `git diff --check`.
6. Obtain one independent source/evidence review. Reviewer must be read-only and must not run tests or access the database.
7. Remove the exact disposable database container and verify it is absent.

## Evidence boundaries and known incompleteness

- Existing evaluations require an evaluation date and four score dimensions; `po_id` and procurement scope fields are optional. Preserve that model. Do not fabricate links or supplier data.
- The supplier management audit explicitly says delivery, ESG and food-safety inputs are not unified into one supplier scorecard. This task records that as an outstanding design/integration limitation; it does not claim those dimensions are complete.
- The audit does not set a valid score range, denominator, evaluation coverage window, freshness limit, or weighting policy. Do not invent or enforce those decisions here.
- Verification uses synthetic records only. It does not establish owner-data coverage, live-provider behavior, production acceptance, or approval of a future comprehensive scorecard.

## Closure evidence

Record baseline/fetched SHAs, source-field trace, exact commands/results, PostgreSQL version and migration head, disposable DB guard and cleanup, reviewer findings, changed files, commit/push state, and remaining evidence limits in `CODEX_LOG_V01.md`.
