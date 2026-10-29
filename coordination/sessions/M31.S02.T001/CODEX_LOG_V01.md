# M31.S02.T001 — Canonical domain event envelope

Date: 2026-10-30
Workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`
Task authority: root `TASKS.md` (M31.S02.T001)

## Scope and evidence

- Reviewed the M31.S02.T001 task row and the applicable webhook/event-engine section of `docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md`. The tracker has no separate acceptance document for T001; the audit describes the existing event engine as a partial foundation.
- Added a typed, versionless envelope with event UUID/type/module/time, actor, optional business reference, and nested business `data`. Event publication no longer mutates the caller's payload; the existing JSONB column is reused, so no migration is needed.
- New webhook deliveries use the envelope. Existing flat event rows are normalized when read or replayed and are not rewritten. Legacy `payload.*` filter and transform paths continue to address `data.*`.
- Documented the contract and explicitly left version/schema governance (T002), idempotency/correlation/causation (T003), and transactional outbox (T004) to their own tasks.
- Added focused tests for envelope shape, caller-payload preservation, filter/template aliases, legacy row normalization, legacy-key collisions, and event publication/subscription filtering.

## Verification

- `backend/venv/Scripts/python.exe -m pytest -q tests/test_m31_s02_t001_domain_event_envelope.py` — 5 passed.
- `backend/venv/Scripts/python.exe -m py_compile app/schemas/webhook.py app/services/webhook_service.py` — passed.
- `git diff --check` — passed.
- Independent read-only review — no blockers; one legacy-envelope collision finding was fixed and re-reviewed as resolved.
- Ruff was unavailable in the backend virtual environment; no Ruff result is claimed.

No external database or fabricated production event data was used.
