# Redirect Stub Recovery Report

**Date:** 2026-05-20  
**Scope:** MPS action card redirect stubs — audit, recovery, middleware fix  

---

## Summary

| Metric | Value |
|--------|-------|
| Total redirect stubs found (≤8 lines, `redirect()` only) | 492 |
| Redirect stubs linked from visible action cards (MPS) | 4 |
| Current-code implementations found | 3 (campaigns, capacity, planning-board) |
| Git-history implementations recovered | 1 (whatif — commit 12bcbf5) |
| Middleware prefix-redirect bug fixed | YES |
| Pages reconnected/restored | 4 |
| New pages created from scratch | 0 |
| Remaining needs_review | 0 (MPS complete) |

---

## Root Cause

The Planning workspace (`/dashboard/planning?tab=mps`) dynamically imports `mps/page.tsx`
as the MPS tab. That page renders 4 action cards:

| Card | Target |
|------|--------|
| Planning Board | `/dashboard/mps/planning-board` |
| Capacity Heatmap | `/dashboard/mps/capacity` |
| Campaign View | `/dashboard/mps/campaigns` |
| What-If Simulator | `/dashboard/mps/whatif` |

Two separate issues caused clicking to silently return the user to the same page:

1. **Page files were redirect stubs** — `page.tsx` files contained only `redirect("/dashboard/planning?tab=mps")`.
2. **Middleware prefix-redirect** — `middleware.ts` had `/dashboard/mps` in `REDIRECTS`, which prefix-matched ALL sub-routes including the real pages.

Even after restoring real page content, the middleware intercepted requests first and redirected before pages could render.

---

## MPS Recovery

### Planning Board (`/dashboard/mps/planning-board`)

| Item | Value |
|------|-------|
| Previous behavior | redirect → `/dashboard/planning?tab=mps` |
| Source | `mps/planning-board/page.tsx` — auto-synced in prior session (commit `ced1b1b`) |
| Recovery method | Already real page (previous session) |
| Final behavior | Standalone full planning board: lines table, edit modal, generate from MRP, approve/release |
| Files changed | `middleware.ts` (bypass), `routeRedirectMap.ts` (removed stub entry) |

### Capacity Heatmap (`/dashboard/mps/capacity`)

| Item | Value |
|------|-------|
| Previous behavior | redirect → `/dashboard/planning?tab=mps` |
| Source | `mps/capacity/page.tsx` — auto-synced in prior session (commit `ced1b1b`) |
| Recovery method | Already real page (previous session) |
| Final behavior | Standalone capacity heatmap: work center utilization grid, overload alerts, date columns |
| Files changed | `middleware.ts` (bypass), `routeRedirectMap.ts` (removed stub entry) |

### Campaign View (`/dashboard/mps/campaigns`)

| Item | Value |
|------|-------|
| Previous behavior | redirect → `/dashboard/planning?tab=mps` |
| Source | `mps/campaigns/page.tsx` — auto-synced in prior session (commit `ced1b1b`) |
| Recovery method | Already real page (previous session) |
| Final behavior | Standalone campaign grouping view: SKU groups, sequence, production/changeover hours, efficiency |
| Files changed | `middleware.ts` (bypass), `routeRedirectMap.ts` (removed stub entry) |

### What-If Simulator (`/dashboard/mps/whatif`)

| Item | Value |
|------|-------|
| Previous behavior | redirect → `/dashboard/planning?tab=mps` |
| Source | Original page found in git commit `12bcbf5` (`Add MPS engine: capacity scheduling, campaigns, what-if, AI agents, 5 frontend pages`) |
| Recovery method | Restored from git history |
| Final behavior | Standalone what-if simulator: scenario builder, line selector, change types, impact summary |
| Files changed | `mps/whatif/page.tsx` (restored), `middleware.ts` (bypass), `routeRedirectMap.ts` (removed stub entry) |

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/app/dashboard/mps/whatif/page.tsx` | Restored full what-if simulator from git commit `12bcbf5` |
| `frontend/src/middleware.ts` | Added `BYPASS_PREFIX_REDIRECT` set; `matchRedirect` now skips prefix match for the 4 MPS sub-routes |
| `frontend/src/lib/routeRedirectMap.ts` | Removed 4 stub entries (planning-board, capacity, campaigns, whatif) |
| `scripts/find-redirect-stubs.js` | New audit script — finds all ≤8-line redirect-only pages |
| `scripts/find-broken-action-cards.js` | New audit script — finds action cards pointing to stub routes |
| `scripts/summarize-redirect-stubs.js` | New summary script — groups stubs by target, saves JSON |
| `docs/REDIRECT_STUB_ROUTE_AUDIT.json` | Generated — all 492 redirect stubs with file/route/target |
| `docs/BROKEN_ACTION_CARDS.json` | Generated — action card → stub mapping |

---

## Redirect Stub Architecture (Broader Context)

The ERP uses a page-consolidation architecture: ~492 old standalone sub-routes redirect to
consolidated workspace tabs (Finance, HR, Quality, etc.). These are **safe_redirect** —
intentional consolidation, not broken.

The MPS stubs were a different case: they pointed to routes that should have been real
standalone pages (the original MPS engine created them as real pages in commit `12bcbf5`,
but a later auto-sync commit `bd6faf5` replaced them with redirect stubs during
page consolidation work that should not have touched them).

---

## Verification

| Check | Result |
|-------|--------|
| `npm run type-check` | PASS |
| `npm run build` | PASS (28.4 kB middleware) |
| `pytest tests/ -q` | 482/482 PASS |
| MPS whatif page renders | YES — restoring from git history |
| Middleware bypass active | YES — BYPASS_PREFIX_REDIRECT set |
| routeRedirectMap synced | YES — 4 entries removed |
