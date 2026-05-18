# PDF Export Report

**Date:** 2026-05-19  
**Status:** COMPLETE — Kenya Go-Live PDF generated successfully

---

## PDF Target

**Kenya Go-Live ERP Training Manual**  
Combined role-based training manual for Kenya production launch.

---

## Generation Results

| Metric | Value |
|--------|-------|
| Output file | `docs/user-manual/pdf-output/Kenya-Go-Live-ERP-Training-Manual.pdf` |
| PDF size | **17.5 MB** |
| Images in PDF | **45/45 loaded, 0 failed** |
| Pages (estimated) | ~80–100 A4 pages |
| Page format | A4, 20mm margins |
| Header/footer | Yes (page numbers, document title) |
| Generated | 2026-05-19 |

---

## Source Files Used (in chapter order)

| # | File | Chapter |
|---|------|---------|
| 1 | `kenya-go-live/00_GO_LIVE_TRAINING_INDEX.md` | Training Index & Go-Live Checklist |
| 2 | `kenya-go-live/01_ADMIN_USER_MANUAL.md` | Admin User Manual |
| 3 | `kenya-go-live/02_PRODUCTION_USER_MANUAL.md` | Production User Manual |
| 4 | `kenya-go-live/03_WAREHOUSE_INVENTORY_USER_MANUAL.md` | Warehouse & Inventory Manual |
| 5 | `kenya-go-live/04_PROCUREMENT_USER_MANUAL.md` | Procurement Manual |
| 6 | `kenya-go-live/05_QUALITY_CONTROL_USER_MANUAL.md` | Quality Control Manual |
| 7 | `kenya-go-live/06_SALES_LOGISTICS_USER_MANUAL.md` | Sales & Logistics Manual |
| 8 | `kenya-go-live/07_HR_USER_MANUAL.md` | HR & Payroll Manual |
| 9 | `kenya-go-live/08_MANAGER_DASHBOARD_USER_MANUAL.md` | Manager Dashboard Manual |
| 10 | `kenya-go-live/09_COMMON_PROBLEMS_AND_FAQ.md` | Common Problems & FAQ |

---

## Screenshot Validation

| Metric | Value |
|--------|-------|
| Markdown image refs in Kenya manuals | 45 |
| Refs pointing to existing PNGs | 45 |
| Broken refs | 0 |
| Images loaded in PDF | 45 |
| Images failed in PDF | 0 |

Screenshots validated before PDF generation. All 45 image references in Kenya go-live manuals point to existing captured PNGs.

---

## Export Method

**Tool:** Playwright Chromium + marked (Node.js)  
**Pipeline:**
1. `marked` converts each chapter Markdown to HTML
2. Image paths converted from `../screenshots/captured/xxx.png` to `file:///` absolute URIs
3. CSS stylesheet (`pdf-style.css`) applied — A4, professional, print-optimised
4. Playwright opens HTML as `file:///` page in headless Chromium
5. `page.pdf()` generates PDF with A4 format, 20mm margins, header/footer

**No internet connection required.** No external services. Fully local.

---

## PDF Committed?

**No.** `docs/user-manual/pdf-output/` is gitignored (17.5 MB).

Regenerate locally before printing or distributing.

---

## How to Regenerate

```powershell
# Windows PowerShell (from repo root)
.\docs\user-manual\pdf-export\export-kenya-go-live.ps1

# Bash / Mac / Linux / Git Bash (from repo root)
bash docs/user-manual/pdf-export/export-kenya-go-live.sh

# Direct Node.js (any OS, from repo root)
node docs/user-manual/pdf-export/generate-kenya-pdf.mjs
```

**Prerequisites:**
1. Docker stack running (`docker compose up -d`)
2. Screenshots present: `docs/user-manual/screenshots/captured/` (140 PNGs)
   - Regenerate if missing: `cd frontend && E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots`
3. `marked` installed: `cd frontend && npm install --save-dev marked`

---

## Export Scripts

| File | Purpose |
|------|---------|
| `pdf-export/generate-kenya-pdf.mjs` | Main Node.js generation script |
| `pdf-export/export-kenya-go-live.ps1` | Windows PowerShell wrapper (validates prerequisites) |
| `pdf-export/export-kenya-go-live.sh` | Bash wrapper (validates prerequisites) |
| `pdf-export/pdf-style.css` | A4 print stylesheet |
| `pdf-export/README.md` | Setup and usage instructions |

---

## Known Limitations

- PDF is **not portable** — images use `file:///` absolute paths on the machine where it was generated. Distribute the PDF file, not the paths.
- Screenshots must exist locally (~70 MB). They are gitignored.
- PDF size (~17.5 MB) may exceed email attachment limits. Use file sharing (Google Drive, SharePoint, USB).
- Page breaks are CSS-based. Very long tables or text blocks may split across pages.
- The PDF generator does not produce a clickable table of contents. For navigable TOC, use Pandoc with `--toc` flag if installed later.

---

## Next Recommended PDF

**Full ERP Reference Manual** — covers all 15 chapters for IT admin and ERP power users.

Source: `docs/user-manual/full-reference/01_DASHBOARD_AND_NAVIGATION.md` through `13_STANDALONE_OPERATIONAL_PAGES.md`

Script to create: `docs/user-manual/pdf-export/generate-full-reference-pdf.mjs`

Estimated size: ~30–40 MB (more chapters, same screenshot set).
