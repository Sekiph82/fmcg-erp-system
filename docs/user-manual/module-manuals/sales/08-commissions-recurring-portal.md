# Commissions, Recurring Orders, Margin, Contracts & Customer Portal

---

## Commissions

**Route:** `/dashboard/sales?tab=commissions`  
**Permission required:** `sales.view`

### What It Does

Commissions calculates sales representative commission based on configurable rules tied to sales volume, margin, or collections performance. Results are used for payroll input.

![Commissions tab](../../../screenshots/captured/module-ui/sales/sales/commissions-tab.png)
*Commissions tab showing sales rep commission calculations with period, sales value, commission rate, and payout status.*

### Commission Concepts

| Concept | Description |
|---|---|
| Commission Rule | Rate or formula applied per rep, product, or territory |
| Commission Period | Month or quarter over which commissions are calculated |
| Commission Run | Calculation run that produces commission amounts |
| Payout Status | PENDING / APPROVED / PAID |

---

## Recurring Orders

**Route:** `/dashboard/sales?tab=recurring`  
**Permission required:** `sales.view`

### What It Does

Recurring Orders auto-generates sales orders on a schedule (weekly, monthly) for customers with standing orders. This eliminates manual order entry for repeat customers.

![Recurring Orders tab](../../../screenshots/captured/module-ui/sales/sales/recurring-tab.png)
*Recurring Orders tab showing scheduled order templates with frequency, next run date, and customer.*

### Recurring Order Fields

| Field | Description |
|---|---|
| Template No | Unique reference |
| Customer | Recipient customer |
| Frequency | DAILY / WEEKLY / MONTHLY |
| Next Run | Date of next auto-generated order |
| Products | Template order lines |
| Is Active | Whether auto-generation is enabled |

---

## Margin Analysis

**Route:** `/dashboard/sales?tab=margin`  
**Permission required:** `sales.view`

### What It Does

Margin shows gross profit margin by product, customer, and channel. It compares revenue from invoices against the standard cost of goods sold (from product costing) to produce margin percentages.

![Margin tab](../../../screenshots/captured/module-ui/sales/sales/margin-tab.png)
*Margin tab showing product and customer profitability with revenue, cost, gross profit, and margin % columns.*

### Margin Columns

| Column | Description |
|---|---|
| Product / Customer | Analysis dimension |
| Revenue | Total invoiced value |
| COGS | Cost of goods sold (from costing module) |
| Gross Profit | Revenue minus COGS |
| Margin % | Gross Profit / Revenue × 100 |

---

## Contracts (Sales Workspace)

**Route:** `/dashboard/sales?tab=contracts`  
**Permission required:** `sales.view`

Sales workspace contracts tab shows the same Contract Management module embedded in the sales context. See [Finance & Payroll — Chapter 11](../../finance-payroll/11-expenses-contracts.md) for full contract fields and workflow.

![Contracts tab](../../../screenshots/captured/module-ui/sales/sales/contracts-tab.png)
*Contracts tab within the Sales workspace.*

---

## Customer Portal

**Route:** `/dashboard/sales?tab=portal`  
**Permission required:** `sales.view`

### What It Does

Customer Portal configures the self-service portal that allows customers to place orders, view invoices, track shipments, and download statements without contacting the sales team.

![Customer Portal tab](../../../screenshots/captured/module-ui/sales/sales/portal-tab.png)
*Customer Portal tab showing portal configuration and access management.*

---

## Sales Reports

**Route:** `/dashboard/sales?tab=reports`  
**Permission required:** `sales.view`

### What It Does

Reports provides pre-built sales analytics: revenue by period, top customers, top products, channel mix, rep performance, and collection rates.

![Sales Reports tab](../../../screenshots/captured/module-ui/sales/sales/reports-tab.png)
*Sales Reports tab showing analytics reports with period filters and export options.*
