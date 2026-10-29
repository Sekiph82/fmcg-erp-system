# M06.S03.T002 — Landed-cost integration verification criteria V01

## Authority and scope

The exact task is `M06.S03.T002 — Verify landed-cost accounting integration` in root `TASKS.md`. Verify current `origin/main` against the latest applicable GAP-001/GAP-002 audits and the accepted M13.S03.T001 implementation evidence. Do not duplicate or redesign the landed-cost subsystem when the current main code already supplies direct, current evidence.

## Required verification

1. Confirm the current source still contains the accepted integration: posted-GRN allocation, correct material-scoped account mapping, FIFO source cost-layer update without quantity mutation, COGS split for consumed value, configured expense/clearing posting for non-capitalizable costs, balanced journals, posting batches/events and source links.
2. Confirm `finance.post`, open-period, missing-mapping/source-layer, invalid/negative-line, rollback, repeat-post and concurrent-post guards remain present.
3. Run the existing M13.S03.T001 PostgreSQL task suite on a fresh task-owned disposable PostgreSQL database. Preserve its strict database guard and task-specific `fmcg_m13_s03_t001_...` naming requirement; identify in the log that this is a reuse/rerun of the original acceptance suite for M06.S03.T002, not a new M13 implementation.
4. Run the named GAP-002 posting-helper regression suite, Python compile, and `git diff --check`.
5. Obtain an independent read-only review of current source and evidence; reviewer must not edit, execute tests, or access the database/container.
6. Remove the exact disposable container and verify it is absent. Report no production/live-provider/owner-data acceptance.

## Accounting and evidence boundaries

- Use synthetic company, supplier, GRN, stock movement, FIFO layer, accounts, period and user records only.
- Do not introduce account IDs, account codes, allocation methods, tolerance values, or FX rules beyond the existing configuration and accepted M13 criteria.
- The GAP-002 audit's broader operational integration remains partial. This task may verify landed-cost posting to inventory/GL; it does not claim supplier-invoice AP/GRNI clearing, all inventory accounting, period-close readiness, or production acceptance.
- If the M13 test suite, current source, or configured-account assumptions are no longer valid, fix only the evidenced landed-cost defect within this task. Record any missing owner-controlled accounting policy as a precise gate rather than inventing it.

## Closure evidence

Record baseline and fetched remote SHAs, source/test lineage, exact commands/results, PostgreSQL version and revision, task-specific guard details, cleanup, independent review, changed-file list, commit/push state, failures/corrections and explicit evidence limits in `CODEX_LOG_V01.md`.
