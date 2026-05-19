# Manufacturing Manual — PDF Export Report

**Generated:** 2026-05-19  
**Status:** SUCCESS

---

## Output

| Item | Value |
|------|-------|
| PDF file | `docs/user-manual/pdf-output/FMCG-ERP-Manufacturing-Manual.pdf` |
| File size | 0.6 MB |
| Chapters | 13 |
| Images loaded | 0 / 0 |
| Images failed | 0 |
| Exit code | 0 |

> Note: 0 images because chapter files do not yet contain embedded screenshot references. Screenshots are planned in SCREENSHOT_PLAN.md. When screenshots are embedded in chapters, re-run the generator — it validates image refs against `docs/user-manual/screenshots/captured/` before build.

---

## Generator

```
node docs/user-manual/module-manuals/manufacturing/pdf-export/generate-manufacturing-pdf.mjs
```

**Run from repo root.** Requires:
- Node.js 18+
- `cd frontend && npm install` (Playwright + marked)
- `docs/user-manual/screenshots/captured/` with captured PNGs (optional; PDF generates without images)

---

## Chapters Included

| # | File | Title |
|---|------|-------|
| 1 | `00-overview.md` | Manufacturing Overview |
| 2 | `01-recipes.md` | Recipes |
| 3 | `02-recipes-import.md` | Recipe Bulk CSV Import |
| 4 | `03-bom-formula.md` | BOM & Formula Management |
| 5 | `04-production-plans.md` | Production Plans |
| 6 | `05-work-orders.md` | Work Orders & Scheduling |
| 7 | `06-batch-lots.md` | Batch & Lots |
| 8 | `07-quality-control.md` | QC Inspections |
| 9 | `08-shop-floor.md` | Shop Floor Operations |
| 10 | `09-planning-scheduling.md` | Advanced Planning & MRP |
| 11 | `10-npd.md` | New Product Development |
| 12 | `11-oee-reporting.md` | OEE, Downtime & Yield Reporting |
| 13 | `12-compliance.md` | Compliance & Labelling |

---

## Git Status

PDF output is gitignored (`docs/user-manual/pdf-output/`). The generator script and chapter source files are committed.

---

## Next Run

After screenshots are captured and embedded in chapter files, re-run:
```powershell
.\docs\user-manual\module-manuals\manufacturing\pdf-export\run-manufacturing-pdf.ps1
```
