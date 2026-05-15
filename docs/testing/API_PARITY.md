# Frontend / Backend API Parity Checks

## Purpose

The API parity check keeps the dashboard from drifting away from backend routes and shared API-client conventions.

It is especially meant to catch browser code that calls raw relative API paths such as:

```ts
fetch("/api/v1/notifications/...")
```

Those calls can resolve against the frontend host (`localhost:3000`) instead of the backend host and may bypass the shared Axios client, cookie auth, and response interceptors.

## Files

- Manifest: `frontend/scripts/api-parity-manifest.mjs`
- Checker: `frontend/scripts/check-api-parity.mjs`
- Package script: `npm run check:api-parity`

## Run

From `frontend`:

```powershell
npm run check:api-parity
```

Strict mode:

```powershell
npm run check:api-parity -- --strict
```

Current expected result:

- 35 manifest entries
- 753 dashboard page files scanned
- 51 known raw API pages
- 0 uncovered raw API pages

## Manifest Rules

Each entry should map a frontend module to its backend/API contract:

- `key`
- `backendRouteKey`
- `backendPrefix`
- `frontendRoute`
- `frontendClient`
- `requiredViewPermissions`
- `aliases`
- `status`
- `e2eSmoke`
- `allowRawApiPath`
- `notes`

Use `allowRawApiPath: true` only for existing partial modules that still need conversion. Do not add it for new dashboard pages unless there is a clear short-term migration reason and a note.

## Cleanup Workflow

When converting a page away from raw API paths:

1. Add or reuse a typed client in `frontend/src/lib`.
2. Use `apiClient` so `NEXT_PUBLIC_API_URL`, `withCredentials`, and interceptors apply.
3. Keep existing UI behavior unchanged.
4. Remove direct `/api/v1` calls from the dashboard page.
5. Remove or narrow `allowRawApiPath` in the manifest.
6. Run:

```powershell
npm run type-check
npm run check:api-parity -- --strict
```

## CI Recommendation

Add strict mode to CI once the current GAP-005 changes are accepted:

```powershell
cd frontend
npm run check:api-parity -- --strict
```

This command does not require Docker, backend services, database access, or secrets.

