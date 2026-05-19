# Shift Planning

**Route:** `/dashboard/hr?tab=shifts`  
**Permission required:** `hr.view`

## What It Does

The Shifts tab manages workforce scheduling. It has two sections: **Shift Templates** (named work patterns with start/end times) and **Active Assignments** (which employees work which shift). Assignments are date-ranged so that changing shifts over time is tracked.

![Shifts tab](../../../screenshots/captured/module-ui/hr/hr/shifts-tab.png)
*Shifts tab showing Shift Templates table and Active Assignments table.*

## Shift Templates

Shift templates define reusable work patterns. Templates are assigned to employees via the Assign Shift form.

Button: **+ Template** — opens the New Shift Template form inline.

![New Shift Template form](../../../screenshots/captured/module-ui/hr/shifts/new-template-form.png)
*New Shift Template form with Name, Department, Start Time, End Time, and Notes fields.*

### Shift Template Fields

| Field | Label | Required | Description |
|---|---|---|---|
| `name` | Name | Yes | Template name, e.g. `Morning Shift` |
| `department` | Department (optional) | No | Restrict template to a department |
| `start_time` | Start Time | Yes | Shift start, e.g. `06:00` |
| `end_time` | End Time | Yes | Shift end, e.g. `14:00` |
| `notes` | Notes | No | Free-text notes |

### Template Table Columns

| Column | Description |
|---|---|
| Name | Template name |
| Hours | Start time – End time |
| Department | Department restriction (or "All") |
| Active | Whether template is active (Yes / No) |

## Shift Assignments

Assignments link an employee to a shift template for a date range. The Shifts tab shows all assignments active as of today.

Button: **+ Assign Shift** — opens the Assign Shift form inline.

![Assign Shift form](../../../screenshots/captured/module-ui/hr/shifts/assign-shift-form.png)
*Assign Shift form with Employee, Shift Template, Effective From, Effective To, and Supervisor fields.*

### Assignment Fields

| Field | Label | Required | Description |
|---|---|---|---|
| `employee_id` | Employee | Yes | Employee to assign |
| `shift_template_id` | Shift Template | Yes | Template to assign |
| `effective_from` | Effective From | Yes | Start date of assignment |
| `effective_to` | Effective To (optional) | No | End date — leave blank for open-ended |
| `supervisor_id` | Supervisor (optional) | No | Supervising employee |

### Active Assignments Columns

| Column | Description |
|---|---|
| Employee | Employee full name |
| Dept | Employee department |
| Shift | Assigned shift template name |
| Hours | Shift start – end time |
| From | Assignment effective from date |
| To | Assignment end date ("Open" if ongoing) |
