# M31.S03.T001 — Prove always-running dispatcher

## Outcome

Implemented an application-lifespan webhook dispatcher that starts after API startup seeding, polls pending and due retry deliveries on a configurable interval, opens a fresh database session for each batch, logs cycle failures and continues on the next poll, and is cancelled and awaited during graceful application shutdown. Settings default to a 5-second poll and batches of 50; non-positive and non-finite intervals and invalid batch sizes are rejected.

The API runs multiple workers, so both pending and due-retry selections now use PostgreSQL `FOR UPDATE SKIP LOCKED` row claims. This prevents concurrent workers from processing the same stored delivery attempt at once. The event envelope documentation describes the runtime and the remaining at-least-once delivery limitation: an external receiver can accept a request before a worker exits without committing its result.

## Verification

From `backend/`:

```text
python -m pytest -q --disable-warnings tests/test_m31_s03_t001_dispatcher.py tests/test_m31_s02_t004_transactional_outbox.py tests/test_m31_s02_t003_event_idempotency.py tests/test_m31_s02_t002_event_schema_governance.py tests/test_m31_s02_t001_domain_event_envelope.py
33 passed, 67 warnings in 25.68s
```

Also passed `python -m py_compile` for the changed Python files and `git diff --check`. The tests cover repeated polling, retry after a failed cycle, separate sessions, lifespan startup/shutdown, PostgreSQL `SKIP LOCKED` SQL generation, and finite-positive interval validation. They do not send requests to real external webhook receivers or claim exactly-once delivery.

## Independent review

Read-only review found a P2 issue because NaN and infinity passed interval validation. Both the settings validator and dispatcher runtime now require a finite positive interval, with tests for NaN and positive/negative infinity. A second read-only review found no remaining blocker. The reviewer did not run tests or edit files.
