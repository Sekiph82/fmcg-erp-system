# PDF Export Plan

**Date:** 2026-05-18  
**Status:** Design only — PDF generation not yet implemented

---

## Goal

Convert Markdown manuals to printable, distributable PDF documents for:
- Classroom training sessions
- Desk reference guides
- Offline field use

---

## Recommended Tool

**Pandoc** + **wkhtmltopdf** or **WeasyPrint**

Alternative: `md-to-pdf` npm package (simpler, Node-native)

```bash
# Pandoc with wkhtmltopdf (best PDF quality)
pandoc docs/user-manual/kenya-go-live/02_PRODUCTION_USER_MANUAL.md \
  --pdf-engine=wkhtmltopdf \
  --resource-path=docs/user-manual \
  -V geometry:a4paper \
  -V margin-top=20mm -V margin-bottom=20mm \
  -o dist/PRODUCTION_MANUAL.pdf

# md-to-pdf (simpler, no external binary)
npx md-to-pdf docs/user-manual/kenya-go-live/02_PRODUCTION_USER_MANUAL.md
```

---

## Folder Order (Full Reference PDF)

```
1. Cover page + table of contents
2. full-reference/01_DASHBOARD_AND_NAVIGATION.md
3. full-reference/02_MASTER_DATA.md
4. full-reference/03_PROCUREMENT.md
5. full-reference/04_INVENTORY_AND_WAREHOUSE.md
6. full-reference/05_PRODUCTION.md
7. full-reference/06_QUALITY_AND_COMPLIANCE.md
8. full-reference/07_SALES_AND_DISTRIBUTION.md
9. full-reference/08_FINANCE.md
10. full-reference/09_HR_AND_PAYROLL.md
11. full-reference/10_ADMIN_AND_SECURITY.md
12. full-reference/11_AI_AND_AUTOMATION.md
13. full-reference/12_REPORTS_AND_EXPORTS.md
14. full-reference/13_STANDALONE_OPERATIONAL_PAGES.md
15. full-reference/14_OLD_ROUTE_COMPATIBILITY.md
```

---

## Image Handling

Pandoc resolves image paths relative to the Markdown file.  
Screenshot paths in Markdown: `../screenshots/captured/001_login.png`  
Pass `--resource-path=docs/user-manual` to help Pandoc locate images.

---

## Page Size

A4 (210mm × 297mm)  
Margins: 20mm all sides  
Font: Arial or system default sans-serif

---

## Cover Page

Create `docs/user-manual/templates/COVER_PAGE.md`:
```markdown
# FMCG ERP User Manual
**Version:** {version}  
**Date:** {date}  
**Role:** {role}  
**Confidential — Internal Use Only**
```

---

## Table of Contents

Pandoc generates TOC automatically:
```bash
pandoc ... --toc --toc-depth=2
```

---

## Role-Based Separate PDFs

| File | Audience | Pages (est.) |
|---|---|---|
| ADMIN_MANUAL.pdf | IT Admin | ~30 |
| PRODUCTION_MANUAL.pdf | Production staff | ~40 |
| WAREHOUSE_MANUAL.pdf | Warehouse/Inventory | ~35 |
| PROCUREMENT_MANUAL.pdf | Procurement | ~25 |
| QUALITY_MANUAL.pdf | QC/QA | ~25 |
| SALES_LOGISTICS_MANUAL.pdf | Sales/Logistics | ~35 |
| HR_MANUAL.pdf | HR | ~30 |
| MANAGER_MANUAL.pdf | Managers | ~20 |
| FULL_ERP_REFERENCE.pdf | All roles | ~250 |

---

## Screenshot Compression

Before PDF export, compress screenshots if large:
```bash
# Using ImageMagick
mogrify -quality 70 docs/user-manual/screenshots/captured/*.png
```

Target: < 300 KB per image in PDF.

---

## Filename/Versioning Convention

```
dist/
├── FMCG_ERP_PRODUCTION_MANUAL_v1.0_2026-05-18.pdf
├── FMCG_ERP_WAREHOUSE_MANUAL_v1.0_2026-05-18.pdf
└── FMCG_ERP_FULL_REFERENCE_v1.0_2026-05-18.pdf
```

Version format: `v{major}.{minor}` — increment minor for content updates, major for major UI changes.

---

## npm Script (Future)

Add to `package.json` (root level):
```json
{
  "scripts": {
    "manual:pdf:production": "pandoc docs/user-manual/kenya-go-live/02_PRODUCTION_USER_MANUAL.md --pdf-engine=wkhtmltopdf -V geometry:a4paper -o dist/PRODUCTION_MANUAL.pdf",
    "manual:pdf:all": "node scripts/export-all-manuals.mjs"
  }
}
```

---

## Do Not Generate PDF Yet

Do not generate PDFs until:
1. Screenshots are captured and reviewed
2. Manual content is reviewed by Kenya operations team
3. PDF tool is confirmed installed on build machine
