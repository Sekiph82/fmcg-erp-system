# M31 domain event envelope

This document records the canonical envelope introduced by M31.S02.T001 and the version governance added by M31.S02.T002. New event rows and webhook deliveries use this JSON shape:

```json
{
  "id": "<event UUID>",
  "type": "invoice.posted",
  "module": "finance",
  "schema_version": 1,
  "occurred_at": "2026-10-30T08:15:00Z",
  "actor_id": "<actor ID or null>",
  "correlation_id": "<workflow ID or null>",
  "causation_id": "<parent event ID or null>",
  "reference": { "type": "invoice", "id": "<business ID or null>" },
  "data": { "status": "posted" }
}
```

- `id` is the event-log UUID and is also exposed by the existing `X-Webhook-Event-Id` header.
- `type` is the existing event code; `module` is resolved from the event definition, an explicit module, or `unknown`.
- `schema_version` identifies the immutable JSON Schema snapshot used to validate `data`. The initial version is `1`; an event definition schema change creates the next integer version.
- `occurred_at` is a UTC timestamp captured when the event is created and stored alongside the existing event log row.
- `reference` and `actor_id` carry the existing event metadata. Missing values are represented as JSON `null`.
- `correlation_id` groups events in one workflow; `causation_id` identifies the event that directly caused this event. Both are optional opaque identifiers carried into webhook deliveries.
- `data` contains the caller-supplied business payload unchanged, including any field named `_event`.

Publishers may provide an optional `idempotency_key`, scoped to the event type. The database stores it with a request fingerprint: repeating the same key and request returns the original event without creating new deliveries; reusing the key with different request content returns HTTP 409. A database unique constraint handles concurrent retries. Identifiers are trimmed and length-limited; blank values are rejected. Inbound requests accept `Idempotency-Key`, `X-Correlation-ID`, and `X-Causation-ID` headers.

The envelope is stored in the existing JSONB `payload` column. The original envelope task added no migration; T003 adds nullable idempotency metadata columns and a unique constraint. T004 uses the event log and its pending delivery-attempt rows as the transactional outbox: `stage_event()` flushes them into the caller's transaction without committing, so the business change and outbox rows become visible together or are rolled back together. Callers must commit once after both the business change and `stage_event()` succeed. The standalone `publish_event()` wrapper stages and commits the event/outbox transaction itself. Existing flat rows remain untouched; replay/delivery reads normalize them to the envelope using their existing event-log metadata. Subscription filters and transform templates that use `payload.<field>` continue to address `data.<field>`. New templates may use `data.<field>` or envelope metadata paths such as `reference.id`.

Schema definitions use JSON Schema Draft 2020-12, must have an object root, and may use local references only. Null schemas are explicitly ungoverned and accept object payloads without schema validation. A schema change requires a short change summary; old snapshots are immutable and remain inspectable. Existing definitions begin at version 1, and legacy event rows without a version are read as version 1.

The outbox guarantees atomic persistence of an event and its pending delivery records with the caller's transaction. It does not guarantee exactly-once external delivery: dispatch, retry, dead-letter, delivery authentication, and tenant isolation remain separate concerns.

## Delivery dispatcher runtime

The FastAPI application lifespan starts a background dispatcher in each API worker after startup seeding. While the worker remains alive, it polls pending deliveries and due retry rows every `WEBHOOK_DISPATCH_INTERVAL_SECONDS` (default 5 seconds), processing up to `WEBHOOK_DISPATCH_BATCH_SIZE` rows in each batch (default 50). Each batch uses a fresh database session. The lifespan cancels and awaits the dispatcher during graceful shutdown; an unexpected cycle error is logged and retried on the next poll.

The production API uses multiple Gunicorn workers. Both automatic polling and manual delivery processing use PostgreSQL `FOR UPDATE SKIP LOCKED` row claims, so workers do not process the same database attempt concurrently. The HTTP request and its status update still cannot be made one atomic transaction across the remote system and PostgreSQL: if a receiver accepts a request but the worker exits before committing the result, that delivery can be sent again. Consumers should deduplicate repeated requests using `X-Webhook-Delivery-Id` (or their event-level idempotency policy). This runtime is available only while at least one API worker is running; it is not an external scheduler or a guarantee that delivery occurs while the API is stopped.

