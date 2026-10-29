# M31.S02.T002 — Event versioning/schema governance

Date: 2026-10-30
Workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`
Task authority: root `TASKS.md` (M31.S02.T002)

## Scope and policy

- Reviewed the T002 task row, the webhook/event-engine section of `docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md`, and the webhook-documentation findings in `docs/planning/GAP-016_API_DOCS_DEVELOPER_PORTAL_AUDIT.md`. The tracker has no separate T002 acceptance document.
- Event definitions start at schema version 1. Schemas use JSON Schema Draft 2020-12 and validate event business `data` before an event log row or delivery is queued. Definitions without a schema remain explicitly ungoverned and accept object data without schema validation.
- A superuser-only schema update creates a higher version and immutable snapshot; a non-empty change summary and actor ID are stored. Name/module/description changes do not increment the schema version. The public history endpoint reads registered snapshots.
- Schema references are local-only; remote references are rejected. Validation responses identify a failing path/keyword without returning business payload values.
- `schema_version` is carried in the canonical envelope. Existing events are read as version 1, including public event-list/detail responses. Existing schema definitions are migrated as version-1 snapshots. Version-history foreign keys restrict deleting an event definition while snapshots exist.
- Added a conditional Alembic revision that works both after the squashed fresh-install baseline and on an existing pre-versioning database. Existing event definitions are backfilled without changing their current schema content.
- Added the `jsonschema` dependency and typed frontend contracts/helpers. Correlation/causation identifiers, idempotency, and the transactional outbox remain outside T002.

## Verification

- Focused unit suite: `pytest -q tests/test_m31_s02_t001_domain_event_envelope.py tests/test_m31_s02_t002_event_schema_governance.py tests/test_m31_s02_t002_event_schema_governance_db.py` — 17 passed, 3 skipped without the task-specific database gate; 69 framework/deprecation warnings.
- Task-owned disposable PostgreSQL runner: fresh migration to head, downgrade to `20261029_0043`, seed one synthetic legacy definition, upgrade to `20261030_0001`, then API and persistence checks — 4 passed. Image: `postgres:16-alpine`, ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`. Loopback-only binding, no volume mounts; container cleanup completed. Transcript and pytest output are in this task session folder.
- Python compilation passed for changed backend modules, migration, and tests.
- Alembic reports one head: `20261030_0001`.
- Frontend TypeScript `tsc --noEmit` and targeted ESLint for `src/lib/webhooks.ts` passed.
- `git diff --check` passed.
- Independent read-only review examined migration compatibility, version-history deletion protection, validation safety, and public read normalization; findings were corrected and re-reviewed.
- Ruff is not installed in the backend virtual environment; no Ruff result is claimed.

All test records use synthetic identifiers and payloads. No production data, secrets, or real event traffic was used.
