# Finance

**URL:** `/dashboard/finance`  
**Module:** Finance  
**Permission:** `finance.view`

---

## Screenshot

> Screenshot pending: Finance workspace overview

---

## Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | — | P&L and cash position summary |
| Accounting | ?tab=accounting | Chart of accounts, journal entries |
| Cashbook | ?tab=cashbook | Cash and petty cash |
| Receivables | ?tab=receivables | Accounts receivable ageing |
| Budget | ?tab=budget | Budget vs actual |
| M-Pesa | ?tab=mpesa | M-Pesa reconciliation |
| Costing | ?tab=costing | Product costing |
| Exchange Rates | ?tab=exchange-rates | FX rate management |
| eTIMS | ?tab=etims | KRA e-invoice status |
| VAT Returns | ?tab=vat-returns | VAT filing preparation |
| Bank Recon | ?tab=bank-recon | Bank statement matching |
| Invoice Match | ?tab=invoice-match | PO/GRN/invoice 3-way match |
| Fixed Assets | ?tab=fixed-assets | Asset register, depreciation |
| Dimensions | ?tab=dimensions | Cost centre / department codes |
| Dunning | ?tab=dunning | Overdue collection letters |
| Tax | ?tab=tax | Tax setup and filing |
| Bank API | ?tab=bank-api | Bank statement auto-import |
| Expenses | ?tab=expenses | Employee expense claims |

---

## Kenya-Specific Finance Features

**eTIMS:** Electronic Tax Invoice Management System — mandatory for VAT-registered companies  
**M-Pesa:** Mobile money reconciliation and payment processing  
**VAT returns:** Automated VAT return calculation for KRA filing  
**Housing Levy:** 1.5% employer + 1.5% employee on gross salary (2024 requirement)

---

## 3-Way Matching

Purchase Invoice → Goods Receipt Note → Purchase Order  
All three must match before an invoice is approved for payment. Discrepancies are flagged in Invoice Match tab.

---

## Bank Reconciliation

1. Import bank statement (CSV/OFX) or use Bank API auto-import
2. System matches transactions to ERP entries automatically
3. Review unmatched items manually
4. Post any missing entries
5. Mark reconciliation as complete

---

## Fixed Assets

Full asset lifecycle:
- Capitalization, depreciation (straight-line or reducing balance)
- Asset revaluation
- Disposal and write-off
- Depreciation schedules linked to GL accounts

---

## Related Workspaces

- Sales (Collections tab) — receivables source
- Procurement (Deliveries tab) — payables source
- HR (Payroll) — payroll journal posts to Finance
- Admin (Integrations) — M-Pesa and bank API config
