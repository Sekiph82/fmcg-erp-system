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

The envelope is stored in the existing JSONB `payload` column. The original envelope task added no migration; T003 adds nullable idempotency metadata columns and a unique constraint. Existing flat rows remain untouched; replay/delivery reads normalize them to the envelope using their existing event-log metadata. Subscription filters and transform templates that use `payload.<field>` continue to address `data.<field>`. New templates may use `data.<field>` or envelope metadata paths such as `reference.id`.

Schema definitions use JSON Schema Draft 2020-12, must have an object root, and may use local references only. Null schemas are explicitly ungoverned and accept object payloads without schema validation. A schema change requires a short change summary; old snapshots are immutable and remain inspectable. Existing definitions begin at version 1, and legacy event rows without a version are read as version 1.

Transactional outbox fields remain a separate M31.S02 task. The contract does not assert delivery authentication, retry guarantees, tenant isolation, or successful external delivery.
