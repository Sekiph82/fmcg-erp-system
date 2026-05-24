# Compliance Regulatory Certs JSON Fix

**Date:** 2026-05-24

---

## Problem

`/dashboard/compliance?tab=regulatory-certs` threw:

```
SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

---

## Root Cause

`frontend/src/app/dashboard/quality/certificates/page.tsx` used bare `fetch("/api/v1/...")` calls — relative URLs that the browser resolved against `http://localhost:3000` (the Next.js dev server). Next.js has no API routes for `/api/v1/regulatory-certs/`, so it returned an HTML 404 page. `r.json()` on HTML throws the SyntaxError.

The backend FastAPI server runs on `http://localhost:8000` and has the endpoint registered at prefix `/api/v1/regulatory-certs` (confirmed in `backend/app/core/module_registry.py` line 513).

All other API lib files (`gs1.ts`, `quality.ts`, etc.) either use `apiClient` from `@/lib/api` (base URL `http://localhost:8000`) or construct absolute URLs with `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`. The certificates page was the only outlier.

---

## Fix

**File:** `frontend/src/app/dashboard/quality/certificates/page.tsx`

Added at top of file:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```

Changed all three `fetch` call sites:

| Before | After |
|--------|-------|
| `fetch("/api/v1/regulatory-certs/expiring?days=90")` | `fetch(\`${API_BASE}/api/v1/regulatory-certs/expiring?days=90\`, { credentials: "include" })` |
| `fetch(\`/api/v1/regulatory-certs/?${p}\`)` | `fetch(\`${API_BASE}/api/v1/regulatory-certs/?${p}\`, { credentials: "include" })` |
| `fetch("/api/v1/regulatory-certs/stats")` | `fetch(\`${API_BASE}/api/v1/regulatory-certs/stats\`, { credentials: "include" })` |
| `fetch("/api/v1/regulatory-certs/", { method: "POST", ... })` | `fetch(\`${API_BASE}/api/v1/regulatory-certs/\`, { method: "POST", credentials: "include", ... })` |

Added `credentials: "include"` to all fetch calls to send the `erp_access_token` cookie to the backend (same pattern used by `apiClient.withCredentials = true`).

---

## Redirect Cache Check

| Check | Result |
|-------|--------|
| 308 in codebase | 0 (only color hex `#eab308`) |
| 301 in codebase | 0 |
| permanentRedirect calls | 0 |
| Middleware redirect status | 302 (both call sites) |
| no-store headers on redirects | ✅ added (commit eb0e1df) |

Dashboard redirects were already 302 + no-store before this fix (from commit `eb0e1df`). No change needed here.

---

## Regression Test

`frontend/e2e/compliance-regulatory-certs.spec.ts`

- Loads `/dashboard/compliance?tab=regulatory-certs`
- Asserts no JSON parse errors in console or uncaught errors
- Asserts no 404 errors
- Asserts no Application error in page HTML
- Asserts `<main>` non-empty
- Asserts Regulatory Certs tab visible

Run:
```
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/compliance-regulatory-certs.spec.ts --project=chromium --reporter=list
```

---

## Static Audit Results

| Audit | Result |
|-------|--------|
| type-check | ✅ CLEAN |
| build | ✅ CLEAN |
| find-broken-action-cards | ✅ 0 |
| audit-visible-import-graph | ✅ BVT 0, 487 working |
| check-restored-routes-quality | ✅ 313/313 valid |
| check-workspace-tabs | ✅ All passed |
| check-route-redirects | ⚠ Expected "Missing middleware" warnings only |

---

## User Action Required

**Normal Chrome still shows old cached redirect behavior:**
Chrome DevTools → **Application** tab → **Storage** → **Clear site data** for `localhost:3000`

This clears any 308 that was cached before Round 14 changed redirects to 302. The server cannot fix what is already cached locally — only clearing site data works.
