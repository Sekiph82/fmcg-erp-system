# Expenses & Contracts

---

## Expenses

**Route:** `/dashboard/finance?tab=expenses`  
**Permission required:** `hr.view`

### What It Does

Expenses manages the employee expense claim lifecycle from submission through approval to reimbursement. It supports receipt OCR, policy enforcement, advances, and management reports.

![Expenses tab](../../../screenshots/captured/module-ui/finance-payroll/finance/expenses-tab.png)
*Expenses tab within the Finance workspace.*

![Expenses dashboard](../../../screenshots/captured/module-ui/finance-payroll/expenses/expenses-dashboard.png)
*Expenses standalone dashboard showing eight KPI tiles and navigation quick links.*

### Dashboard KPIs

| KPI | Description |
|---|---|
| Total Claims | All expense claims submitted |
| Pending Approval | Claims awaiting manager or finance approval |
| Finance Approved (Unpaid) | Claims approved but reimbursement not yet processed |
| Reimbursed This Month | Total KES reimbursed in current calendar month |
| Claimed This Month | Total KES claimed in current calendar month |
| Policy Violations | Open claims that breach expense policy rules |
| Overdue Advances | Employee advances outstanding past due date |
| AI Alerts | AI-flagged anomalies requiring review |

### Expense Claim Workflow

```
Employee submits claim (/expenses/claims/new)
    → Manager approval (Approval Queue)
    → Finance approval
    → Reimbursement processing (/expenses/reimbursement)
    → Payment via cashbook
```

### Expense Sub-pages

| Page | Route | Purpose |
|---|---|---|
| My Claims | `/dashboard/expenses/claims` | Employee's own claims |
| New Claim | `/dashboard/expenses/claims/new` | Submit a new expense claim |
| Approval Queue | `/dashboard/expenses/approval` | Manager and finance approval workflow |
| Reimbursement | `/dashboard/expenses/reimbursement` | Process approved claim payments |
| Advances | `/dashboard/expenses/advances` | Employee advance requests and repayments |
| Categories | `/dashboard/expenses/categories` | Expense category setup |
| Policies | `/dashboard/expenses/policies` | Spend limits and rules per category/role |
| Reports | `/dashboard/expenses/reports` | Expense analytics and audit reports |
| AI Insights | `/dashboard/expenses/ai` | AI-detected anomalies and duplicate submissions |
| Receipt OCR | `/dashboard/expenses/receipt-ocr` | Scan receipts to auto-populate claim lines |

---

## Contracts

**Route:** `/dashboard/contracts`  
**Permission required:** `finance.view`

### What It Does

Contract Management tracks commercial agreements — supplier, customer, and partner contracts — through their full lifecycle from draft to expiry. It flags contracts nearing expiry and supports AI-assisted contract review.

![Contracts dashboard](../../../screenshots/captured/module-ui/finance-payroll/contracts/contracts-dashboard.png)
*Contracts dashboard showing five KPI tiles, recent contracts list, expiring contracts panel, and AI recommendations.*

### Dashboard KPIs

| KPI | Colour | Description |
|---|---|---|
| Total | White | All contracts in the system |
| Active | Green | Currently active contracts |
| Expiring 30d | Amber | Contracts expiring within 30 days |
| Draft | Gray | Contracts not yet executed |
| Under Review | Blue | Contracts in legal/management review |

### Contract Status Values

Defined in `STATUS_COLORS` in the codebase; typical values:

| Status | Meaning |
|---|---|
| `DRAFT` | Being prepared, not yet executed |
| `UNDER_REVIEW` | Sent for legal or management review |
| `ACTIVE` | Executed and in effect |
| `EXPIRING` | Within the alert window |
| `EXPIRED` | Past end date |
| `TERMINATED` | Ended early |

### Contract Sub-pages

| Page | Route | Purpose |
|---|---|---|
| Contract List | `/dashboard/contracts/list` | All contracts with filter and search |
| New Contract | `/dashboard/contracts/new` | Create a new contract |
| Expiring | `/dashboard/contracts/expiring` | Contracts expiring within configurable days |
| Performance | `/dashboard/contracts/performance` | KPI and milestone tracking per contract |
| Reports | `/dashboard/contracts/reports` | Expiry calendar and summary reports |
| AI Agents | `/dashboard/contracts/ai` | AI recommendations (renewal, renegotiation alerts) |

### Expiry Alerts

The dashboard shows all contracts expiring within 30 days. Clicking a contract opens its detail page where renewal or termination actions can be taken.
