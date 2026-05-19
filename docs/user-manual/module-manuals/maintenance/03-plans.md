# PM Plans & Work Orders

**Route:** `/dashboard/maintenance?tab=plans`  
**Permission required:** `maintenance.view`

## What It Does

Manages preventive maintenance schedules (PM Plans) and generates Work Orders for each scheduled maintenance run. Supports fixed-frequency and custom-interval scheduling with technician assignment and checklist-based completion.

## Two Sub-Tabs

### PM Plans

![Plans Tab](../../../screenshots/captured/module-ui/maintenance/plans/plans-tab.png)
*PM Plans sub-tab — schedule list with frequency badges and overdue highlighting.*

Defines recurring maintenance schedules per asset.

**PM Plans Table Columns**

| Column | Description |
|--------|-------------|
| Asset | Asset name and number |
| Plan Name | Descriptive name of the maintenance task |
| Frequency | Schedule type badge |
| Assigned To | Default technician for this plan |
| Last Done | Date most recent work order was completed |
| Next Due | Due date — highlighted red when overdue |
| Est. Duration | Expected time in minutes |
| Active | Toggle — inactive plans don't generate work orders |

### Work Orders

![Work Orders Tab](../../../screenshots/captured/module-ui/maintenance/plans/work-orders-tab.png)
*Work Orders sub-tab — scheduled and completed work orders.*

**Work Orders Table Columns**

| Column | Description |
|--------|-------------|
| WO No | System-assigned work order number |
| Asset | Asset name |
| Plan | Source PM Plan name |
| Scheduled | Scheduled execution date |
| Technician | Assigned technician |
| Status | PENDING · IN_PROGRESS · COMPLETED · OVERDUE · SKIPPED |
| Duration | Actual duration (minutes) after completion |

## PM Plan Frequency

| Value | Description |
|-------|-------------|
| DAILY | Every day |
| WEEKLY | Every 7 days |
| MONTHLY | Every month |
| QUARTERLY | Every 3 months |
| BIANNUAL | Every 6 months |
| ANNUAL | Every year |
| CUSTOM | Custom interval — set interval_days manually |

## PM Plan Status

| Status | Meaning |
|--------|---------|
| PENDING | Scheduled, not yet started |
| IN_PROGRESS | Technician started work |
| COMPLETED | Finished within scheduled date |
| OVERDUE | Past due date, not completed |
| SKIPPED | Marked as skipped with reason |

## New PM Plan Form

![New Plan Modal](../../../screenshots/captured/module-ui/maintenance/plans/new-plan-modal.png)
*New PM Plan modal — asset, frequency, duration, checklist.*

| Field | Description |
|-------|-------------|
| Asset | Select from asset register |
| Plan Name | Descriptive maintenance task name |
| Frequency | Schedule type (see table above) |
| Interval Days | Custom interval in days (CUSTOM frequency only) |
| Estimated Duration | Expected time in minutes |
| Assigned To | Default technician name |
| Next Due Date | First or next scheduled date |
| Checklist | One task item per line — checklist used at completion |

API: `POST /api/v1/maintenance/plans`

## New Work Order Form

| Field | Description |
|-------|-------------|
| PM Plan | Select source plan |
| Scheduled Date | Date the work order is scheduled for |
| Technician | Assigned technician |

API: `POST /api/v1/maintenance/work-orders`

## Complete Work Order Form

Triggered by clicking "Complete" on an active work order.

| Field | Description |
|-------|-------------|
| Actual Duration (minutes) | Actual time taken |
| Checklist Notes | Notes per checklist item |
| Technician | Technician who completed the work |

API: `PUT /api/v1/maintenance/work-orders/{id}/complete`
