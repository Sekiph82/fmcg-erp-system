# Screenshot Capture Plan

**Date:** 2026-05-18  
**Status:** Implemented — ready to run

---

## Goals

Capture a PNG screenshot of every ERP workspace and key tab for use in user manuals. Screenshots must show a real running ERP, not placeholder images.

---

## Route List Source

`docs/user-manual/screenshots/routes.json`

Rules for routes in this file:
- Only real consolidated workspace paths (e.g., `/dashboard/production`)
- Only real tab query params (e.g., `?tab=orders`)
- No old redirect-only paths (e.g., `/dashboard/van-sales` redirects to `/dashboard/sales`)
- capture=false for any route that is a duplicate or not yet stable

---

## Capture Command

```bash
# From repo root — Docker stack must be running
cd frontend
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manual-screenshots.spec.ts \
  --project=chromium --reporter=list
```

Or use the npm script (once added to package.json):
```bash
npm run test:manual-screenshots
```

The test requires the Playwright setup project to have run first (auth state saved):
```bash
E2E_SKIP_WEBSERVER=1 npx playwright test --project=setup
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manual-screenshots.spec.ts --project=chromium
```

---

## Viewport

Width: 1440px  
Height: 900px  
Full page: false (visible viewport only for workspace screens)

---

## Auth Method

Reuses existing Playwright auth state from `frontend/playwright/.auth/state.json`.  
Auth state created by `e2e/auth.setup.ts` (admin / Admin1234! login).

---

## Output Folder

```
docs/user-manual/screenshots/captured/
```

File naming: `{001-NNN}_{route-id}.png`

---

## Screenshot Index Format

`docs/user-manual/screenshots/screenshots-index.json`

```json
[
  {
    "id": "production-orders",
    "title": "Production — Orders Tab",
    "path": "/dashboard/production?tab=orders",
    "role": "production",
    "module": "production",
    "priority": 1,
    "screenshot": "captured/021_production_orders.png",
    "capturedAt": "2026-05-18T...",
    "status": "captured"
  },
  {
    "id": "some-failing-route",
    "status": "failed",
    "error": "Application error overlay visible",
    "screenshot": null
  }
]
```

---

## Failed Capture Handling

- Capture continues after any single route failure
- Failed routes recorded in index with `status: "failed"` and `error` message
- Manual text for failed routes uses: `> Screenshot pending: [description]`
- Re-run capture after fixing the underlying issue

---

## Old Redirect Route Policy

Old routes (e.g., `/dashboard/van-sales`, `/dashboard/qms`) redirect via Next.js middleware to the consolidated workspace. These are NOT screenshot targets.

Document them in `full-reference/14_OLD_ROUTE_COMPATIBILITY.md` only.

---

## Screenshot Review Checklist

After capture, verify:
- [ ] No screenshots show the login page (auth state stale — re-run setup first)
- [ ] No screenshots show "Application error" overlay
- [ ] No screenshots show a 404 page
- [ ] Priority-1 routes all captured (production, inventory, admin, sales, hr, finance)
- [ ] Screenshots show workspace content, not loading spinners
- [ ] File sizes reasonable (typical: 200–800 KB each)

---

## When to Re-Run Screenshots

- After significant UI changes to any workspace
- Before generating a new manual release
- After adding new workspace tabs
- After theme/branding updates
- After major backend data changes (if demo data is visible)

---

## Avoiding Huge Artifacts in Git

Typical PNG size per screenshot: 200–600 KB.  
140 screenshots × 500 KB average = ~70 MB.

Strategy:
- If total size < 50 MB: commit screenshots alongside docs
- If total size > 50 MB: add `docs/user-manual/screenshots/captured/` to .gitignore and document local generation
- Current policy: check size before committing with `du -sh docs/user-manual/screenshots/captured/`

Screenshots already in .gitignore scope check (they are NOT currently ignored — check if they should be after first capture run).
