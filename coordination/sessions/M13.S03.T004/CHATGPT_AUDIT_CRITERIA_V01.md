# M13.S03.T004 — Period-close rehearsal acceptance criteria V01

## Task

Rehearse period close and reconciliation on a staging/live-like database using synthetic finance records only.

## Acceptance

1. Run only against a task-owned PostgreSQL database on loopback with an exact, unique `fmcg_m13_s03_t004_<hex>` name. Require an explicit `M13_S03_T004_DISPOSABLE_TEST_DATABASE=1` opt-in and verify the configured SQLAlchemy URL matches the exact expected database before any test writes. Never read or write a production/owner database.
2. Exercise the actual finance API/service paths with a synthetic company/period, balanced journal activity, and explicit period-close reconciliation checks. Record the trial-balance and reconciliation outcomes; do not claim live bank or eTIMS acceptance.
3. A period with any `PENDING` or `FAILED` close check must remain `OPEN`; the close endpoint must report a conflict and leave actor/time/status fields unchanged. A `WAIVED` check is an explicit controlled exception only when its result summary records a reason.
4. Close is allowed for an `OPEN` period when its configured checks are terminal (`PASSED` or reasoned `WAIVED`). The authenticated actor and close timestamp must persist. A repeated close must fail without replacing the original actor/timestamp.
5. `LOCKED` may only follow `CLOSED`; repeated lock and lock-from-`OPEN` must not mutate state. Close-check create/update must be rejected once the period is closed or locked. Serialize checklist mutations and close against the same period row so concurrent updates cannot bypass the gate.
6. Preserve existing `finance.configure` permissions for checklist maintenance and `finance.approve` for close/lock. Exercise allowed and denied actors through FastAPI dependencies, not by calling route functions in a way that bypasses authorization.
7. Verify a real posting attempt dated in a closed period is rejected and no journal state is committed. Verify balanced synthetic activity remains balanced in the period-close report/rehearsal.
8. No schema migration is expected if existing fields support actor, timestamp, status and summary. If code requires an unrequested business rule or a schema migration, stop before implementing that change and surface the specific owner decision.
9. Record exact commit, commands, PostgreSQL version, outputs, fixture classifications, cleanup, and failures in `coordination/sessions/M13.S03.T004/CODEX_LOG_V01.md`. Do not claim live-provider, production, or deployment acceptance.

## Evidence standard

The task is complete only with exact-SHA PostgreSQL evidence, negative state/permission/transaction cases, a read-only review of the diff and tests, cleanup evidence, and a validated `TASKS.md` update. Test receipts are implementer evidence; they are not an independent audit verdict.
