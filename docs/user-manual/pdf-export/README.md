# PDF Export Pipeline

Generates training manuals as printable PDFs from Markdown source files.

## Requirements

- Node.js 18+
- `frontend/node_modules/playwright` (already installed — `cd frontend && npm install`)
- `frontend/node_modules/marked` (`cd frontend && npm install --save-dev marked`)
- `docs/user-manual/screenshots/captured/` — 140 PNG screenshots (gitignored, regenerate locally)

## Generate the Kenya Go-Live Manual

**Windows (PowerShell):**
```powershell
# From repo root
.\docs\user-manual\pdf-export\export-kenya-go-live.ps1
```

**Linux / Mac / Git Bash:**
```bash
# From repo root
bash docs/user-manual/pdf-export/export-kenya-go-live.sh
```

**Direct (any OS):**
```bash
# From repo root
node docs/user-manual/pdf-export/generate-kenya-pdf.mjs
```

Output: `docs/user-manual/pdf-output/Kenya-Go-Live-ERP-Training-Manual.pdf`

The `pdf-output/` folder is gitignored. Regenerate locally before printing or distributing.

## Regenerate Screenshots First (if missing)

```bash
# From frontend/
E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots
```

Screenshots are required for the PDF to include images. The PDF generates without screenshots but images will be broken.

## Source Files (in order)

| File | Chapter |
|------|---------|
| `kenya-go-live/00_GO_LIVE_TRAINING_INDEX.md` | Cover + Training Index |
| `kenya-go-live/01_ADMIN_USER_MANUAL.md` | Admin User Manual |
| `kenya-go-live/02_PRODUCTION_USER_MANUAL.md` | Production Manual |
| `kenya-go-live/03_WAREHOUSE_INVENTORY_USER_MANUAL.md` | Warehouse & Inventory |
| `kenya-go-live/04_PROCUREMENT_USER_MANUAL.md` | Procurement |
| `kenya-go-live/05_QUALITY_CONTROL_USER_MANUAL.md` | Quality Control |
| `kenya-go-live/06_SALES_LOGISTICS_USER_MANUAL.md` | Sales & Logistics |
| `kenya-go-live/07_HR_USER_MANUAL.md` | HR & Payroll |
| `kenya-go-live/08_MANAGER_DASHBOARD_USER_MANUAL.md` | Manager Dashboard |
| `kenya-go-live/09_COMMON_PROBLEMS_AND_FAQ.md` | Common Problems & FAQ |

## Files in This Folder

| File | Purpose |
|------|---------|
| `generate-kenya-pdf.mjs` | Main PDF generation script |
| `export-kenya-go-live.ps1` | Windows PowerShell wrapper with validation |
| `export-kenya-go-live.sh` | Bash wrapper with validation |
| `pdf-style.css` | A4 print stylesheet |
| `README.md` | This file |

## Known Limitations

- PDF output requires Playwright Chromium to be installed (runs automatically with `npm install` in `frontend/`).
- Screenshots are gitignored (~70 MB). Must exist locally for images to appear in the PDF.
- `marked` must be installed in `frontend/node_modules/` (`npm install --save-dev marked`).
- File paths use `file:///` absolute URIs for images — PDF is not portable across machines unless screenshots are embedded.
- On first run Playwright may need to download the Chromium browser binary.

## Next Recommended PDF

After Kenya manual is confirmed correct:

```bash
# Full ERP Reference Manual (all 13 chapters)
# Script TBD — run after Kenya manual is reviewed and approved
node docs/user-manual/pdf-export/generate-full-reference-pdf.mjs
```
