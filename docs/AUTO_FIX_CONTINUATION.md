# Auto-Fix Continuation Guide

Date: 2026-05-21 (ERP Button Recovery — Wave 1A + 1B complete, stabilization done)

## Current State

**Latest commit:** `7de5623` — fix(ui): restore high-confidence action target pages from git history
**Working tree:** CLEAN
**Type-check:** CLEAN | **Build:** CLEAN | **Backend tests:** 478/482 PASS

### What was restored (this session)

| Wave | Pages | Status |
|------|-------|--------|
| Wave 1A — Cycle Count | 5 | ✅ done |
| Wave 1A — Critical create/new/run | 26 | ✅ done |
| Wave 1B — High-conf operational | ~218 | ✅ done |
| Wave 0 — MPS | 4 | ✅ prior session |

### Broken visible targets
- **Before:** 353
- **After:** 102 (critical: 0, high: 48, medium: 54)
- **Fixed:** 251

### Middleware bypass
253 entries in BYPASS_PREFIX_REDIRECT. All 253 verified as valid real pages (UI present, not redirect-only, not missing).

### Stabilization fixes (this session)
- `machine-ops/performance/page.tsx`: double `.data` wrap removed + Recharts formatter `as never` cast
- 7 files: `react/no-unescaped-entities` (literal quotes in JSX text) escaped

---

## Key rules (carry forward)

- **BYPASS_PREFIX_REDIRECT check must come BEFORE exact REDIRECTS and prefix matching** in `matchRedirect()`.
- **API lib `.data` pattern:** `moApi.*`, `mfApi.*`, etc. already call `.then((r) => r.data)` — pages must NOT call `.then((r) => r.data)` again on the return value.
- **Recharts Formatter type:** wrap `(v: number) => ...` with `as never`.
- **Set/matchAll iteration:** use `Array.from()`, not spread `[...set]` (strict TS/target issue).
- **Unescaped JSX entities:** literal `"` → `&ldquo;&rdquo;`, literal `'` → `&apos;` in JSX text nodes.
- **Git commits for page recovery:** `674b6c5` (2026-05-01) = real page implementations. `bd6faf5` = replaced with stubs.
- **Do NOT restore pages blindly:** verify type-check passes after each batch.

---

## Next session tasks (in order)

1. **Browser smoke test** — when Docker running, verify 14 sample routes show real UI, no redirects, no 404
2. **Wave 1C** — restore remaining 54 high-confidence git-matched pages (48 high + some medium)
   - Only after smoke test passes
   - Same fix patterns apply: `.data` double-wrap, Recharts formatter, Set iteration
3. **Investigate 47 unresolved** — no git match; need new pages or navigation link updates
4. **E2E regression tests** — add Cycle Count + critical routes to `frontend/e2e/action-card-health.spec.ts`

---

## Wave 1C readiness checklist

Before starting Wave 1C:
- [ ] Browser smoke test of Wave 1A + 1B pages passes
- [ ] Working tree clean (no uncommitted changes)
- [ ] Run: `node scripts/audit-visible-import-graph.js` — confirm still 102 broken
- [ ] Run: `npm run type-check` in frontend — confirm clean
