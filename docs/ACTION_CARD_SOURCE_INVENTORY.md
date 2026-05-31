# Action Card Source Inventory

**Generated:** 2026-05-31
**Method:** Static scan of all TSX/TS source files for dashboard hrefs and router.push calls.

## Summary

| Metric | Count |
|--------|-------|
| Total href / push references scanned | 813 |
| **Pointing to redirect stub page** | 0 |
| Pointing to middleware-redirected route | 62 |
| Pointing to direct route (no redirect) | 751 |

## Redirect Stub References

*None — all action cards point to direct routes or middleware-handled routes.*

## Middleware-Redirected References

- `/dashboard/tax` in `frontend/src/app/dashboard/ai/compliance/page.tsx`
- `/dashboard/webhooks` in `frontend/src/app/dashboard/developer/page.tsx`
- `/dashboard/documents/new` in `frontend/src/app/dashboard/documents/compliance/page.tsx`
- `/dashboard/esign` in `frontend/src/app/dashboard/documents/compliance/page.tsx`
- `/dashboard/esg` in `frontend/src/app/dashboard/esg/intelligence/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/assignment/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/certs/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/costing/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/downtime/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/machines/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/operators/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/performance/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/runtime/page.tsx`
- `/dashboard/machine-ops` in `frontend/src/app/dashboard/machine-ops/teams/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/bulk-transfer/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/fg-receipt/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/history/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/issue/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/reconciliation/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/reservations/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/returns/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/tanks/page.tsx`
- `/dashboard/material-flow` in `frontend/src/app/dashboard/material-flow/wip-transfer/page.tsx`
- `/dashboard/approvals` in `frontend/src/app/dashboard/mobile/page.tsx`
- `/dashboard/notification-center` in `frontend/src/app/dashboard/mobile/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/campaigns/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/capacity/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/planning-board/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/whatif/page.tsx`
- `/dashboard/mrp` in `frontend/src/app/dashboard/mrp/forecast/page.tsx`
- *(32 more — see JSON)*

## Notes

- Redirect stubs: page.tsx files with `redirect()` and ≤8 non-empty lines.
- Middleware redirects: routes intercepted by middleware.ts REDIRECTS map.
- Both cause extra redirect hops. Stubs are classified broken; middleware redirects are usually safe consolidation routes.
- See `docs/BROKEN_ACTION_CARDS.json` for cross-referenced report.
