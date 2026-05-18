# ERP User Manual — Screenshot-Based Strategy

**Date:** 2026-05-18  
**Project:** FMCG ERP — Kenya Go-Live  
**Status:** Active — screenshot capture in progress

---

## 1. Why a Screenshot Manual is Needed for Kenya Go-Live

Kenya production staff will use this ERP from day one. They have no prior ERP experience. Without a concrete visual reference, support load on IT/admin will be extremely high and operational errors will increase during the critical first weeks.

A screenshot-based manual provides:
- A visual walkthrough matching exactly what staff see on screen
- Self-service troubleshooting ("my screen looks like this — what do I click?")
- Training material for classroom and on-the-job coaching
- Reference for approvals and data entry workflows specific to Kenya operations (M-Pesa, PAYE, NHIF, eTIMS)

---

## 2. Recommended Manual Structure

```
docs/user-manual/
├── kenya-go-live/          # Role-based go-live training manuals
│   ├── 00_GO_LIVE_TRAINING_INDEX.md
│   ├── 01_ADMIN_USER_MANUAL.md
│   ├── 02_PRODUCTION_USER_MANUAL.md
│   ├── 03_WAREHOUSE_INVENTORY_USER_MANUAL.md
│   ├── 04_PROCUREMENT_USER_MANUAL.md
│   ├── 05_QUALITY_CONTROL_USER_MANUAL.md
│   ├── 06_SALES_LOGISTICS_USER_MANUAL.md
│   ├── 07_HR_USER_MANUAL.md
│   ├── 08_MANAGER_DASHBOARD_USER_MANUAL.md
│   └── 09_COMMON_PROBLEMS_AND_FAQ.md
├── full-reference/         # Complete page-by-page reference
│   ├── 00_FULL_ERP_MANUAL_INDEX.md
│   ├── 01_DASHBOARD_AND_NAVIGATION.md
│   ├── 02_MASTER_DATA.md
│   ├── 03_PROCUREMENT.md
│   ├── 04_INVENTORY_AND_WAREHOUSE.md
│   ├── 05_PRODUCTION.md
│   ├── 06_QUALITY_AND_COMPLIANCE.md
│   ├── 07_SALES_AND_DISTRIBUTION.md
│   ├── 08_FINANCE.md
│   ├── 09_HR_AND_PAYROLL.md
│   ├── 10_ADMIN_AND_SECURITY.md
│   ├── 11_AI_AND_AUTOMATION.md
│   ├── 12_REPORTS_AND_EXPORTS.md
│   ├── 13_STANDALONE_OPERATIONAL_PAGES.md
│   └── 14_OLD_ROUTE_COMPATIBILITY.md
├── screenshots/
│   ├── routes.json                 # Capture targets (workspace-based)
│   ├── screenshots-index.json      # Capture results with status
│   └── captured/                   # PNG files (001_login.png, etc.)
└── templates/
    └── PAGE_MANUAL_TEMPLATE.md
```

---

## 3. What Kenya Staff Need Before Production Starts

Priority 1 (before go-live day):
- [ ] Admin: system configured, users created, roles assigned
- [ ] Admin: company info, timezone (Africa/Nairobi), currency (KES), logo
- [ ] Admin: M-Pesa integration configured
- [ ] Production: BOM/recipes loaded for all active SKUs
- [ ] Inventory: opening stock counted and entered
- [ ] Warehouses: zones and locations created in WMS
- [ ] HR: all employees created with payroll profiles
- [ ] Finance: chart of accounts set up, opening balances

Priority 2 (first week):
- [ ] Sales: customer master loaded, price lists created
- [ ] Procurement: supplier master loaded, preferred suppliers set
- [ ] Quality: inspection parameters defined per product

---

## 4. Staff Roles Needing Manuals

| Role Group | Who | Priority |
|---|---|---|
| Admin / IT | System administrator, IT manager | 1 |
| Production | Factory supervisors, production operators, shift leaders | 1 |
| Warehouse / Inventory | Store keepers, receiving clerks, WMS operators | 1 |
| Procurement | Purchasing officers, procurement manager | 1 |
| Quality Control | QC technicians, lab analysts, QA manager | 1 |
| Sales / Logistics | Sales reps, invoicing clerks, logistics coordinator | 1 |
| HR | HR officer, payroll clerk | 1 |
| Managers | Department heads, MD, finance director | 2 |

---

## 5. Critical Modules for Go-Live (Must Work Day 1)

| Module | Why Critical |
|---|---|
| User management / Admin | Staff must be able to log in |
| Production orders | Core manufacturing workflow |
| Inventory / Stock | Must know stock at all times |
| WMS receiving | All incoming goods must be captured |
| Procurement / GRN | Purchase orders and goods receipt |
| Sales orders | Revenue processing |
| Van sales | Kenya distribution model heavily route-based |
| HR / Payroll | PAYE, NHIF, NSSF compliance from day 1 |
| Finance / M-Pesa | Kenya-specific payment collection |
| Quality inspections | Food safety / regulatory requirement |

---

## 6. Modules That Can Wait (Post Go-Live Phase 2)

