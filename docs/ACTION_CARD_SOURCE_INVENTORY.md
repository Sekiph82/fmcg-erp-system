# Action Card Source Inventory

**Generated:** 2026-05-20
**Method:** Static scan of all TSX/TS source files for dashboard hrefs and router.push calls.

## Summary

| Metric | Count |
|--------|-------|
| Total href / push references scanned | 557 |
| **Pointing to redirect stub page** | 0 |
| Pointing to middleware-redirected route | 26 |
| Pointing to direct route (no redirect) | 531 |

## Redirect Stub References

*None — all action cards point to direct routes or middleware-handled routes.*

## Middleware-Redirected References

- `/dashboard/tax` in `frontend/src/app/dashboard/ai/compliance/page.tsx`
- `/dashboard/production/orders` in `frontend/src/app/dashboard/analytics/production/page.tsx`
- `/dashboard/webhooks` in `frontend/src/app/dashboard/developer/page.tsx`
- `/dashboard/documents/new` in `frontend/src/app/dashboard/documents/compliance/page.tsx`
- `/dashboard/esign` in `frontend/src/app/dashboard/documents/compliance/page.tsx`
- `/dashboard/marketing/campaigns` in `frontend/src/app/dashboard/marketing/page.tsx`
- `/dashboard/marketing/promotions` in `frontend/src/app/dashboard/marketing/page.tsx`
- `/dashboard/approvals` in `frontend/src/app/dashboard/mobile/page.tsx`
- `/dashboard/notification-center` in `frontend/src/app/dashboard/mobile/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/campaigns/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/capacity/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/planning-board/page.tsx`
- `/dashboard/mps` in `frontend/src/app/dashboard/mps/whatif/page.tsx`
- `/dashboard/production/orders` in `frontend/src/app/dashboard/page.tsx`
- `/dashboard/planning/schedule` in `frontend/src/app/dashboard/planning/page.tsx`
- `/dashboard/planning/capacity` in `frontend/src/app/dashboard/planning/page.tsx`
- `/dashboard/planning/bottlenecks` in `frontend/src/app/dashboard/planning/page.tsx`
- `/dashboard/planning/simulation` in `frontend/src/app/dashboard/planning/page.tsx`
- `/dashboard/planning/changeover` in `frontend/src/app/dashboard/planning/page.tsx`
- `/dashboard/movements` in `frontend/src/app/dashboard/products/page.tsx`
- `/dashboard/utility-management/kpi-center` in `frontend/src/app/dashboard/utility-management/alarm-center/page.tsx`
- `/dashboard/utility-management/kpi-center` in `frontend/src/app/dashboard/utility-management/alarm-rules/page.tsx`
- `/dashboard/utility-management/kpi-center` in `frontend/src/app/dashboard/utility-management/integration/page.tsx`
- `/dashboard/iot` in `frontend/src/components/nav-config.tsx`
- `/dashboard/notification-center` in `frontend/src/components/NotificationBell.tsx`
- `/dashboard/production/orders` in `frontend/src/lib/actionRegistry.ts`

## Notes

- Redirect stubs: page.tsx files with `redirect()` and ≤8 non-empty lines.
- Middleware redirects: routes intercepted by middleware.ts REDIRECTS map.
- Both cause extra redirect hops. Stubs are classified broken; middleware redirects are usually safe consolidation routes.
- See `docs/BROKEN_ACTION_CARDS.json` for cross-referenced report.
