# GAP-016 API Documentation and Developer Portal Maturity — Audit

## Existing State

| Layer | Status |
|---|---|
| OpenAPI/Swagger at `/docs` | EXISTS — auto-generated |
| ReDoc at `/redoc` | EXISTS — auto-generated |
| FastAPI OpenAPI metadata | PARTIAL — title and version set; description/contact/servers/license missing |
| Developer portal frontend | EXISTS — API key management, GraphQL status, developer tools grid |
| Route-level docstrings | MISSING on 93% of routes (~2,264 of 2,456 total) |
| FastAPI `summary=` / `description=` params | MISSING on 99% of routes |
| Standalone API reference docs | MISSING |
| SDK/client library docs | MISSING |
| Error code reference | MISSING |
| Webhook documentation | MISSING |
| Auth/bearer token examples | MISSING |

---

## FastAPI App Config

**File:** `backend/app/main.py:60-67`

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

Missing from the app definition:
- `description` — high-level ERP API description
- `contact` — support email/name
- `license_info` — licensing terms
- `terms_of_service` — ToS URL
- `servers` — environment-specific base URLs (dev/staging/prod)
- `openapi_tags` — grouped tag metadata with descriptions

---

## Developer Portal Frontend

**Directory:** `frontend/src/app/dashboard/developer/`

| Page | Content |
|---|---|
| `page.tsx` | KPI strip (total keys, active keys, API calls, success/error counts), auth methods card, rate limit card, developer tools grid |
| `keys/page.tsx` | API key list, create, revoke, copy raw key UI |
| `graphql/page.tsx` | GraphQL planned/disabled status, mentions REST at `/api/v1` as primary, integration steps |

The portal exists and is functional for key management. The KPI data appears to be static/mocked — no backend API key management endpoint was found in `module_registry.py`.

---

## Route Documentation Coverage

Total routes: ~2,456 across 138 endpoint files.

| Metric | Count | % |
|---|---|---|
| Routes with function-level docstrings | ~192 | 7.8% |
| Routes with FastAPI `summary=` param | ~24 | 0.98% |
| Routes with no documentation at all | ~2,264 | 92.2% |

Sampled files with zero route docstrings: `auth.py`, `users.py`, `products.py`, `sales.py`, `finance.py` — all core-critical modules.

---

## Docs Directory Structure

```
docs/
  DEPLOYMENT.md         — production deployment guide
  planning/             — 40+ GAP audit/implementation docs
  testing/              — API_PARITY.md, E2E.md
  user-manual/          — 7-phase user manual with index
```

No standalone API reference document. No generated markdown from OpenAPI schema.

---

## Critical Findings

### CRITICAL-001: OpenAPI Metadata Is Incomplete
FastAPI app has `title` and `version` only. No `description`, `contact`, `license_info`, `servers`, or tag descriptions. The Swagger UI at `/docs` shows a blank description and no environment context. This is the first thing external developers see.

### MEDIUM-001: 93% of Routes Have No Documentation
Almost all route functions are undocumented. The auto-generated OpenAPI shows only the URL path and HTTP method — no description, no parameter explanation, no response schema description.

### MEDIUM-002: Developer Portal KPIs Appear Static
The developer portal dashboard shows API call counts and key stats but no backend endpoint serves this data. The portal is a UI shell without live telemetry.

### LOW-001: No Standalone API Reference
No `docs/api/` directory. No generated or hand-written API reference beyond the live Swagger UI. Offline or version-pinned reference is not possible.

---

## What Is NOT Missing

- The OpenAPI JSON is accessible at `/api/v1/openapi.json` — it can be imported into Postman/Insomnia
- The developer portal UI for API key management exists (keys/page.tsx)
- Planning/implementation docs are comprehensive (40+ files)
- User manual exists for end users (7 phases)

---

## Scope for GAP-016

Realistic scope — adding docstrings to 2,456 routes is out of scope:

1. **GAP-016B** (Schema/Design): No new DB tables. Enhance FastAPI `app` metadata and add OpenAPI tag descriptions.
2. **GAP-016C/D/E** (Migration/Models/Schemas): SKIP.
3. **GAP-016F** (Services): No service changes.
4. **GAP-016G** (Endpoints): Add `summary` and `description` to the 20-30 most critical endpoints (auth, users, inventory, sales); add OpenAPI tag definitions.
5. **GAP-016H** (Frontend): No new pages; the developer portal already exists.
6. **GAP-016I** (Permissions): No new permissions.
7. **GAP-016J** (Tests): Smoke check that `/api/v1/openapi.json` contains required metadata fields (title, version, description).
8. **GAP-016K** (Docs): Implementation notes.
9. **GAP-016L** (Checks): compile + import + openapi smoke check.
