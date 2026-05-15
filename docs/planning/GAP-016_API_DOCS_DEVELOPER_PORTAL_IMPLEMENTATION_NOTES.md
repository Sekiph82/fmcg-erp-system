# GAP-016 API Documentation and Developer Portal Implementation Notes

## Summary

GAP-016 enhanced the OpenAPI documentation metadata for the FMCG ERP backend API. The FastAPI app had only a title and version — no description, contact, or license. Four critical endpoints (login, logout, me, modules/manifest) received `summary` and `description` parameters. All tests pass.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Migration/Models/Schemas/Services | SKIPPED — docs are code/config only |
| Backend `main.py` | Added `description`, `contact`, `license_info` to FastAPI app |
| Auth endpoints | Added `summary`/`description` to login, logout, GET /me |
| Modules endpoint | Added `summary`/`description` to GET /modules/manifest |
| Tests | Added `backend/tests/test_gap016_api_docs_metadata.py` with 6 checks |
| Frontend | SKIPPED — developer portal pages already exist |
| Permissions | SKIPPED — no new permissions needed |

---

## Changes Made

### `backend/app/main.py`

Added to `FastAPI(...)` constructor:

```python
description="## FMCG ERP REST API\n\n..."  # explains auth, permissions, rate limits, environments
contact={"name": "ERP Support", "email": "support@erp.internal"}
license_info={"name": "Proprietary"}
```

### `backend/app/api/v1/endpoints/auth.py`

| Route | Added |
|---|---|
| `POST /auth/login` | `summary="Authenticate user"`, multi-line description covering 2FA flow, rate limiting, lock-out |
| `POST /auth/logout` | `summary="Revoke access token"`, description of blocklist behavior |
| `GET /auth/me` | `summary="Current user profile"`, description of returned payload |

### `backend/app/api/v1/endpoints/modules.py`

| Route | Added |
|---|---|
| `GET /modules/manifest` | `summary="Module manifest for authenticated user"`, description of frontend use case |

---

## Tests

### `backend/tests/test_gap016_api_docs_metadata.py`

6 focused tests against the live OpenAPI schema:

| Test | Checks |
|---|---|
| `test_openapi_has_title` | `info.title` is non-empty |
| `test_openapi_has_version` | `info.version` is non-empty |
| `test_openapi_has_description` | `info.description` contains "Authentication" and "Permissions" |
| `test_openapi_has_contact` | `info.contact.email` is present |
| `test_openapi_has_license_info` | `info.license` is present |
| `test_module_manifest_route_has_summary` | `GET /api/v1/modules/manifest` operation has `summary` |

All 6 passed.

---

## Known Limitations

| Area | Detail |
|---|---|
| Route coverage | 93% of routes (~2,264) still have no docstring or FastAPI `summary`. Adding docs to all routes is impractical in a single GAP. |
| Developer portal KPIs | Portal shows static/mocked stats; no backend endpoint supplies live API usage telemetry. |
| SDK docs | No generated client SDK (Python/JS) documentation. |
| Webhook docs | Webhook endpoints have duplicate operation ID warnings (pre-existing FastAPI config issue). |
| GraphQL | Listed in developer portal as planned; not implemented. |
| `pyotp` missing in dev venv | Auth module fails to register in the dev environment OpenAPI schema because `pyotp` is not installed in the worktree venv. Auth routes have correct `summary` parameters but they don't appear in the generated schema locally. |
