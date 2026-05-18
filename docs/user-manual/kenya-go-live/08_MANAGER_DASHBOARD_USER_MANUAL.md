# Manager Dashboard User Manual

**Audience:** Department Heads, Managing Director, Finance Director  
**URLs:** `/dashboard`, `/dashboard/analytics`, `/dashboard/finance`  
**Permission required:** `analytics.view`, `finance.view`, `approvals.view`

---

## Your Role

You monitor business performance, approve large transactions, and use the ERP for strategic decisions. You do not enter data directly — you review, approve, and analyse.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Dashboard | /dashboard | High-level KPI overview |
| Analytics | /dashboard/analytics | Detailed business intelligence |
| Finance | /dashboard/finance | P&L, cash flow, bank |
| Approvals | /dashboard/approvals | Approve POs, expenses, discounts |
| Production (read) | /dashboard/production?tab=oee | OEE and production efficiency |
| HR (read) | /dashboard/hr | Headcount, attendance |

---

## Screenshot

![Dashboard Home — KPI Cards](../screenshots/captured/002_dashboard.png)

---

## Dashboard Overview

The main dashboard shows:
- Today's production output vs plan
- Current stock value
- Open sales orders
- Outstanding receivables
- Cash position
- Pending approvals count

Click any KPI card to drill into the detail page.

---

## Approve Pending Items

Items requiring your approval appear as notifications and in the Approvals queue:

1. Go to `/dashboard/approvals`
2. View pending approvals by type:
   - Purchase Orders above threshold
   - Sales discounts above limit
   - Expense claims above limit
   - Payroll runs
3. Click an item to review details
4. Click **Approve** or **Reject**
5. If rejecting: enter reason (mandatory)

![Approvals Workspace](../screenshots/captured/135_approvals.png)

---

## Finance Overview

1. Go to `/dashboard/finance`
2. Overview tab shows:
   - P&L summary (this month vs last month)
   - Cash and bank balances
   - Receivables and payables
   - Budget vs actual

![Finance Workspace](../screenshots/captured/087_finance.png)

---

## Bank Reconciliation Status

1. Finance → Bank Reconciliation tab
2. View unreconciled items
3. Finance team handles reconciliation; you review the status
4. Escalate if large unreconciled amounts persist more than 7 days

---

## Analytics — Sales Dashboard

1. Go to `/dashboard/analytics?tab=sales`
2. View:
   - Revenue by customer, product, region
   - Trend vs last month / last year
   - Top 10 customers, top 10 products
   - Sales rep performance

![Analytics — Sales Tab](../screenshots/captured/110_analytics-sales.png)

---

## Analytics — Production Dashboard

1. Analytics → Production tab
2. View:
   - OEE trend over time
   - Production output vs plan
   - Downtime hours by reason
   - Waste % by product line

---

## Analytics — Inventory Dashboard

1. Analytics → Inventory tab
2. View:
   - Stock value trend
   - Slow-moving items
   - Items below reorder point
   - Expiry exposure (value at risk)

---

## Custom Reports (Report Builder)

1. Analytics → Report Builder tab
2. Create a new report:
   - Select data source (sales, inventory, production, etc.)
   - Choose dimensions and metrics
   - Apply filters
   - Save report with a name
3. Schedule delivery: email PDF every Monday morning

---

## Finance — Budget vs Actual

1. Finance → Budget tab
2. Compare actual spend to budget by department and account
3. Variance highlighted in red if > 10%
4. Click on a line to see underlying transactions

---

## Finance — M-Pesa Overview

1. Finance → M-Pesa tab
2. View M-Pesa collections today/this week/this month
3. Reconciliation status
4. Unmatched transactions (require manual matching)

---

## Common Tasks

| Task | How |
|---|---|
| Approve a PO > KES 500,000 | Approvals workspace → PO queue |
| Check receivables ageing | Finance → Receivables tab |
| View weekly production summary | Analytics → Production tab |
| Get top customers this month | Analytics → Sales tab |
| Review payroll before payout | HR → Payroll → approve run |

---

## Training Checklist

- [ ] Can navigate the main dashboard and understand KPI cards
- [ ] Can approve pending POs, expense claims, and discounts
- [ ] Can view P&L and cash position in Finance
- [ ] Can interpret OEE and production output charts
- [ ] Can find and review sales analytics
- [ ] Can run a custom report in Report Builder
- [ ] Can review and respond to approvals from mobile