| Module | Reason |
|---|---|
| AI / NL Commands | Requires OpenAI/Anthropic keys, not day-1 critical |
| eTIMS live calls | KRA integration—go live with placeholder, enable later |
| WhatsApp | Twilio config needed, not critical path |
| IoT / MQTT streaming | Hardware integration, separate project |
| NPD | New product development, not operational |
| ESG Reporting | Compliance reporting, not day-1 |
| Market Intelligence | Analytics feature, not operational |
| Advanced MRP/MPS simulation | Useful but can be set up in week 2 |

---

## 7. Screenshot Capture Route List

Source: `docs/user-manual/screenshots/routes.json`

Routes selected are:
- Real consolidated workspace URLs (e.g., `/dashboard/production`)
- Real tab query parameters (e.g., `?tab=orders`)
- NOT old redirect paths (e.g., `/dashboard/van-sales` redirects to `/dashboard/sales?tab=van-sales`)

Total capture targets: ~140 routes
Priority 1 (go-live critical): ~60 routes
Priority 2 (important): ~50 routes
Priority 3 (reference): ~30 routes

---

## 8. Old Redirect Routes — Policy

Old routes (e.g., `/dashboard/van-sales`, `/dashboard/qms`, `/dashboard/fixed-assets`) redirect via middleware to the consolidated workspace. These must NOT become duplicate screenshot targets.

Policy:
- Document old route in `full-reference/14_OLD_ROUTE_COMPATIBILITY.md`
- Do not capture screenshots for redirect-only paths
- Manual text says: "If you bookmarked `/dashboard/van-sales`, it now opens the Sales workspace Van Sales tab"

---

## 9. Screenshot Requirements

- Viewport: 1440 × 900 desktop
- Format: PNG
- Full page: false (capture visible viewport only for workspace screenshots)
- Full page: true only for long settings or template pages if useful
- Auth: logged in as admin (admin@erp.local / Admin1234! username: admin)
- Wait for: `h1` visible, no error overlay, no 404
- Hide: N/A (no sensitive data expected on demo stack)
- Fail capture if: Next.js error overlay, 404 text, login redirect

---

## 10. Screenshot Naming Convention

```
{3-digit-sequence}_{module}_{tab-or-page}.png
```

Examples:
```
001_login.png
002_dashboard.png
003_admin.png
004_admin_users.png
005_admin_roles.png
020_production.png
021_production_orders.png
022_production_execution.png
```

Sequence is derived from order in `routes.json`. Names must be stable across re-captures.

---

## 11. Folder Structure

```
docs/user-manual/screenshots/
├── routes.json               # Source of truth for capture targets
├── screenshots-index.json    # Output: status, path, capturedAt per screenshot
└── captured/                 # Actual PNG files
    ├── 001_login.png
    ├── 002_dashboard.png
    └── ...
```

---

## 12. Training Schedule Recommendation

| Week | Audience | Content |
|---|---|---|
| -2 (before go-live) | Admin / IT | System setup, user creation, role assignment |
| -2 | HR | Employee setup, payroll profiles |
| -1 | Production supervisors | BOM review, production order flow |
| -1 | Warehouse / receiving | WMS setup, goods receipt, stock count |
| -1 | Procurement | Supplier setup, PO flow, GRN |
| -1 | Quality | Inspection setup, allergen matrix |
| Go-live week | Sales / Logistics | Order entry, invoicing, van sales |
| Go-live week | All | Troubleshooting, FAQ |
| +1 week | Managers | Dashboard, reports, approvals |
| +2 weeks | All | Advanced features, AI, analytics |

---

## 13. Best Format

| Format | Use Case | Priority |
|---|---|---|
| Role-based PDF | Print training guide, offline reference | 1 |
| Web manual (Markdown / HTML) | Searchable online reference, link from ERP | 2 |
| Role-based quick guide (1-2 pages) | Laminated desk reference | 1 |
| In-app Help links | Context-sensitive help from each page | 3 |
| Training videos | Complex workflows (van sales, payroll run) | Post go-live |

---

## 14. How Screenshots Are Used in Markdown Manuals

Reference syntax in Markdown:
```markdown
![Production Orders screen](../screenshots/captured/021_production_orders.png)
```

If screenshot not yet captured:
```markdown
> Screenshot pending: production orders tab
```

Never include placeholder images that pretend to be real screenshots.

---

## 15. PDF Export Plan

See `docs/user-manual/PDF_EXPORT_PLAN.md`.

Recommended tool: Pandoc + wkhtmltopdf or md-to-pdf.  
Separate PDF per role + one full ERP reference PDF.

---

## 16. In-App Help Plan

See `docs/user-manual/IN_APP_HELP_PLAN.md`.

Each workspace will link to its manual section via a `?` help button.

---

## 17. Risks if Manual is Delayed

| Risk | Impact |
|---|---|
| Staff data entry errors | Wrong stock, wrong orders, financial reconciliation problems |
| High IT support load | IT team overwhelmed from day 1 |
| Low adoption | Staff revert to spreadsheets |
| Audit compliance gap | Incomplete process records |
| Kenya-specific gaps | M-Pesa, PAYE, NHIF, eTIMS not documented = compliance errors |

---

## 18. Recommended Next Implementation Steps

1. Run `npm run test:manual-screenshots` to capture all priority-1 routes
2. Review screenshots — retake any blank/error captures
3. Export Kenya go-live PDFs per role using Pandoc
4. Print and laminate quick guides for production floor
5. Wire in-app `?` help button to manual sections (admin workspace first)
6. Schedule training sessions per role group
7. Collect feedback after week 1, update FAQ section
