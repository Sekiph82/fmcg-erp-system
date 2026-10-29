# M25.S03.T003 — Reconciliation and audit trail

## Scope and source material

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Exact task: `M25.S03.T003 — Reconciliation and audit trail` from root `TASKS.md`; the task row did not link separate acceptance material.
- Before implementation, reviewed `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`, `docs/planning/GAP-002_POSTING_INTEGRATION_IMPLEMENTATION_NOTES.md`, `docs/planning/GAP-001_ACCOUNTING_CORE_AUDIT.md`, and the M25.S03.T001/T002 execution logs.
- The applicable acceptance intent is to reconcile operational source records with posting events, batches, balanced journals, inventory valuation adjustments, and actual-cost variances, while preserving auditability and not creating accounting side effects.

## Implementation

- Added a finance-view-protected, read-only `GET /api/v1/landed-cost/{header_id}/reconciliation` report.
- The report checks the header/cost-line/allocation totals; source allocation identity against the linked GRN, GRN line, material, accepted quantity, and stock movement; the event-to-batch-to-posted-journal chain; journal balance and amount; capitalization adjustment links; and the saved-rate actual/variance calculation.
- The report distinguishes pending work from exceptions and reconciled postings. It detects missing, duplicate, orphaned, mismatched, zero-delta-but-marked-posted, and unbalanced evidence. It does not repair or mutate accounting records.
- Added an audit timeline containing actual-source entries, operational posting events, posting batches, and journals, including timestamps, statuses, source references, amounts, actor IDs, and cross-record IDs.
- Added the finance-view-only reconciliation panel to the landed-cost detail screen. It refreshes after allocation, posting, actual recording, variance posting, and cancellation.
- Mirrored the variance posting algorithm's stable allocation order, rounded proportional shares, and final-row remainder. Zero-rounded allocation shares are not expected to create posting records.

## Verification

- Task-owned disposable PostgreSQL runner: `coordination/sessions/M25.S03.T003/run_reconciliation_tests.ps1`.
- Final run: **8 passed**; Alembic reached `20261029_0041 (head)`.
- The database used the exact task-prefixed name `fmcg_m25_s03_t003_8904af3fad104ca7b9f0`, `postgres:16-alpine` image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`, a random loopback-only host port, local trust authentication, no password, no volume, and synthetic records only. The runner verified the task labels and removed its container.
- Coverage includes the task database guard, full posted estimate-plus-variance reconciliation, pending variance, tiny rounded allocations and final remainder, corrupted zero-delta status, missing journal link, reassigned GRN identity, finance-view denial/grant, and read-only record-count stability.
- Frontend `npm run type-check` and targeted ESLint passed. Backend `py_compile` and `git diff --check` passed.
- Independent read-only review found and helped correct small-variance rounding and GRN source identity cases. Final read-only review confirmed the zero-delta guard and actor/batch audit timeline; no blockers remain.

## Limits

- No real supplier invoice, factory, business, user, payment, AP/tax record, or live finance configuration was used.
- The report reflects current database evidence and is not a persisted audit snapshot or an approval of the source document.
