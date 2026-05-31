# Chrome Redirect Cache Fix

**Date:** 2026-05-24

---

## Problem

Normal Chrome profile shows old cached redirect behavior; Incognito works correctly.

This is classic browser-cached permanent redirect. Chrome (and all browsers) cache HTTP 301/308 responses indefinitely and replay them locally without contacting the server. Incognito starts with an empty cache, so it hits the server and gets the current 302.

---

## Audit Results

### Were any 308 or permanentRedirect calls found?

**No.** Full search across `frontend/src/**/*.{ts,tsx}`:

- Zero `308` status codes (hits were only hex color strings like `#eab308`)
- Zero `permanentRedirect(...)` calls
- Zero `NextResponse.redirect(..., { status: 301 })` calls
- Zero `NextResponse.redirect(..., { status: 308 })` calls

The middleware was already using `status: 302` on both redirect paths (auth guard + REDIRECTS match).

### Conclusion on 308 source

The cached 308 in normal Chrome was written by an **earlier version of the middleware** (prior to Round 14). That cached entry is still stored in the browser profile. The fix is already in code — the problem is solely browser-side stale cache.

---

## Fix Applied

Added `no-store` cache headers to all middleware redirect responses via a shared `tempRedirect()` helper in `frontend/src/middleware.ts`.

**Before:**
```typescript
return NextResponse.redirect(new URL(dest, request.url), { status: 302 });
```

**After:**
```typescript
function tempRedirect(url: URL | string, base: string): NextResponse {
  const response = NextResponse.redirect(typeof url === "string" ? new URL(url, base) : url, { status: 302 });
  response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
  response.headers.set("Pragma", "no-cache");
  response.headers.set("Expires", "0");
  return response;
}
```

Applied to both redirect call sites:
1. Auth guard (unauthenticated → `/login`)
2. REDIRECTS match (old dashboard route → workspace tab)

Status remains **302** (temporary). Headers prevent any future caching.

---

## Why This Won't Fully Fix the Current Normal Profile

The `no-store` headers prevent **future** caching. They cannot clear a 308 that is **already cached** in the browser. The browser replays the cached 308 locally and never sends a request to the server, so the server-side headers are never seen.

---

## How to Clear the Cached Redirect (User Steps)

### Option A — Clear Site Data (recommended, surgical)

1. Open Chrome with your normal profile
2. Navigate to `http://localhost:3000`
3. Open DevTools → **Application** tab
4. Left sidebar → **Storage** → **Clear site data**
5. Make sure "Cache storage" and "Cookies and other site data" are checked
6. Click **Clear site data**
7. Reload — redirects will now go through the server

### Option B — Clear browsing data for localhost

1. Chrome address bar → `chrome://settings/clearBrowserData`
2. Advanced tab → select "Cached images and files"
3. Clear data
4. Or use keyboard shortcut: `Ctrl+Shift+Delete`

### Option C — Hard reload once (sometimes sufficient)

`Ctrl+Shift+R` — forces full reload bypassing cache for the current page only. May not clear all stored redirects.

### Option D — Test in Incognito first

`Ctrl+Shift+N` — always starts clean. If Incognito works, the issue is confirmed as stale cache in the normal profile.

---

## Post-Fix Verification

| Check | Result |
|-------|--------|
| 308 in codebase | 0 |
| permanentRedirect calls | 0 |
| Middleware redirect status | 302 (both call sites) |
| no-store headers added | ✅ yes |
| type-check | ✅ CLEAN |
| build | ✅ CLEAN |
| Broken action cards | 0 |
| BVT | 0 |
| Restored route quality | 313/313 valid |
| Workspace tabs | ✅ pass |
