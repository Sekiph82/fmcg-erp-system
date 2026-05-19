# Breakdown Records

**Route:** `/dashboard/maintenance?tab=breakdowns`  
**Permission required:** `maintenance.view`

## What It Does

Logs all equipment failures from first report through resolution. Tracks downtime duration, root cause, and corrective action. Can be linked to a Manufacturing Production Order via `production_order_id`.

![Breakdowns Tab](../../../screenshots/captured/module-ui/maintenance/breakdowns/breakdowns-tab.png)
*Breakdown log — list with severity badges, downtime column, and total downtime summary.*

## Breakdown Status

| Status | Meaning |
|--------|---------|
| OPEN | Failure reported, not yet repaired |
| IN_REPAIR | Repair in progress |
| RESOLVED | Repaired and returned to service |

## Severity

| Level | Usage |
|-------|-------|
| LOW | Minor fault, production continues |
| MEDIUM | Partial production impact |
| HIGH | Significant production stoppage |
| CRITICAL | Full line stoppage or safety hazard |

## Breakdown Table Columns

| Column | Description |
|--------|-------------|
| Breakdown No | System-assigned reference |
| Asset | Asset name and number |
| Reason | Brief description of failure |
| Severity | LOW · MEDIUM · HIGH · CRITICAL badge |
| Start | Failure start time |
| End | Repair completion time |
| Downtime | Minutes (auto-calculated from start/end) |
| Status | Current status badge |

Total downtime summary (minutes + hours) shown below the table.

## Log Breakdown Form

![Log Breakdown Modal](../../../screenshots/captured/module-ui/maintenance/breakdowns/log-breakdown-modal.png)
*Log Breakdown modal — asset, start time, severity, and reason fields.*

| Field | Description |
|-------|-------------|
| Asset | Select from asset register |
| Start Time | Datetime failure was detected |
| Reason | Description of fault |
| Severity | LOW · MEDIUM · HIGH · CRITICAL |
| Production Order | Link to a manufacturing order (optional UUID) |

API: `POST /api/v1/maintenance/breakdowns`

## Resolve Breakdown Form

Triggered by clicking "Resolve" on an OPEN or IN_REPAIR breakdown.

| Field | Description |
|-------|-------------|
| End Time | Datetime repair was completed |
| Root Cause | Identified cause of failure |
| Corrective Action | Steps taken to fix and prevent recurrence |

Downtime (minutes) auto-calculated as end_time − start_time.

API: `PUT /api/v1/maintenance/breakdowns/{id}/resolve`
