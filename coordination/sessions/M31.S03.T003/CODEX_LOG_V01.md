# M31.S03.T003 — Dead-letter/replay

## Scope and outcome

Implemented bounded, auditable webhook delivery replay and dead-letter handling within the existing M31 webhook engine. No production credentials, provider callbacks, or owner data were used.

- Delivery inspection, dead-letter inspection, manual retry, and bulk event replay require superuser access.
- Manual retry accepts only `FAILED`/`DEAD_LETTER` attempts and active subscriptions. It creates one linked successor without rewriting the original status; the row lock and unique `replay_of_id` constraint prevent duplicate successors.
- Bulk replay requires an event selector, applies active-subscription/event-code filters, links a successor to the latest leaf attempt, and skips in-flight pairs. Selected event rows are locked in deterministic order so concurrent first replays serialize even when no previous attempt exists.
- Replay is bounded to 200 matched events, 100 active subscriptions, and 1,000 generated attempts. Oversized requests return HTTP 422 before writes; requests are not silently truncated.
- Actionable dead-letter listing and dashboard counts exclude dead letters with a replay successor while delivery history remains queryable.
- Added nullable lineage metadata and a single-successor database constraint through Alembic revision `20261030_0003`.

## Verification

- Focused M31.S03 T001–T003 regression suite: **41 passed, 2 skipped, 69 warnings** in 128.10 seconds. The two database-gated tests were skipped in this ordinary run; the third test verifies the gate itself.
- Disposable PostgreSQL runner: **3 passed** in 11.33 seconds against `fmcg_m31_s03_t003_7209ecbc271f44e39cd6432f`, using local PostgreSQL image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`. This included replay lineage/history, unique successor enforcement, and concurrent first replay producing exactly one root attempt. The task-labeled container was stopped and removed by the runner.
- `python -m py_compile` passed for the changed Python modules and tests.
- `alembic heads` reported only `20261030_0003 (head)`; the disposable runner also upgraded to and confirmed this head.
- `git diff --check` passed.
- Independent read-only review found no remaining blocker after fixes for duplicate validation, fan-out limits, bulk replay lineage, and concurrent first replay serialization.

Warnings are from existing Pydantic model namespace/configuration and FastAPI `regex` deprecations in adjacent modules. They did not fail these checks.
