# Maintenance Reports

**Route:** `/dashboard/maintenance?tab=reports`  
**Permission required:** `maintenance.export`

## What It Does

Provides equipment reliability analytics: MTBF (Mean Time Between Failures), MTTR (Mean Time To Repair), downtime totals by machine, and a list of overdue PM plans.

![Reports Tab](../../../screenshots/captured/module-ui/maintenance/reports/reports-tab.png)
*Maintenance Reports — summary tiles, MTBF/MTTR table, downtime by machine, and overdue PM list.*

## Summary Tiles

| Tile | Description |
|------|-------------|
| Total Downtime | Sum of all breakdown downtime in hours (and minutes) |
| Total Breakdowns | Count across all assets |
| Worst Asset | Asset with highest total downtime |
| Best MTBF | Asset with the highest mean time between failures |

## MTBF / MTTR Table

MTBF = Mean Time Between Failures (days). MTTR = Mean Time To Repair (minutes).

| Column | Description |
|--------|-------------|
| Asset | Asset name and asset_no |
| Line | Production line |
| Breakdowns | Total breakdown count |
| Total Downtime | Cumulative downtime in minutes |
| MTTR (min) | Average repair time — red if > 120 min |
| MTBF (days) | Days between breakdowns — red < 7 days, orange < 30 days, green ≥ 30 days |

## Downtime by Machine

Includes breakdown downtime and MES downtime logs.

| Column | Description |
|--------|-------------|
| Asset | Asset name and asset_no |
| Line | Production line |
| Breakdowns | Breakdown count |
| Total Downtime | Minutes |
| Hours | Converted hours |
| Open | Open breakdown count badge |
| Severity Bar | Proportional red bar — % of total downtime |

## Overdue PM Plans

| Column | Description |
|--------|-------------|
| Asset | Asset name and asset_no |
| Plan | PM Plan name |
| Frequency | Schedule frequency badge |
| Due Date | Scheduled next_due_date |
| Days Overdue | Red if > 14 days, orange otherwise |

A "All PM plans are up to date" message replaces the table when none are overdue.
