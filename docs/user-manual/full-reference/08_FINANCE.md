# Finance

**URL:** `/dashboard/finance`  
**Module:** Finance  
**Permission:** `finance.view`

---

## Screenshot

![Finance Workspace](../screenshots/captured/087_finance.png)

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

**eTIMS:** Electronic Tax Invoice Management System — mandatory for VAT-registered companies. See below for current implementation status.
**M-Pesa:** Mobile money reconciliation and payment processing
**VAT returns:** Automated VAT return calculation for KRA filing
**Housing Levy:** 1.5% employer + 1.5% employee on gross salary (2024 requirement)

---

## eTIMS Implementation Status

eTIMS fiscalization uses a provider-neutral connector architecture. The connector is complete; live provider calls are not yet active.

### Current State

| Component | Status |
|---|---|
| Backend adapter interface (`ETIMSConnector` protocol) | Done |
| `SimulationETIMSConnector` (fake ACCEPTED; no network) | Done — active by default |
| `HttpETIMSConnector` skeleton | Skeleton only — auth scheme not yet wired |
| All fiscalization endpoints (prepare/submit/retry/cancel/poll/health) | Done |
| Frontend global eTIMS page (`/dashboard/finance/etims`) | Done — 10-status model, provider health panel, retry/cancel/poll |
| Frontend eTIMS card in invoice detail | Done — submit/retry/cancel/poll per invoice |
| `production_execution_allowed` | `false` — no live KRA calls |
| GL posting gate (require ACCEPTED before posting) | Not implemented — blocked on accountant decision |
| Live provider credentials | Not configured — requires KRA provider selection |

### eTIMS Status Values

10 statuses: `DRAFT`, `READY`, `PENDING`, `SUBMITTED`, `RETRY_PENDING`, `ACCEPTED`, `REJECTED`, `FAILED`, `ERROR`, `CANCELLED`

### What Users Can Do (Simulation Mode)

- View all eTIMS submissions and their status
- Submit, retry, cancel, and poll submissions (all routed to SimulationETIMSConnector)
- Check provider health
- View debug payload details per submission
- Access eTIMS card on individual invoice detail pages

### What Is Blocked Until Live Provider Configured

- Real KRA submission and fiscal acceptance
- GL posting gate enforcement
- Production eTIMS control numbers (`control_unit_invoice_no`)

> For full workflow and field reference, see the Finance-Payroll module manual: `module-manuals/finance-payroll/07-tax-etims.md`

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
