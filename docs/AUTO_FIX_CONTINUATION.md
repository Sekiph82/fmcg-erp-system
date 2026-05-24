# Auto-Fix Continuation Guide

Date: 2026-05-24 (ERP Button Recovery — FULLY COMPLETE)

## Current State

**Working tree:** CLEAN
**Type-check:** CLEAN | **Build:** CLEAN | **Backend tests:** 482/482 PASS
**Live smoke:** 141/141 passed (exit code 0)

### Full Recovery Results

| Wave | BVT Before | BVT After |
|------|-----------|-----------|
| Baseline | 353 | — |
| Wave 1A+1B+1C | 353 | 48 |
| Broken action cards fix | 48 | 47 |
| Wave 2A+2B | 47 | 3 |
| Wave 2C | 3 | **0** |

**All broken visible action targets resolved. Full live smoke verified.**

---

## Key rules (carry forward)

- **BYPASS_PREFIX_REDIRECT check must come BEFORE exact REDIRECTS and prefix matching** in `matchRedirect()`.
- **API lib `.data` pattern:** `moApi.*`, `mfApi.*`, etc. already call `.then((r) => r.data)` — pages must NOT call `.then((r) => r.data)` again on the return value.
- **Recharts Formatter type:** wrap `(v: number) => ...` with `as never`.
- **Set/matchAll iteration:** use `Array.from()`, not spread `[...set]` (strict TS/target issue).
- **Unescaped JSX entities:** literal `"` → `&ldquo;&rdquo;`, literal `'` → `&apos;` in JSX text nodes.
- **Git commits for page recovery:** `674b6c5` (2026-05-01) = real page implementations. `bd6faf5` = replaced with stubs.
- **Do NOT restore pages blindly:** verify type-check passes after each batch.
- **routeRedirectMap.ts must stay in sync with middleware.ts** redirect map — both must be updated when adding/removing redirects.
- **`useParams()` not `use(params)`** — Next.js App Router client components must use `useParams<{id:string}>()` from `next/navigation`, not `use(params)` from React. The latter suspends and renders empty `<main>`.

---

## Redirect cache defense (2026-05-24)

- Verified: no 308/permanentRedirect anywhere in codebase
- Added `Cache-Control: no-store` + `Pragma: no-cache` + `Expires: 0` to both middleware redirect call sites via `tempRedirect()` helper
- Status is 302 on all dashboard redirects
- If normal Chrome still shows old redirect: Chrome → DevTools → Application → Storage → Clear site data for localhost:3000
- Report: `docs/CHROME_REDIRECT_CACHE_FIX.md`

## Recovery complete

No pending recovery tasks. Next session can start new work directly.
