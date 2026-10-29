# M13.S03.T004 — Implementation and rehearsal log V01

## Scope and starting state

- Task: rehearse period close and reconciliation against synthetic staging data.
- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Starting `HEAD` and `origin/main`: `665cf1c06711ef51ca637539b88e06e746f67334`.
- PostgreSQL application target was not used. No live bank, eTIMS, production or owner finance data was used.
- Existing owner changes and unrelated untracked files were preserved.

## Changes

- Period-close checks now serialize with close/lock on the accounting-period row.
- `PENDING` and `FAILED` checks prevent close. A `FAILED` or `WAIVED` result requires a non-empty explanation; non-pending results record the actor and timestamp.
- Only an `OPEN` period can close; only a `CLOSED` period can lock. Repeated transitions are rejected. Checklists cannot change after close.
- Period API responses include `closed_by_id`. Locking records `locked_by_id`/`locked_at` without overwriting the original close actor/time.
- Added PostgreSQL-backed API tests for close-check outcomes, permission boundaries, transition persistence, a synthetic balanced journal/trial balance, and rejection of a posting dated in a closed period.
- The PostgreSQL suite also checks create/update rejection after CLOSED and LOCKED, and queues an update and close behind a held period-row lock to verify their serialized outcome.

Changed implementation/test files:

- `backend/app/api/v1/endpoints/finance.py`
- `backend/app/schemas/finance.py`
- `backend/tests/test_m13_period_close_rehearsal.py`

## Disposable database and evidence

- Final disposable Docker container: `codex-m13-s03-t004-23750b99e77f4b2eb6a7b119` (ephemeral, loopback-only port `62485`, PostgreSQL `16.6`).
- Final database: `fmcg_m13_s03_t004_23750b99e77f4b2eb6a7b119`.
- Opt-in: `M13_S03_T004_DISPOSABLE_TEST_DATABASE=1`; expected database name was set to that exact database. The test guard rejects non-loopback URLs, another database name, or a missing opt-in before integration writes.
- Applied migrations through `20261029_0025 (head)`.
- Final command from `backend`: `python -m pytest -q tests/test_m13_period_close_rehearsal.py --tb=short` — **5 passed in 6.52s**.
- The run exercised API dependencies and database persistence. Synthetic trial balance was balanced at KES 100 debit = KES 100 credit; a later journal dated in the closed period remained unposted and did not change totals.
- `python -m compileall -q app/api/v1/endpoints/finance.py app/schemas/finance.py tests/test_m13_period_close_rehearsal.py` completed successfully.
- `git diff --check` reported no whitespace errors. It printed Git's existing line-ending warning for `TASKS.md`.

## Failed attempts and corrections

- First PostgreSQL-backed suite run: **2 failed, 2 passed**. One assertion exposed that `PeriodRead` omitted the already-persisted `closed_by_id`; another synthetic journal request lacked a broad scope. Added the response field and made only that posting test actor an explicit synthetic superuser. The separate API permission test continues to verify ordinary `finance.configure` and `finance.approve` boundaries.
- The next run passed 4/4. Independent review then found that lock overwrote close actor/time, so locking was corrected and persistence assertions were added. Review also required persisted-state assertions after repeated lock, direct checklist-mutation checks after `LOCKED`, and a real row-lock race. Those checks were added and the final 5/5 database-backed run passed.

## Independent review and cleanup

- Independent read-only review identified three findings during iteration: lock must preserve close history; duplicate lock must leave persisted close/lock actor and timestamps unchanged; checklist edits must be tested after `LOCKED` and serialized against close. All were resolved. Final read-only review reported **no remaining findings** and confirmed the new concurrency coverage.
- Stopped the exact disposable container after the final run; `docker ps -a --filter name=^/codex-m13-s03-t004-23750b99e77f4b2eb6a7b119$` returned no container.
- No database credentials were created or shared. No schema migration was added.

## Acceptance boundary

Evidence supports the synthetic PostgreSQL period-close rehearsal and the tested permission/state/posting matrix only. It does not establish live-provider, production, deployment, external bank, or eTIMS acceptance.
