# M31.S04.T002 — Event/API permission tests

## Scope and changes

- Required an authenticated active superuser for every internal webhook/event API route; kept the partner callback free of ERP-session authentication.
- Bound event publication's `actor_id` to the authenticated user, ignoring a caller-supplied actor identity.
- Prevented unauthenticated inbound endpoints from being created in production at both schema and service boundaries. Existing `NONE` endpoints also fail closed in production; nonproduction behavior remains available for local synthetic work.
- Documented the production callback-authentication rule and added HTTP/API coverage for route permissions, actor spoofing, and a timestamped HMAC partner callback with an idempotency key and no ERP session.

## Verification evidence

From `backend/`:

```text
python -m pytest tests/test_m31_s04_t002_event_api_permissions.py tests/test_m31_s03_t004_webhook_secret_rotation.py -q
17 passed, 1 warning in 8.69s

python -m pytest tests/test_m31_s03_t001_dispatcher.py tests/test_m31_s03_t002_retry_backoff.py tests/test_m31_s03_t003_dead_letter_replay.py tests/test_m31_s03_t004_webhook_secret_rotation.py tests/test_m31_s04_t001_delivery_observability.py tests/test_m31_s04_t002_event_api_permissions.py -q
63 passed, 68 warnings in 21.73s

python -m py_compile app/schemas/webhook.py app/services/webhook_service.py app/api/v1/endpoints/webhooks.py tests/test_m31_s04_t002_event_api_permissions.py
PASS

git diff --check
PASS
```

Warnings are existing Starlette/httpx and Pydantic deprecation warnings; no test failed.

## Independent review

Read-only review found no remaining gaps: all internal routes have direct active-superuser dependencies; publication uses the session actor; the public partner callback verifies a real timestamped HMAC without an ERP session; production rejects both new and legacy unauthenticated (`NONE`) endpoints; documentation matches the enforced behavior. Reviewer did not edit files or run tests.
