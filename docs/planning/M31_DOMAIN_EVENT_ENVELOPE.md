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
  "reference": { "type": "invoice", "id": "<business ID or null>" },
  "data": { "status": "posted" }
}
```

- `id` is the event-log UUID and is also exposed by the existing `X-Webhook-Event-Id` header.
- `type` is the existing event code; `module` is resolved from the event definition, an explicit module, or `unknown`.
- `schema_version` identifies the immutable JSON Schema snapshot used to validate `data`. The initial version is `1`; an event definition schema change creates the next integer version.
- `occurred_at` is a UTC timestamp captured when the event is created and stored alongside the existing event log row.
- `reference` and `actor_id` carry the existing event metadata. Missing values are represented as JSON `null`.
- `data` contains the caller-supplied business payload unchanged, including any field named `_event`.

The envelope is stored in the existing JSONB `payload` column, so this task adds no database migration. Existing flat rows remain untouched; replay/delivery reads normalize them to the envelope using their existing event-log metadata. Subscription filters and transform templates that use `payload.<field>` continue to address `data.<field>`. New templates may use `data.<field>` or envelope metadata paths such as `reference.id`.

Schema definitions use JSON Schema Draft 2020-12, must have an object root, and may use local references only. Null schemas are explicitly ungoverned and accept object payloads without schema validation. A schema change requires a short change summary; old snapshots are immutable and remain inspectable. Existing definitions begin at version 1, and legacy event rows without a version are read as version 1.

Correlation/causation identifiers and transactional outbox fields remain separate M31.S02 tasks. The contract does not assert delivery authentication, retry guarantees, tenant isolation, or successful external delivery.
