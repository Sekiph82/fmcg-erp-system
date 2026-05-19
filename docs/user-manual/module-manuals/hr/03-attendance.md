# Attendance Management

**Route:** `/dashboard/hr?tab=attendance`  
**Permission required:** `hr.view`

## What It Does

The Attendance tab records and reports daily employee attendance. Each record captures whether an employee was present, absent, late, on leave, or working a half day. The tab shows a period summary (counts per status) and a filterable attendance log.

![Attendance tab](../../../screenshots/captured/module-ui/hr/hr/attendance-tab.png)
*Attendance tab showing the summary tiles and attendance log with date, employee, department, status, and clock-in/out columns.*

## Period Summary Tiles

Five summary tiles show counts for the selected date range:

| Tile | Status | Badge |
|---|---|---|
| PRESENT | Employee was present | Green |
| ABSENT | Employee did not attend | Red |
| LATE | Employee arrived late | Yellow |
| LEAVE | Employee was on approved leave | Blue |
| HALF_DAY | Employee worked half a day | Gray |

## Record Attendance Form

Button: **+ Record** — appears top-right. Opens an inline form.

![Record Attendance form](../../../screenshots/captured/module-ui/hr/attendance/record-attendance-form.png)
*Record Attendance inline form with Employee, Date, Status, and Notes fields.*

![Attendance dropdowns](../../../screenshots/captured/module-ui/hr/attendance/attendance-dropdowns.png)
*Attendance Status dropdown options expanded: PRESENT, ABSENT, LATE, LEAVE, HALF_DAY.*

### Attendance Record Fields

| Field | Description |
|---|---|
| Employee | Employee select — choose from all employees |
| Date | Attendance date (defaults to today) |
| Status | PRESENT / ABSENT / LATE / LEAVE / HALF_DAY |
| Notes | Optional free-text notes |

## Attendance Log Columns

| Column | Description |
|---|---|
| Date | Attendance date |
| Employee | Employee full name |
| Dept | Employee department |
| Status | Attendance status badge |
| Clock In | Time clocked in (if recorded) |
| Clock Out | Time clocked out (if recorded) |
| Notes | Any notes on the record |

## Filters

| Filter | Description |
|---|---|
| From / To | Date range for the attendance report |
| Department | Filter by department |
| Status | Filter by attendance status |
