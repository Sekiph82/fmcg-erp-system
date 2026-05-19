# Receivables, Dunning & Invoice Match

---

## Receivables

**Route:** `/dashboard/finance?tab=receivables`  
**Permission required:** `finance.view`

### What It Does

Receivables tracks all outstanding customer invoices and presents an aging analysis. It is the collections view — not a ledger editor.

![Receivables tab](../../../screenshots/captured/module-ui/finance-payroll/finance/receivables-tab.png)
*Receivables tab showing four KPI tiles, an aging bar chart, and the outstanding invoices table.*

### KPI Tiles

| Tile | Description |
|---|---|
| Total Outstanding | Sum of all outstanding invoice balances |
| Overdue | Amount and count of invoices past due date |
| Severely Overdue | Amount and count of invoices > 60 days overdue |
| Current (Not Due) | Amount and count of invoices not yet due |

### Aging Buckets

Five buckets shown as a bar chart and summary cards:

| Bucket | Days Overdue |
|---|---|
| Current | ≤ 0 (not yet overdue) |
| 1–30 days | 1–30 |
| 31–60 days | 31–60 |
| 61–90 days | 61–90 |
| 90+ days | > 90 |

Current bucket: green bar. All overdue buckets: red bar.

### Outstanding Invoices Table

| Column | Field | Notes |
|---|---|---|
| Invoice No | `invoice_no` | Monospace reference |
| Customer | `customer_name` | — |
| Invoice Date | `invoice_date` | — |
| Due Date | `due_date` | — |
| Total | `total_amount` | Invoice total |
| Paid | `paid_amount` | Green |
| Outstanding | `outstanding` | Orange if overdue, red if > 60 days |
| Age | `days_overdue` | "Current" (green) or "{N}d overdue" (yellow/red) badge |

---

## Dunning

**Route:** `/dashboard/finance?tab=dunning`  
**Permission required:** `finance.view`

### What It Does

Dunning manages the collections escalation process. When a receivable becomes overdue, a dunning case is created and tracked through escalation levels.

![Dunning tab](../../../screenshots/captured/module-ui/finance-payroll/finance/dunning-tab.png)
*Dunning tab showing dunning cases with customer, invoice, overdue amount, days overdue, and escalation level.*

---

## Invoice Match

**Route:** `/dashboard/finance?tab=invoice-match`  
**Permission required:** `finance.view`

### What It Does

Invoice Match reconciles incoming supplier invoices against purchase orders and GRNs. It identifies matches, tolerances, duplicates, and blocked invoices.

![Invoice Match tab](../../../screenshots/captured/module-ui/finance-payroll/finance/invoice-match-tab.png)
*Invoice Match tab showing match status, PO linkage, and tolerance rules.*

![Invoice Match dashboard](../../../screenshots/captured/module-ui/finance-payroll/invoice-match/invoice-match-dashboard.png)
*Invoice Match standalone dashboard with match queues and review workflow.*

### Match Status Values

| Status | Meaning |
|---|---|
| `MATCHED` | Invoice matches PO/GRN within tolerance |
| `TOLERANCE` | Minor variance within configured tolerance rule |
| `MISMATCH` | Significant variance requiring review |
| `DUPLICATE` | Invoice already processed |
| `BLOCKED` | Held pending manual approval |

### Sub-pages

| Page | Purpose |
|---|---|
| Review Queue | Invoices requiring manual review |
| Matches | Confirmed matched invoices |
| Blocked | Invoices on hold |
| Duplicates | Detected duplicate submissions |
| Tolerance Rules | Configure variance thresholds per supplier/category |
| Reports | Match rate and exception reports |
