# FMCG ERP — Finance & Payroll Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Finance Managers, Accountants, Payroll Officers, Tax Compliance Teams  
**Modules Covered:** Finance · Cashbook · Payroll · Expenses · Fixed Assets · Bank Reconciliation · Tax/eTIMS · Contracts · Invoice Matching

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Finance Hub](#2-finance-hub)
3. [Cashbook & Accounts](#3-cashbook--accounts)
4. [Accounts Receivable](#4-accounts-receivable)
5. [Budgeting](#5-budgeting)
6. [M-Pesa Integration](#6-m-pesa-integration)
7. [Production Costing](#7-production-costing)
8. [Exchange Rates](#8-exchange-rates)
9. [eTIMS (KRA Tax Compliance)](#9-etims-kra-tax-compliance)
10. [VAT Returns](#10-vat-returns)
11. [Bank Reconciliation](#11-bank-reconciliation)
12. [Invoice Matching](#12-invoice-matching)
13. [Fixed Assets](#13-fixed-assets)
14. [Payroll](#14-payroll)
15. [Expenses](#15-expenses)
16. [Tax Management](#16-tax-management)
17. [Financial Contracts](#17-financial-contracts)
18. [Common Mistakes & Troubleshooting](#18-common-mistakes--troubleshooting)
19. [Related Modules](#19-related-modules)

---

## 1. Module Overview

**What it does:** Complete financial management — chart of accounts, journals, cashbook, accounts payable/receivable, payroll, budgeting, tax compliance (eTIMS/VAT), bank reconciliation, and fixed asset management.

**Who uses it:**
- Finance Manager — oversees accounts, approves journals, reviews reports
- Accountant — posts journals, reconciles bank, manages AP/AR
- Payroll Officer — runs monthly payroll, manages employee salary profiles
- Tax Officer — manages eTIMS submissions, VAT returns, withholding tax

**When to use it:**
- Monthly payroll processing
- Daily cashbook entries and bank reconciliation
- Invoice matching after goods receipt
- eTIMS submission for customer invoices
- VAT return preparation
- Fixed asset depreciation runs
- Budget vs. actual monitoring

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| Finance | `/dashboard/finance` | Full finance workspace |
| Payroll | `/dashboard/payroll` | Employee payroll |
| Expenses | `/dashboard/expenses` | Expense claims |
| Fixed Assets | `/dashboard/fixed-assets` | Asset register and depreciation |
| Bank Reconciliation | `/dashboard/bank-reconciliation` | Bank statement matching |
| Bank API | `/dashboard/bank-api` | Bank feed integration |
| Tax | `/dashboard/tax` | Tax management |
| Contracts | `/dashboard/contracts` | Financial contracts |
| Invoice Match | `/dashboard/invoice-match` | AP invoice matching |

![Finance Overview](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/overview-tab.png)
*Finance hub overview — KPIs, recent transactions, and module shortcuts.*

---

## 2. Finance Hub

**Route:** `/dashboard/finance`  
**Required permission:** `finance.view`

### Tabs

| Tab | Purpose |
|-----|---------|
| Overview | Finance KPI dashboard |
| Accounting | Chart of accounts and journal entries |
| Cashbook | Cash and bank account management |
| Receivables | Customer outstanding balances |
| Budget | Budget planning and variance |
| M-Pesa | M-Pesa transaction reconciliation |
| Costing | Production cost allocation |
| Exchange Rates | Multi-currency exchange rate management |
| eTIMS | KRA eTIMS submission log |
| VAT Returns | VAT return preparation |
| Bank Recon | Bank reconciliation workspace |
| Invoice Match | Supplier invoice matching |
| Fixed Assets | Asset register link |
| Dimensions | Financial dimensions/cost centres |
| Dunning | Overdue customer payment follow-up |
| Tax | Tax code configuration |
| Bank API | Bank feed settings |
| Expenses | Expense claim management |

### Accounting Tab

![Accounting Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/accounting-tab.png)
*Accounting module — chart of accounts, journal entries, and trial balance.*

**Chart of Accounts structure:**
- Assets (1xxx)
- Liabilities (2xxx)
- Equity (3xxx)
- Revenue (4xxx)
- Cost of Sales (5xxx)
- Expenses (6xxx)

**Posting a Journal Entry:**
1. Accounting tab → **+ New Journal**
2. Set journal date and reference
3. Add debit lines and credit lines (must balance)
4. Attach supporting documents
5. Submit for approval (if approval chain configured)
6. Approve → journal posted; entries reflected in trial balance

---

## 3. Cashbook & Accounts

**Route:** `/dashboard/cashbook` (also accessible via Finance → Cashbook tab)

### What it does
Manages cash accounts, petty cash, bank accounts, and transactions. Records receipts and payments not covered by the AP/AR modules.

![Cashbook Accounts Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/cashbook/accounts-tab.png)
*Cashbook accounts — bank accounts and petty cash funds.*

### Creating a Cashbook Account

Click **+ New Account**:

![New Account Modal](../../user-manual/screenshots/captured/module-ui/finance-payroll/cashbook/new-account-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Account Name | Yes | e.g. "Stanbic Current Account" |
| Account Type | Yes | Bank / Petty Cash / Mobile Money |
| Currency | Yes | KES, USD, etc. |
| Opening Balance | No | Balance at go-live date |
| Bank Name | No | For bank accounts |
| Account Number | No | Bank account number |
| Branch | No | Bank branch |

**Account Type Dropdown:**

![Account Type Dropdown](../../user-manual/screenshots/captured/module-ui/finance-payroll/cashbook/account-type-dropdown.png)

### Cashbook Transactions Tab

![Transactions Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/cashbook/transactions-tab.png)
*Transaction history — all receipts and payments with running balance.*

### Journal Tab

![Journal Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/cashbook/journal-tab.png)
*Cashbook journal entries — linked to general ledger.*

---

## 4. Accounts Receivable

**Tab:** Receivables

![Receivables Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/receivables-tab.png)
*Accounts receivable — outstanding customer invoices by age bucket.*

**Aging buckets:** Current · 1–30 days · 31–60 days · 61–90 days · 90+ days

**Dunning Tab:**

![Dunning Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/dunning-tab.png)
*Dunning — automated overdue payment reminders by level (friendly → formal → legal).*

**Dunning workflow:**
1. System flags invoices past due date
2. Level 1 reminder sent at 7 days overdue (automated email)
3. Level 2 at 30 days (formal notice)
4. Level 3 at 60 days (legal/collections)
5. Manually escalate or resolve from Dunning tab

---

## 5. Budgeting

**Tab:** Budget

![Budget Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/budget-tab.png)
*Budget management — define annual budget by account and cost centre, track variances monthly.*

**Budget workflow:**
1. Create budget for financial year
2. Distribute across periods (monthly)
3. Assign to accounts and cost centres
4. Monitor actual vs. budget in real-time
5. Budget amendments require finance manager approval

---

## 6. M-Pesa Integration

**Tab:** M-Pesa

![M-Pesa Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/mpesa-tab.png)
*M-Pesa transactions — incoming and outgoing M-Pesa payments, auto-matching to invoices.*

**Auto-matching:** M-Pesa transactions with invoice reference numbers are auto-matched. Unmatched transactions appear in the **Unmatched** sub-tab for manual allocation.

See also: Finance → Integrations M-Pesa tab (`/dashboard/integrations/mpesa`) for API configuration.

---

## 7. Production Costing

**Tab:** Costing

![Costing Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/costing-tab.png)
*Production cost allocation — material, labor, and overhead cost per production order.*

Links to Manufacturing → Production → Costing tab for drill-down detail.

---

## 8. Exchange Rates

**Tab:** Exchange Rates

![Exchange Rates Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/exchange-rates-tab.png)
*Exchange rate management — maintain rates for multi-currency transactions.*

Update rates daily or weekly. Historic rates retained for revaluation and reporting. Supports: KES, USD, EUR, GBP, ZAR, UGX, TZS, ETB.

---

## 9. eTIMS (KRA Tax Compliance)

**Tab:** eTIMS  
**Route:** `/dashboard/etims`

![eTIMS Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/etims-tab.png)
*eTIMS submission log — KRA invoice submissions, status, and error handling.*

### What it does
Submits customer invoices to KRA's Electronic Tax Invoice Management System as required by Kenyan law.

### eTIMS Workflow
1. Customer invoice posted in Sales
2. System automatically queues for eTIMS submission
3. eTIMS tab shows: PENDING → SUBMITTED → ACCEPTED / REJECTED
4. Accepted invoices receive KRA control unit number
5. Rejected invoices show error code — fix and resubmit

### Common eTIMS errors
| Code | Meaning | Fix |
|------|---------|-----|
| E001 | Customer PIN invalid | Update customer PIN in Customers master |
| E002 | Product description too long | Shorten line item description to <50 chars |
| E003 | Invoice date in future | Check system date/time; use today's date |
| E004 | Duplicate invoice number | Invoice number already submitted; void and reissue |

---

## 10. VAT Returns

**Tab:** VAT Returns

![VAT Returns Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/vat-returns-tab.png)
*VAT return workspace — standard rated, zero rated, exempt, and input VAT summary per period.*

**VAT return workflow:**
1. Select tax period (month)
2. System computes: Output VAT (from sales invoices) - Input VAT (from purchase invoices)
3. Review line-by-line breakdown
4. Export to KRA iTax format (CSV/XML)
5. Submit on iTax portal (manual step — not auto-submitted)
6. Record submission reference number in ERP

---

## 11. Bank Reconciliation

**Route:** `/dashboard/bank-reconciliation`

![Bank Reconciliation Dashboard](../../user-manual/screenshots/captured/module-ui/finance-payroll/bank-reconciliation/bank-recon-dashboard.png)
*Bank reconciliation — match ERP transactions to bank statement lines.*

**Reconciliation workflow:**
1. Download bank statement (CSV/OFX from bank)
2. Import statement in Bank Recon module
3. System auto-matches transactions by amount and date
4. Manually match unmatched items
5. Post adjustments for bank charges, interest
6. Close period when fully reconciled

**Bank API Tab (auto-import):**

![Bank API Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/bank-api-tab.png)
*Bank API integration — automated bank statement import via open banking APIs.*

![Bank API Page](../../user-manual/screenshots/captured/module-ui/finance-payroll/bank-api/bank-api-page.png)

![Bank API Dropdowns](../../user-manual/screenshots/captured/module-ui/finance-payroll/bank-api/bank-api-dropdowns.png)
*Bank API settings — select bank, set sync frequency, and configure credentials.*

---

## 12. Invoice Matching

**Route:** `/dashboard/invoice-match`

![Invoice Match Dashboard](../../user-manual/screenshots/captured/module-ui/finance-payroll/invoice-match/invoice-match-dashboard.png)
*Invoice matching — 3-way match of PO, GRN, and supplier invoice.*

### 3-Way Match
Each supplier invoice must match:
1. Purchase Order (approved price and quantity)
2. Goods Receipt Note (what was actually received)
3. Supplier Invoice (amount billed)

**Tolerance:** Configurable tolerance (e.g. ±2% or ±KES 500) before requiring manual approval.

**Match statuses:**
| Status | Meaning |
|--------|---------|
| AUTO_MATCHED | All 3 documents match within tolerance |
| REVIEW | Discrepancy outside tolerance — requires approval |
| EXCEPTION | Missing GRN or PO — cannot match |
| POSTED | Approved and posted to AP |

---

## 13. Fixed Assets

**Route:** `/dashboard/fixed-assets`

![Fixed Assets Dashboard](../../user-manual/screenshots/captured/module-ui/finance-payroll/fixed-assets/fixed-assets-dashboard.png)
*Fixed asset register — assets, net book value, depreciation schedule.*

### Asset lifecycle
1. **Create asset** — enter purchase cost, useful life, depreciation method
2. **Capitalize** — post capitalization journal
3. **Depreciate** — run monthly depreciation (straight-line or reducing balance)
4. **Revalue** (if applicable) — enter revaluation amount
5. **Dispose** — record sale or write-off; post disposal gain/loss

**Depreciation methods:** Straight Line / Reducing Balance / Units of Production

---

## 14. Payroll

**Route:** `/dashboard/payroll`  
**Required permission:** `payroll.view`

### What it does
Process monthly payroll — calculate gross pay, deductions (PAYE, NSSF, NHIF/SHIF, NITA), net pay, and generate payslips.

![Payroll Overview](../../user-manual/screenshots/captured/module-ui/finance-payroll/payroll/overview-tab.png)
*Payroll overview — current period status, total payroll cost, and run controls.*

### Payroll Profiles Tab

![Profiles Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/payroll/profiles-tab.png)
*Payroll profiles — employee salary structures, allowances, and deductions.*

**Each profile contains:**
- Basic salary
- Allowances (house, transport, commuter)
- Statutory deductions (PAYE, NSSF, NHIF/SHIF, NITA)
- Other deductions (loans, advances, pension)
- Tax relief (personal relief, insurance relief)

### Payroll Run — Step by Step

1. Go to Payroll → **New Payroll Period**

![New Period Form](../../user-manual/screenshots/captured/module-ui/finance-payroll/payroll/new-period-form.png)

![Payroll Month Dropdown](../../user-manual/screenshots/captured/module-ui/finance-payroll/payroll/payroll-month-dropdown.png)

2. Select month and year
3. Click **Generate** — system calculates for all active employees
4. Review exceptions (missing profiles, mid-month joiners, leavers)
5. Process adjustments (overtime, bonuses, deductions)
6. **Preview** payroll summary
7. **Approve** payroll — triggers payslip generation
8. **Post** payroll — creates GL journal entries (salaries payable)
9. **Pay** — trigger bank transfer file / M-Pesa bulk payment
10. Mark as **Paid** — payslips accessible to employees via ESS

### Payroll Reports Tab

![Payroll Reports](../../user-manual/screenshots/captured/module-ui/finance-payroll/payroll/reports-tab.png)
*Payroll reports — payslips, PAYE returns, NSSF/NHIF schedules, bank payment file.*

**Statutory reports generated:**
- P9 form (PAYE annual summary per employee)
- NSSF contribution schedule
- NHIF/SHIF contribution schedule
- NITA levy return

---

## 15. Expenses

**Route:** `/dashboard/expenses`

![Expenses Dashboard](../../user-manual/screenshots/captured/module-ui/finance-payroll/expenses/expenses-dashboard.png)
*Expense claims — submit, approve, and reimburse employee expenses.*

**Expense workflow:**
1. Employee submits expense claim (category, amount, receipt upload)
2. Manager reviews and approves/rejects
3. Finance approves for payment
4. Reimbursement via payroll or direct payment

---

## 16. Tax Management

**Route:** `/dashboard/tax`

![Tax Dashboard](../../user-manual/screenshots/captured/module-ui/finance-payroll/tax/tax-dashboard.png)
*Tax dashboard — all tax obligations with due dates and filing status.*

**Tax types tracked:**
- VAT (16% standard, 0% zero-rated, exempt)
- PAYE (employee income tax)
- WHT (withholding tax on services)
- Corporate income tax provisions
- Turnover tax (TOT) for applicable entities

**Tax Tab in Finance:**

![Tax Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/tax-tab.png)
*Tax code configuration — define tax rates and rules for sales and purchase transactions.*

---

## 17. Financial Contracts

**Route:** `/dashboard/contracts`

![Contracts Dashboard](../../user-manual/screenshots/captured/module-ui/finance-payroll/contracts/contracts-dashboard.png)
*Financial contracts — supplier and customer long-term agreements with payment schedules.*

**Contract types:** Lease / Service Agreement / Loan / Framework / License

**Dimensions Tab:**

![Dimensions Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/dimensions-tab.png)
*Financial dimensions — cost centres, projects, and departments for GL tagging.*

---

## 18. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Journal won't post | Debits ≠ Credits | Balance the journal — total debit must equal total credit |
| eTIMS rejection | Customer PIN missing | Add PIN in Sales → Customers → Tax Details tab |
| Payroll generates wrong PAYE | Employee tax profile out of date | Update payroll profile before running; check tax bands |
| Bank recon has unmatched items | Bank charges not in ERP | Post bank charge journal; then re-run auto-match |
| Invoice match exception | No GRN created for PO | Complete goods receipt in Procurement → Deliveries |
| Fixed asset not depreciating | Asset not activated | Set asset status to Active and set capitalization date |
| VAT return mismatch | Credit notes not posted | Ensure all credit notes are posted before period close |

---

## 19. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Goods receipt (GRN) | Invoice Match → 3-way match |
| Sales invoice posted | eTIMS submission + AR aging |
| Customer payment | Bank Reconciliation + AR clearance |
| Payroll approved | GL journal (Salaries payable) |
| Production work order | Costing → actual cost capture |
| Expense approved | Payroll (reimbursement) or Bank Payment |

---

*End of Finance & Payroll Manual v2*
