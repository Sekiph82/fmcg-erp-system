# M31.S04.T001 — Delivery metrics/logs/traces

## Scope and outcome

Added bounded delivery telemetry to the existing `/metrics` endpoint and correlated delivery logs/traces using event envelope identifiers. Metrics are process-local and aggregate by a fixed outcome set; no customer, endpoint, or event-code labels are created.

- Each delivery attempt records `sent`, `failed`, `retrying`, or `dead_letter` totals. A bounded 50–5,000 ms histogram records attempt duration and overflow. The existing `/metrics` endpoint returns these values with its request metrics.
- Outbound deliveries propagate envelope `correlation_id` and `causation_id` through `X-Correlation-ID` and `X-Causation-ID`; configured headers cannot override those trace identifiers.
- Production JSON logs include event/delivery/subscription IDs, attempt number, outcome, response status, duration, exception class, and correlation/causation identifiers. They omit payload, response body, endpoint URL, and raw exception text. Preparation, key-decryption, signing, and HTTP errors all transition through retry/dead-letter policy and the same telemetry path.
- Oversized payload failures are counted and logged without creating a network-latency sample. Documentation distinguishes per-worker counters (reset on restart) from durable database reports.
- Updated existing production-settings test fixtures for the dedicated `WEBHOOK_SECRET_ENCRYPTION_KEY` added in T004.

## Verification

- Focused M31.S03 T001–T004 regression tests plus new T001 telemetry tests: **58 passed, 67 warnings** in 36.13 seconds.
- Production configuration and observability tests in `test_hardening.py`: **6 passed** after updating the production fixture for the newly required dedicated encryption key.
- `py_compile` passed for the changed observability/service/test modules; `git diff --check` passed.
- Alembic remains at `20261030_0004 (head)`; this task adds no database migration.
- Full `test_hardening.py` run: **22 passed, 4 failed** in unrelated existing tests. Two auth tests still patch missing `app.core.deps.decode_token`; two route-registration tests assume `.path` on FastAPI `_IncludedRouter`. The production-config failures caused by the new encryption-key requirement were corrected and the relevant tests passed. No auth/router code was changed for T001.
- Independent read-only review found no remaining blocker after expanding telemetry handling to cover failures during preparation as well as network requests.

Warnings are existing Pydantic deprecation warnings in neighboring schemas.
