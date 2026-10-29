# M13.S03.T001 — Execution log V01

## Scope and baseline

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Task: `M13.S03.T001 — Verify landed-cost posting chain` from root `TASKS.md`.
- Baseline before implementation: `a403f6f1762addfb2d0e530f60b6a2f7848fae75` (`origin/main`); fetched `origin/main` and confirmed zero ahead/behind divergence before starting.
- Applicable acceptance: `CHATGPT_AUDIT_CRITERIA_V01.md`; baseline audits: `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md` and `docs/planning/GAP-001_ACCOUNTING_CORE_AUDIT.md`.
- No production/owner/provider database or credentials were used. No schema migration was added.

## Implementation

- Landed-cost allocation now uses actual posted GRN fields and accepted quantities, and refuses unavailable allocation bases instead of substituting equal shares.
- Account mapping lookup rejects mappings scoped to a different material/product/category even when their stock type matches; this prevents unrelated inventory or clearing accounts from winning lookup.
- Reallocation and posting serialize on the landed-cost header row. Draft-only editing protects validated allocations from stale header, cost-line, or GRN-link changes.
- Posting requires `finance.post`, an open accounting period covering the supplier bill date, an authenticated actor, the source receipt, and the configured clearing/account mappings.
- Capitalizable FIFO costs update only the source cost layer value and unit cost, preserve quantity, split consumed value to configured COGS, and create linked adjustment, journal, event, and posting batch records.
- Non-capitalizable lines require `LandedCostLine.account_code` to resolve to an active, postable `EXPENSE` chart account. Each allocated amount debits that account and credits the receipt's configured landed-cost clearing account.
- Missing/invalid configuration and journal validation errors roll back the complete transaction. Repeated or concurrent posts cannot apply a second valuation or journal.
- Header foreign-currency and base-currency totals are recalculated from persisted lines when adding a cost line; the previous code double-counted the new base amount.
- The posting API preserves 400 responses for rejected state/configuration changes and uses the existing permission dependency. No hardcoded business account IDs were introduced.

## Disposable PostgreSQL verification

- PostgreSQL image/server: `postgres:16.6-alpine`; server reported PostgreSQL `16.6`.
- Task-owned container: `codex-m13-s03-t001-42da58e053c84067957451de` (labels `codex.task=M13.S03.T001`, `codex.disposable=true`).
- Task-owned database: `fmcg_m13_s03_t001_42da58e053c84067957451de`, exposed only at `127.0.0.1:59639`; no persistent volume. PostgreSQL used local trust authentication, so no password was created or shared.
- The test module required `M13_S03_T001_DISPOSABLE_TEST_DATABASE=1` and an exact matching `M13_S03_T001_DISPOSABLE_TEST_DATABASE_NAME`; its URL guard also required a loopback host and the task-specific database prefix.
- Migration command: `python -m alembic upgrade head`; final database revision: `20261029_0025 (head)`.
- Final task integration run: `python -m pytest -q --tb=short tests/test_m13_landed_cost_posting.py` — **12 passed in 8.34s**.
- Existing posting-helper regression run after the final implementation: `python -m pytest -q tests/test_gap002_posting_integration.py` — **6 passed in 4.92s**.
- `python -m compileall -q app/services/landed_cost_service.py app/services/finance_service.py app/api/v1/endpoints/landed_cost.py tests/test_m13_landed_cost_posting.py` — passed.
- `git diff --check` — passed.
- The task tests cover exact database guard, API permission denial/grant, balanced GL and FIFO valuation, unchanged quantity, partial-consumption COGS, explicit expense posting, wrong-material same-stock-type mapping rejection, closed-period and missing-mapping rejection, rollback after journal-account validation failure, duplicate posting, and simultaneous posting attempts.

## Failed attempts retained as evidence

1. Initial disposable run: `1 passed, 3 failed`. It exposed a stale eagerly loaded GRN-link collection in a reused service session and duplicate synthetic accounting periods in the fixture.
2. Second disposable run: `2 passed, 2 failed`. It exposed the mapping helper selecting a different material's mapping through the shared stock-type predicate, plus the test's matching assumptions.
3. After the mapping lookup fix, the original four-test set passed. The new rollback/concurrency focused run also passed (`2 passed, 4 deselected`).
4. First expanded run: `5 passed, 2 failed`. It exposed the old capitalizable-only posting guard still rejecting the newly supported explicit expense flow and a stale expected error string in the missing-mapping assertion.
5. A clean run of the then-current eight tests passed (`8 passed in 6.74s`).
6. The first ten-test run: `8 passed, 2 failed`. The new two-layer rounding fixture inserted its cost layer before its stock movement, causing a synthetic foreign-key failure; the dependent second failure was an asyncio cleanup warning after that fixture setup aborted.
7. Final clean-database run after inserting the synthetic movement before its layer and rejecting negative lines before allocation: `10 passed in 9.04s`; no test failures.
8. The independent reviewer requested direct source-layer and missing-period rollback coverage plus allocation/batch assertions. Those cases and assertions were added; the final clean-database run reports `12 passed in 8.34s`. All failed attempts affected only this task-owned disposable database and synthetic test setup.

## Review and cleanup

- Independent read-only review: completed; no remaining findings. The reviewer inspected the implementation and test coverage without running tests or accessing the disposable database.
- Implementation commit: `64dcc82eaf70c3b50649830937f2433cd57c9845`.
- Disposable container/database cleanup: complete; the exact task-labeled container was stopped and removed, and a follow-up inspect confirmed it is absent.
- No application service/container, other database, dashboard, owner worktree, or unrelated untracked file was modified or staged for this task.
