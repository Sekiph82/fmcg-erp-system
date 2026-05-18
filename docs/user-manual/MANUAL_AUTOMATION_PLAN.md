# Manual Automation Plan

**Date:** 2026-05-18  
**Status:** Design only — not yet implemented

---

## Goal

A future script that reads structured sources and generates Markdown manual pages automatically, keeping manuals in sync with the ERP as it evolves.

---

## Input Sources

| Source | Path | What it provides |
|---|---|---|
| Nav config | `frontend/src/components/nav-config.tsx` | All workspace paths, labels, clusters |
| Route redirect map | `frontend/src/lib/routeRedirectMap.ts` | Old route → new workspace mappings |
| Workspace tab definitions | Each `frontend/src/app/dashboard/*/page.tsx` | Tab keys and labels per workspace |
| Permissions | `backend/app/core/permissions.py` | Permission strings per module |
| Screenshot routes | `docs/user-manual/screenshots/routes.json` | Capture targets, roles, chapters |
| Screenshot index | `docs/user-manual/screenshots/screenshots-index.json` | Status, file paths, capturedAt |
| Manual template | `docs/user-manual/templates/PAGE_MANUAL_TEMPLATE.md` | Output structure |

---

## Script Design

`scripts/generate-manual-pages.mjs`

```
1. Read nav-config.tsx → extract workspace list
2. Read routes.json → map workspace to tabs + roles + chapters
3. Read screenshots-index.json → get screenshot paths (or "pending" if missing)
4. For each workspace:
   a. Render PAGE_MANUAL_TEMPLATE.md with real data
   b. Insert screenshot reference or pending note
   c. Write to docs/user-manual/full-reference/{module}.md
5. Generate 14_OLD_ROUTE_COMPATIBILITY.md from routeRedirectMap
6. Update full-reference/00_FULL_ERP_MANUAL_INDEX.md
```

---

## Output Format

Each generated file follows `PAGE_MANUAL_TEMPLATE.md`.  
Screenshot references use:
```markdown
![Title](../screenshots/captured/NNN_id.png)
```
Or if pending:
```markdown
> Screenshot pending: description
```

---

## Staleness Detection

Script compares `capturedAt` in screenshots-index.json against last git commit date of each workspace page.tsx. If page changed after screenshot, flags as `stale` and adds a warning in the manual.

---

## PDF Export Integration

After generating Markdown:
```
node scripts/generate-manual-pages.mjs
node scripts/export-manual-pdf.mjs --role=production --output=dist/PRODUCTION_MANUAL.pdf
```

See `PDF_EXPORT_PLAN.md` for Pandoc pipeline details.

---

## Future: In-App Help Integration

Generated Markdown can be hosted as static HTML inside `/public/help/` and linked from workspace `?` buttons. See `IN_APP_HELP_PLAN.md`.

---

## Implementation Priority

1. Run screenshot capture manually (done via Playwright)
2. Manually maintain Kenya go-live manuals (done in this pass)
3. Write `generate-manual-pages.mjs` script when manual maintenance becomes too slow (Phase 2)
4. Add PDF export pipeline (Phase 2)
5. Add in-app help wiring (Phase 3)
