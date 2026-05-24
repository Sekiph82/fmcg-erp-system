# FMCG ERP — Intelligence, Analytics & AI Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Managers, Analysts, Business Intelligence Teams, All Senior Staff  
**Modules Covered:** Analytics · Report Builder · Sales Analytics · Production Analytics · Inventory Analytics · Finance Analytics · AI Assistant · NPD Analytics

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Analytics Hub](#2-analytics-hub)
3. [Sales Analytics](#3-sales-analytics)
4. [Production Analytics](#4-production-analytics)
5. [Inventory Analytics](#5-inventory-analytics)
6. [Finance Analytics](#6-finance-analytics)
7. [Report Builder](#7-report-builder)
8. [AI Assistant](#8-ai-assistant)
9. [AI Chat Interface](#9-ai-chat-interface)
10. [Common Mistakes & Troubleshooting](#10-common-mistakes--troubleshooting)
11. [Related Modules](#11-related-modules)

---

## 1. Module Overview

**What it does:** Business intelligence, analytics dashboards, custom report building, and AI-powered insights across all ERP modules. Enables data-driven decision making through interactive charts, KPI monitoring, and natural-language querying.

**Who uses it:**
- Managing Director / CEO — top-level KPI monitoring
- Finance Manager — financial performance and forecasting
- Sales Manager — revenue tracking and pipeline analysis
- Production Manager — OEE, yield, and cost analytics
- Supply Chain Manager — inventory and procurement analytics
- All Managers — custom report building

**When to use it:**
- Daily: Check KPI dashboards at start of business day
- Weekly: Review production OEE, sales performance, inventory levels
- Monthly: Run financial reports for management meetings
- Ad-hoc: Build custom reports for specific analysis needs
- Always available: AI chat for on-demand data queries

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| Analytics | `/dashboard/analytics` | Full analytics workspace |
| AI | `/dashboard/ai` | AI assistant and insights |

---

## 2. Analytics Hub

**Route:** `/dashboard/analytics`

![Analytics Hub](../../user-manual/screenshots/captured/109_analytics.png)
*Analytics hub — module selector and top-level business KPIs.*

### Tabs

| Tab | Purpose |
|-----|---------|
| Overview | Company-wide KPI dashboard |
| Sales | Revenue, orders, and customer analytics |
| Production | Manufacturing performance analytics |
| Inventory | Stock levels, movements, and aging |
| Finance | Financial performance and variance |
| Report Builder | Custom report creation tool |

---

## 3. Sales Analytics

**Tab:** Sales  
**Route:** `/dashboard/analytics/sales`

![Sales Analytics](../../user-manual/screenshots/captured/110_analytics-sales.png)
*Sales analytics — revenue trends, top products, customer rankings, and channel performance.*

### Metrics Available

**Revenue:**
- Total revenue (period selectable)
- Revenue vs. same period last year
- Revenue by product category
- Revenue by customer
- Revenue by territory / region
- Revenue by channel (direct / distributor / van / POS)

**Orders:**
- Order count and average order value
- Order fill rate (% delivered on time in full — OTIF)
- Orders by status
- Order cycle time (order to delivery)

**Customers:**
- Top 10 customers by revenue
- New vs. returning customers
- Customer lifetime value
- Churn indicators

**Products:**
- Top selling SKUs by volume and value
- Slow-moving products
- Margin by product
- Price compliance (actual vs. price list)

### Filters Available
- Date range (custom or presets: Today / This Week / This Month / Last Month / YTD / Last Year)
- Customer
- Product category
- Territory
- Sales rep
- Channel

---

## 4. Production Analytics

**Tab:** Production  
**Route:** `/dashboard/analytics/production`

![Production Analytics](../../user-manual/screenshots/captured/111_analytics-production.png)
*Production analytics — OEE, yield, work order performance, and cost variance.*

### Metrics Available

**OEE:**
- Overall OEE % by line and period
- Availability, Performance, Quality breakdown
- OEE trend chart
- Benchmark vs. target OEE

**Production Output:**
- Planned vs. actual production quantity
- Production plan adherence %
- Batch count and average batch size
- Work order completion rate

**Yield & Waste:**
- Yield % by product
- Waste quantity and cost
- Scrap categories breakdown
- Yield trend over time

**Costing:**
- Standard vs. actual cost per unit
- Material variance
- Labor variance
- Total production cost per period

**Downtime:**
- Total downtime hours
- Downtime by machine
- Downtime by category (Mechanical / Electrical / etc.)
- MTBF and MTTR by asset

---

## 5. Inventory Analytics

**Tab:** Inventory  
**Route:** `/dashboard/analytics/inventory`

![Inventory Analytics](../../user-manual/screenshots/captured/112_analytics-inventory.png)
*Inventory analytics — stock levels, turnover, aging, and procurement performance.*

### Metrics Available

**Stock Levels:**
- Total stock value by category
- Stock below reorder level (count and list)
- Overstock items (above max stock level)
- Zero-stock finished goods with pending orders

**Stock Turnover:**
- Inventory days on hand
- Stock turnover ratio by category
- Slow-moving and dead stock
- Shelf life utilization (perishables)

**Procurement Performance:**
- Supplier on-time delivery %
- PO lead time actuals vs. expected
- Purchase price variance (actual vs. standard)
- Supplier quality score

**Warehouse:**
- Location utilization %
- Picking accuracy
- Goods receipt to putaway time

---

## 6. Finance Analytics

**Tab:** Finance  
**Route:** `/dashboard/analytics/finance`

![Finance Analytics](../../user-manual/screenshots/captured/113_analytics-finance.png)
*Finance analytics — P&L, cash flow, AR aging, and budget variance.*

### Metrics Available

**P&L Summary:**
- Revenue, Cost of Sales, Gross Margin
- Operating Expenses
- EBITDA
- Net Profit
- Period vs. period comparison

**Cash Flow:**
- Cash inflows (customer collections)
- Cash outflows (supplier payments, payroll)
- Net cash position
- Cash flow forecast (30/60/90 days)

**Accounts Receivable:**
- Total outstanding AR
- Aging breakdown (Current / 30 / 60 / 90+ days)
- DSO (Days Sales Outstanding)
- Overdue customers list

**Budget:**
- Budget vs. actual by account and cost centre
- Over-budget items flagged
- Full-year forecast vs. budget

**Tax:**
- VAT output vs. input summary
- PAYE liability
- WHT payable

---

## 7. Report Builder

**Tab:** Report Builder  
**Route:** `/dashboard/analytics/report-builder`

![Report Builder](../../user-manual/screenshots/captured/114_analytics-report-builder.png)
*Report builder — drag-and-drop custom report creation from any ERP data source.*

### What it does
Build custom tabular and chart reports without needing IT support. Choose data sources, columns, filters, grouping, and visualization type.

### Creating a Custom Report

1. Report Builder → **+ New Report**
2. Select **Data Source** (which module/table):
   - Sales Orders
   - Invoices
   - Products
   - Purchase Orders
   - Inventory Stock
   - Production Work Orders
   - HR Employees
   - Finance Journals
   - etc.

3. **Select Columns** — drag fields to include
4. **Add Filters** — optional conditions (e.g. Date > 2026-01-01, Status = COMPLETED)
5. **Group By** — aggregate data (e.g. by Product Category, by Month)
6. **Sort** — set column sort order
7. **Visualization** — Table / Bar Chart / Line Chart / Pie Chart / KPI Card
8. **Save Report** — assign name, category, and access level

### Scheduling Reports
After saving:
1. Open report → **Schedule**
2. Set frequency: Daily / Weekly / Monthly
3. Set recipients (email addresses)
4. Set format: PDF / Excel / CSV
5. Save — report auto-sent on schedule

### Sharing Reports
- Save report as **Public** — all users can view
- Save as **Department** — department members only
- Save as **Private** — only you

---

## 8. AI Assistant

**Route:** `/dashboard/ai`

![AI Module](../../user-manual/screenshots/captured/131_ai.png)
*AI assistant — intelligent recommendations across all ERP modules.*

### AI Features

| Feature | Where Used | What It Does |
|---------|-----------|--------------|
| Demand Forecast | Sales / Inventory | Predicts next 30/60/90 day demand per SKU |
| Reorder Suggestions | Procurement | Suggests when and how much to reorder |
| Production Optimization | Manufacturing | Suggests optimal batch sizes and schedules |
| Quality Anomaly Detection | Quality | Flags unusual QC results for investigation |
| Financial Insights | Finance | Auto-generates commentary on P&L variances |
| Customer Insights | CRM / Sales | Identifies at-risk customers and upsell opportunities |
| Maintenance Prediction | Maintenance | Predicts equipment failures from sensor data |

### Demand Forecast

The AI demand forecast model:
1. Analyzes 24 months of sales history
2. Accounts for seasonality, promotions, and trends
3. Generates SKU-level forecast for configurable horizon
4. Updates weekly (or on-demand)
5. Forecast error tracked (MAPE %)

**Using the forecast:**
- Sales team: review and adjust forecast in Sales → Forecast
- Planning: MPS uses forecast as input automatically if integrated
- Procurement: reorder suggestions incorporate forecast

---

## 9. AI Chat Interface

**Route:** `/dashboard/ai/chat`

![AI Chat](../../user-manual/screenshots/captured/132_ai-chat.png)
*AI chat — natural language queries about your ERP data.*

### What it does
Ask questions about ERP data in plain English (or Swahili). AI queries the database and returns answers with charts or tables.

### Example Queries

**Sales:**
- "What was our total revenue in April 2026?"
- "Show me the top 5 customers by sales value this year"
- "Which products haven't sold in the last 60 days?"
- "What is the average order value this month vs. last month?"

**Inventory:**
- "What items are below reorder level right now?"
- "Show me all products expiring within 30 days"
- "What is the total value of finished goods stock?"
- "Which warehouse has the most dead stock?"

**Production:**
- "What was Line 2 OEE this week?"
- "How many work orders are overdue?"
- "What is the yield % for product SKU-001 this month?"
- "Which machine had the most downtime in May?"

**Finance:**
- "What is our current accounts receivable total?"
- "Show overdue invoices older than 60 days"
- "What is the budget variance for marketing this quarter?"

**HR:**
- "How many employees are on leave today?"
- "List employees whose probation ends this month"
- "What is the average attendance rate for the factory this week?"

### AI Chat Limitations
- AI reads data only — it cannot create, edit, or delete records
- Results are as current as the last data sync (real-time for most tables)
- Complex cross-module queries may take a few seconds
- If a query returns no results, rephrase or check filters

---

## 10. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Dashboard shows no data | Date filter too narrow | Expand date range; check if data exists for period |
| Sales chart missing products | Products not linked to correct category | Update product category in Products master |
| Production analytics wrong | Work orders not closed | Close completed work orders in Production module |
| Report builder export fails | Too many rows | Add more filters to reduce result set; export max 50,000 rows |
| AI forecast not updating | Model hasn't run yet | AI forecast updates weekly; or trigger manual refresh |
| AI chat says "no data found" | Query too specific or table empty | Rephrase; check the underlying module has records |
| Scheduled report not arriving | Email address wrong | Check recipient email in report schedule settings |

---

## 11. Related Modules

| Analytics Topic | Source Module |
|----------------|---------------|
| Sales revenue data | Sales → Invoices |
| Production OEE | Manufacturing → Production |
| Inventory stock | Inventory → Stock |
| Finance P&L | Finance → Accounting |
| HR headcount | HR → Employees |
| Procurement performance | Procurement → Purchase Orders |
| Quality defect rate | Quality → Inspections |
| Maintenance MTBF | Maintenance → Breakdowns |

---

*End of Intelligence, Analytics & AI Manual v2*
