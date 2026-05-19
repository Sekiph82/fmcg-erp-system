# Finance & Payroll Module — Overview

**Primary route:** `/dashboard/finance`  
**Payroll route:** `/dashboard/payroll`  
**Permission required:** `finance.view` (Finance), `payroll_ke.view` (Payroll)

---

## What This Module Covers

The Finance & Payroll module manages all money-in and money-out flows for the business. It encompasses cash management, double-entry accounting, M-Pesa reconciliation, receivables tracking, budget control, tax compliance, bank reconciliation, fixed assets, expenses, and Kenya statutory payroll.

| Sub-module | Route | Permission |
|---|---|---|
| Finance Overview | `/dashboard/finance?tab=overview` | `finance.view` |
| Accounting | `/dashboard/finance?tab=accounting` | `finance.view` |
| Cashbook | `/dashboard/finance?tab=cashbook` | `finance.view` |
| Receivables | `/dashboard/finance?tab=receivables` | `finance.view` |
| Budget | `/dashboard/finance?tab=budget` | `finance.view` |
| M-Pesa | `/dashboard/finance?tab=mpesa` | `finance.view` |
| Costing | `/dashboard/finance?tab=costing` | `finance.view` |
| Exchange Rates | `/dashboard/finance?tab=exchange-rates` | `finance.view` |
| eTIMS | `/dashboard/finance?tab=etims` | `finance.view` |
| VAT Returns | `/dashboard/finance?tab=vat-returns` | `finance.view` |
| Bank Reconciliation | `/dashboard/finance?tab=bank-recon` | `finance.view` |
| Invoice Match | `/dashboard/finance?tab=invoice-match` | `finance.view` |
| Fixed Assets | `/dashboard/finance?tab=fixed-assets` | `finance.view` |
| Dimensions | `/dashboard/finance?tab=dimensions` | `finance.view` |
| Dunning | `/dashboard/finance?tab=dunning` | `finance.view` |
| Tax | `/dashboard/finance?tab=tax` | `finance.view` |
| Bank API | `/dashboard/finance?tab=bank-api` | `finance.view` |
| Expenses | `/dashboard/finance?tab=expenses` | `hr.view` |
| Payroll | `/dashboard/payroll` | `payroll_ke.view` |
| Contracts | `/dashboard/contracts` | `finance.view` |

---

## Key Data Flows

```
Sales Order → Sales Invoice → Receivables → Cash Receipt → Cashbook
Purchase Order → GRN → Purchase Invoice → Payables → Bank Payment → Bank Recon
Payroll Run → PAYE/NHIF/NSSF deductions → Finance Journal
Expenses Claim → Approval → Reimbursement payment
Fixed Asset → Depreciation schedule → Posting to General Ledger
```

---

## Kenya Statutory Compliance

The payroll engine implements Kenya Finance Act 2023/2024:
- **PAYE**: Progressive bands, personal relief
- **NHIF**: Social Health Authority (SHA) contribution
- **NSSF**: Tier I and Tier II contributions
- **AHL**: Affordable Housing Levy (1.5% employee + 1.5% employer)
- **eTIMS**: Electronic Tax Invoice Management System integration
- **VAT Returns**: VAT3 form generation for KRA filing
