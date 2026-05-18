# Full Manual Generation Audit

**Date:** 2026-05-18  
**Status:** PARTIAL CAPTURE COMPLETE — 73/140 routes captured (67 failed due to dev server ERR_EMPTY_RESPONSE)

---

## Current State (2026-05-18 Update)

**What changed this pass:**
- `routes.json` rebuilt with real workspace paths and tab params (old redirect paths removed)
- `manual-screenshots.spec.ts` Playwright capture script created
- Kenya go-live manuals created (10 role-based documents)
- Full reference manual structure created (15 chapters)
- Manual strategy, capture plan, automation plan, PDF plan, in-app help plan created
- Backend readiness tests updated to check manuals exist + routes are workspace-based

**Screenshot capture:**
- Script: `frontend/e2e/manual-screenshots.spec.ts`
- Command: `E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manual-screenshots.spec.ts --project=chromium`
- Output: `docs/user-manual/screenshots/captured/`
- Index: `docs/user-manual/screenshots/screenshots-index.json`

---

## Screenshot capture index

**Status:** Pending capture run (index file is currently empty or contains results from last run).

Run `npm run test:manual-screenshots` to populate.

Results will show: captured screenshots, failed routes, and error reasons.

After capture, screenshots are referenced in manuals as:
```markdown
![Title](../screenshots/captured/NNN_id.png)
```

Pending screenshots use:
```markdown
> Screenshot pending: description
```

---

## Inputs Required for Full Manual Generation

| Input | Status | Notes |
|---|---|---|
| `MANUAL_AUDIT.md` | Existing | Static code audit complete |
| `FULL_MANUAL_GENERATION_AUDIT.md` | Updated | This file |
| `screenshots-index.json` | Ready for capture | Run `npm run test:manual-screenshots` |
| `routes.json` | Updated | 140+ real workspace routes |
| `manual-screenshots.spec.ts` | Created | Playwright capture script |
| Kenya go-live manuals | Created | 10 role-based documents |
| Full reference manuals | Created | 15 chapters |
| Live ERP access | Available | Docker stack running on localhost:3000 |

---

## Manual Generation Readiness

- [x] Backend inventory complete
- [x] Frontend route manifest complete (workspace-based routes.json)
- [x] MANUAL_AUDIT.md content audit complete
- [x] Kenya go-live manuals created
- [x] Full reference manual structure created
- [x] Screenshot capture script created
- [ ] Screenshot capture run — **RUN PENDING**
- [ ] Screenshot review and retake failures
- [ ] PDF export (Phase 2)
- [ ] In-app help links (Phase 3)

---

## How to Run Screenshot Capture

```bash
# From repo root — Docker stack must be running
cd frontend

# Step 1: Ensure auth state exists
E2E_SKIP_WEBSERVER=1 npx playwright test --project=setup

# Step 2: Capture screenshots
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manual-screenshots.spec.ts --project=chromium --reporter=list

# Or via npm script (after adding to package.json):
npm run test:manual-screenshots
```

Screenshots saved to: `docs/user-manual/screenshots/captured/`  
Index written to: `docs/user-manual/screenshots/screenshots-index.json`
