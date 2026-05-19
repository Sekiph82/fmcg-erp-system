# Budget, Costing & Exchange Rates

---

## Budget Management

**Route:** `/dashboard/finance?tab=budget`  
**Permission required:** `finance.view`

### What It Does

Budget Management creates, approves, locks, and tracks department budgets vs actuals. Budgets are versioned — when a locked budget is revised, a new version is created.

![Budget tab](../../../screenshots/captured/module-ui/finance-payroll/finance/budget-tab.png)
*Budget tab showing budget list, selected budget detail, Budget vs Actual table, and threshold alerts.*

### Budget KPI Tiles

| Tile | Description |
|---|---|
| Total Budgeted | Sum of all budgeted amounts for the selected year/department filter |
| Total Actual | Sum of actual spend for the same filter |
| Variance | Actual minus budgeted; red if positive (over budget), green if negative |
| Alerts | Count of CRITICAL and WARNING threshold alerts |

### Budget Status

| Status | Badge | Actions Available |
|---|---|---|
| `DRAFT` | Yellow | Approve |
| `APPROVED` | Green | Lock, Revise |
| `LOCKED` | Blue | New Revision |

### Budget Create Form

Button: **New Budget** (top-right)

| Field | Label | Required | Notes |
|---|---|---|---|
| `year` | Year | Yes | Fiscal year (number) |
| `currency` | Currency | No | Default: KES |
| `department` | Department | Yes | Free text, e.g. Operations, Sales |
| `budget_type` | Budget Type | Yes | OPEX — Operating Expenses / CAPEX — Capital Expenditure |
| `notes` | Notes | No | Optional context |

After creation, budget lines (category + month + amount) are added via the detail panel.

### Budget vs Actual Table

Filterable by year and department. Columns:

| Column | Description |
|---|---|
| Department | Budget owner |
| Category | Expense category |
| Month | Calendar month |
| Budgeted | Planned amount |
| Actual | Actual posted amount |
| Variance | Actual − Budgeted; red if over |
| Var % | Percentage variance |
| Utilization | Progress bar: green < 90%, amber 90–99%, red ≥ 100% |

### Budget Alerts

Alerts trigger at configurable thresholds (default: 90% utilization). Alert levels:

| Level | Badge | Condition |
|---|---|---|
| `WARNING` | Amber | Utilization ≥ threshold |
| `CRITICAL` | Red | Utilization ≥ 100% (over budget) |

---

## Costing

**Route:** `/dashboard/finance?tab=costing`  
**Permission required:** `finance.view`

### What It Does

Costing shows production cost rollups. It aggregates material, labour, and overhead costs from manufacturing runs to produce unit cost figures per product per period.

![Costing tab](../../../screenshots/captured/module-ui/finance-payroll/finance/costing-tab.png)
*Costing tab showing product cost rollups with material, labour, overhead, and unit cost columns.*

---

## Exchange Rates

**Route:** `/dashboard/finance?tab=exchange-rates`  
**Permission required:** `finance.view`

### What It Does

Exchange Rates manages currency conversion rates used across the ERP for multi-currency transactions, revaluation, and reporting.

![Exchange Rates tab](../../../screenshots/captured/module-ui/finance-payroll/finance/exchange-rates-tab.png)
*Exchange Rates tab showing rate entries with currency, rate, effective date, and source.*

### Rate Source Options

| Source | Description |
|---|---|
| `MANUAL` | Rate entered manually by finance team |
| `CBK` | Central Bank of Kenya daily rate |
| `ECB` | European Central Bank rate |
| `API` | Automated rate feed via Bank API |

### Supported Currencies

KES (base), USD, EUR, GBP, and others configurable via Bank API. The Currency select field shows all configured currencies when adding or editing a rate.