## Delivery metrics and traces

`GET /metrics` includes per-process webhook attempt totals by fixed outcome and a bounded delivery-duration histogram (50–5,000 ms buckets plus overflow). These counters reset when a worker restarts and are not cross-worker totals; use the database-backed webhook report for durable history. Each delivery completion emits a structured log containing event, delivery, subscription, attempt, outcome, response status, duration, and correlation/causation identifiers; payloads, response bodies, endpoint URLs, and credentials are excluded. Outbound requests propagate existing envelope identifiers in `X-Correlation-ID` and `X-Causation-ID`, and custom headers cannot replace them. This provides correlation across the ERP event, delivery attempt, and receiver without introducing an external tracing provider or claiming distributed trace sampling.

## Retry delay policy

`Subscription.max_retries` counts retries after the initial request (the default of five allows up to six total attempts). A failed request is scheduled for retry with exponential ceilings beginning at 60 seconds and doubling up to one hour. Equal jitter chooses a delay between 50% and 100% of each ceiling to spread synchronized failures. Once the configured retries have been used, the failed attempt is marked `DEAD_LETTER` and has no next retry timestamp. A subscription configured for zero retries dead-letters the initial failed attempt.

Dead-letter inspection, delivery-attempt inspection, replay, and manual retry are superuser-only operations. Replay requires at least one event selector (IDs, event code, or a timezone-aware date bound), accepts at most 200 event IDs and 100 subscription IDs, and caps matching events at 200, active subscriptions at 100, and total generated delivery attempts at 1,000 per request. Requests that exceed a cap fail atomically with HTTP 422 and must be narrowed; they never silently truncate matching events or fan-out. Empty selector lists are rejected. Only active subscriptions receive replayed attempts, and configured event-code filters are honored. Bulk replay locks selected event rows in deterministic order, links a new attempt to the latest leaf for each event/subscription pair, and skips pairs that already have an in-flight attempt so repeated or concurrent replay requests do not enqueue duplicates. Manual retry accepts only `FAILED` or `DEAD_LETTER` attempts and refuses to send to inactive subscriptions. It links a new pending attempt to the original row without changing that row's status; a unique database constraint and row lock prevent more than one successor from being spawned for the same attempt. The actionable dead-letter list hides a dead letter that already has a replay child; the complete history remains visible in delivery-attempt inspection.

## Webhook signatures and secret rotation

Outbound HMAC signatures use HMAC-SHA256 over `<unix-timestamp>.<exact-request-body>`, sent as `X-Webhook-Signature: sha256=...` with `X-Webhook-Timestamp` and a `X-Webhook-Delivery-Id`. Receivers accept timestamped signatures within five minutes and require an idempotency key (`Idempotency-Key` or the delivery ID); the event outbox then deduplicates retries. Legacy raw-body HMAC signatures remain readable for existing configurations, but clients should move to timestamped signatures and idempotency headers.

Superusers manage subscription/inbound endpoint secrets. The dedicated HMAC rotate-secret endpoints return a generated 256-bit random secret once, increment the version, and retain the prior key for 24 hours. During overlap, outbound deliveries include both current and previous HMAC signatures; inbound verification accepts either key. A second rotation is refused until the overlap ends so the promised prior key is not silently discarded. Configure the replacement with the partner during the overlap. Secret values are excluded from API models and audit records; configured custom header values are redacted from peer responses. New/rotated secrets are encrypted at rest with Fernet using a domain-separated key derived from `WEBHOOK_SECRET_ENCRYPTION_KEY`, which must be a distinct stable value in production. Rotating the application `SECRET_KEY` therefore does not affect webhook ciphertext. Existing plaintext rows and first-draft `enc:v1` rows remain readable until replaced or rotated. Back up the dedicated encryption key; changing it requires an explicit ciphertext re-encryption procedure. Production also requires a strong non-placeholder application `SECRET_KEY`.
