# CRM Dashboard

**Route:** `/dashboard/crm?tab=overview`  
**Permission required:** `crm.view`

## What It Does

The Overview tab is the CRM command center. It surfaces pipeline health KPIs, total and weighted pipeline value, stage distribution by count and value, and top reps ranked by pipeline value.

![CRM Overview tab](../../../screenshots/captured/module-ui/crm/crm/overview-tab.png)
*CRM Overview tab showing KPI grid, pipeline value cards, stage distribution, and top reps.*

## KPI Cards

| KPI | Description |
|---|---|
| Total Leads | All lead records in the system |
| Opportunities | All opportunity records |
| Open Records | Leads and opportunities with status OPEN |
| Won This Month | Records closed WON in the current month |
| Lost This Month | Records closed LOST in the current month |
| Hot Records | Records with temperature HOT |
| Overdue Activities | Activities past their due date and not completed |
| Win Rate | `conversion_rate_pct` — won / (won + lost) × 100 |

## Pipeline Value Cards

| Card | Description |
|---|---|
| Total Pipeline Value | Sum of `expected_revenue` across all open records |
| Weighted Pipeline | Sum of `expected_revenue × probability_pct / 100` |
| Avg Deal Size | `avg_deal_size` from dashboard API |

## Stage Distribution

Lists each active stage with a color dot, open record count, and total value. Stages with zero records are omitted.

## Top Reps by Pipeline

Ranked list of sales reps by total open pipeline value, showing deal count and value per rep.

## Quick Links

| Link | Route |
|---|---|
| Lead List | `/dashboard/crm/leads` |
| Opportunities | `/dashboard/crm/opportunities` |
| Pipeline Board | `/dashboard/crm/pipeline` |
| Activity Timeline | `/dashboard/crm/activities` |
| Forecast | `/dashboard/crm/forecast` |
| Win/Loss Analysis | `/dashboard/crm/win-loss` |
| Overdue Queue | `/dashboard/crm/overdue` |
| AI Agents | `/dashboard/crm/ai` |
| Stage Config | `/dashboard/crm/stages` |

## Buttons

| Button | Action |
|---|---|
| `+ New Lead` | Navigates to `/dashboard/crm/leads` (leads list with create form) |
| `Pipeline Board` | Navigates to `/dashboard/crm/pipeline` |
