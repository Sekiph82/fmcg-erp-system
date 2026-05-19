# Maintenance Module Overview

**Route:** `/dashboard/maintenance`  
**Permission required:** `maintenance.view`

## What It Does

Central hub for equipment reliability: asset register, breakdown logging, preventive maintenance (PM) plans, predictive failure detection, spare parts inventory, and MTBF/MTTR reporting.

![Overview Tab](../../../screenshots/captured/module-ui/maintenance/overview/overview-tab.png)
*Maintenance dashboard — KPI tiles, open breakdowns panel, overdue PM panel, and quick-navigation links.*

## Dashboard KPI Tiles

| Tile | Description |
|------|-------------|
| Total Assets | All registered assets. Sub-label: count under maintenance |
| Open Breakdowns | Active (OPEN) + in-repair (IN_REPAIR) breakdowns |
| Overdue PMs | PM plans past their next_due_date |
| Low Stock Spares | Parts at or below their reorder level |

Clicking any tile navigates to the corresponding sub-page.

## Open Breakdowns Panel

Shows up to 8 active breakdowns: Asset, Reason, Severity badge, Started date. "View all" links to `/dashboard/maintenance/assets`.

## Overdue PM Plans Panel

Shows up to 8 overdue plans: Asset, Plan Name, Due Date, Days Overdue (red when > 14 days).

## Quick Links

| Card | Route | Description |
|------|-------|-------------|
| Asset Register | `/dashboard/maintenance/assets` | Machines, equipment, production lines |
| PM Plans & Work Orders | `/dashboard/maintenance/plans` | Preventive maintenance schedules and completion |
| Breakdown Records | `/dashboard/maintenance/breakdowns` | Log and resolve equipment failures |
| Predictive Maintenance | `/dashboard/maintenance/predictive` | IoT-based failure risk queue |
| Spare Parts | `/dashboard/maintenance/spares` | Spare part inventory with reorder alerts |
| Maintenance Reports | `/dashboard/maintenance/reports` | MTBF, MTTR, downtime, overdue PMs |

## Module Tabs

| Tab Key | Label | Content |
|---------|-------|---------|
| overview | Overview | Dashboard (this page) |
| assets | Assets | Asset register |
| breakdowns | Breakdowns | Breakdown log |
| plans | Plans | PM plans & work orders |
| predictive | Predictive | Failure prediction queue |
| spares | Spares | Spare parts inventory |
| reports | Reports | MTBF/MTTR analytics |
