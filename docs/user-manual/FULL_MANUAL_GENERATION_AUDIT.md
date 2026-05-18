# Full Manual Generation Audit

**Date:** 2026-05-19  
**Status:** COMPLETE — 140/140 routes captured

---

## Current State (2026-05-19 Update)

**What changed this pass (Round 11):**
- `manual-screenshots.spec.ts` rewritten v2: failed-only mode, batching, role/ID filter, retry (3×), 4s retry delay, fresh browser context after crash, progress persistence after every route
- `scripts/validate-manual-routes.mjs` created: validates routes.json before capture
- `docker-compose.yml` frontend memory 1G → 2G (prevents dev server OOM during 140-route capture)
- `package.json` added `manual:validate-routes` script
- All 67 failed routes recaptured (production/shop-floor/BOM/planning/quality/compliance/sales/logistics/finance/HR/payroll)
- 24 `> Screenshot pending:` placeholders replaced with real `![...](../screenshots/captured/NNN_id.png)` links across 21 manual files

**Screenshot capture:**
- Script: `frontend/e2e/manual-screenshots.spec.ts` (v2)
- Command: `E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots`
- Output: `docs/user-manual/screenshots/captured/` (~70 MB, gitignored)
- Index: `docs/user-manual/screenshots/screenshots-index.json`

---

## Screenshot capture index

| Metric | Count |
|--------|-------|
| Total routes (capture=true) | 140 |
| Captured | **140** |
| Failed | 0 |
| capture=false (skipped) | 1 (`/dashboard/admin?tab=security`) |
| PNG files | 140 |
| Total size | ~70 MB (gitignored) |

Screenshots are referenced in manuals as:
```markdown
![Title](../screenshots/captured/NNN_id.png)
```

---

## Inputs Required for Full Manual Generation

| Input | Status | Notes |
|---|---|---|
| `MANUAL_AUDIT.md` | Existing | Static code audit complete |
| `FULL_MANUAL_GENERATION_AUDIT.md` | Updated | This file |
| `screenshots-index.json` | **140/140 captured** | All routes captured 2026-05-19 |
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
