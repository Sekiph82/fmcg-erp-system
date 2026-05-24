# Manual Regeneration Cleanup Report

**Date:** 2026-05-24
**Status:** Complete

---

## Old PDFs Deleted (10)

| File | Location | Status |
|------|----------|--------|
| Kenya-Go-Live-ERP-Training-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Full-Reference-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Manufacturing-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Supply-Chain-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Finance-Payroll-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Sales-Distribution-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-HR-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Commercial-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Logistics-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |
| FMCG-ERP-Maintenance-Manual.pdf | docs/user-manual/pdf-output/ | DELETED |

**Reason deleted:** Pre-recovery PDFs. Button/link recovery (Wave 1A–2C) completed 2026-05-24. All broken action cards fixed. PDFs must be regenerated to reflect correct navigation.

---

## Screenshots Retained (470 total)

| Location | Count | Notes |
|----------|-------|-------|
| docs/user-manual/screenshots/captured/*.png | 140 | Standard workspace/tab screenshots |
| docs/user-manual/screenshots/captured/module-ui/ | 249 | Detailed module UI, modals, tabs |
| docs/user-manual/screenshots/captured/tabs/ | 57 | Tab-level screenshots |
| docs/user-manual/screenshots/captured/actions/ | 9 | Action/button screenshots |
| docs/user-manual/screenshots/captured/Captured by user manually/ | 15 | Manual captures |

**All 470 screenshots retained** — captured post-recovery (or compatible). Index shows 1 intentional skip (security — duplicate of admin-security).

---

## Scripts Retained

| Script | Purpose |
|--------|---------|
| `frontend/e2e/manual-screenshots.spec.ts` | Playwright screenshot capture (140 routes) |
| `frontend/e2e/manufacturing-ui-screenshots.spec.ts` | Manufacturing UI detailed capture |
| `frontend/e2e/supply-chain-ui-screenshots.spec.ts` | Supply chain UI detailed capture |
| `frontend/e2e/finance-payroll-ui-screenshots.spec.ts` | Finance/payroll UI capture |
| `frontend/e2e/sales-ui-screenshots.spec.ts` | Sales UI capture |
| `frontend/e2e/hr-ui-screenshots.spec.ts` | HR UI capture |
| `frontend/e2e/crm-ui-screenshots.spec.ts` | CRM/marketing UI capture |
| `frontend/e2e/logistics-ui-screenshots.spec.ts` | Logistics UI capture |
| `frontend/e2e/pos-ui-screenshots.spec.ts` | POS UI capture |
| `frontend/e2e/maintenance-ui-screenshots.spec.ts` | Maintenance UI capture |

---

## Source Files Retained (module manuals chapters)

| Directory | Files |
|-----------|-------|
| docs/user-manual/module-manuals/manufacturing/ | 13 chapter files |
| docs/user-manual/module-manuals/supply-chain/ | 11 chapter files |
| docs/user-manual/module-manuals/finance-payroll/ | 11 chapter files |
| docs/user-manual/module-manuals/sales/ | 8 chapter files |
| docs/user-manual/module-manuals/hr/ | 8 chapter files |
| docs/user-manual/kenya-go-live/ | 10 chapter files |
| docs/user-manual/full-reference/ | 14 chapter files |

---

## New Output Directories

```
docs/manuals/
├── manufacturing/
├── supply-chain/
├── sales-distribution/
├── commercial/
├── finance-payroll/
├── hr/
├── logistics/
├── maintenance/
├── documents/
├── admin/
├── intelligence/
├── kenya-go-live/
└── full-reference/
```
