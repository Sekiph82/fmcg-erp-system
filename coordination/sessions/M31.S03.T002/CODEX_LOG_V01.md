# M31.S03.T002 — Retry/backoff

## Outcome

Defined `Subscription.max_retries` as additional retries after the initial request, consistent with the API field name. A value of five therefore permits up to six total attempts; zero marks the initial failed attempt `DEAD_LETTER` without scheduling another try. Retry ceilings start at 60 seconds, double exponentially, and cap at one hour. Equal jitter schedules 50%–100% of the current ceiling to spread synchronized failures. An exhausted attempt clears `next_retry_at`.

The policy uses the existing `DeliveryAttempt` fields and dispatcher; no schema migration was needed. The shared M31 event envelope document records the policy and the tests cover first/next/capped delays, retry count boundaries, and zero retries.

## Verification

From `backend/`:

```text
python -m pytest -q --disable-warnings tests/test_m31_s03_t002_retry_backoff.py tests/test_m31_s03_t001_dispatcher.py tests/test_m31_s02_t004_transactional_outbox.py tests/test_m31_s02_t003_event_idempotency.py tests/test_m31_s02_t002_event_schema_governance.py tests/test_m31_s02_t001_domain_event_envelope.py
39 passed, 67 warnings in 24.71s
```

Also passed `python -m py_compile` for the changed Python files and `git diff --check`. No real external webhook receiver was contacted.

## Independent review

An independent read-only review confirmed the attempt count semantics, jitter bounds and cap, zero-retry behavior, and compatibility with T001's due-retry dispatcher. No blocker was reported. The reviewer did not edit files or run tests.
