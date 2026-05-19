# Leave Management

**Route:** `/dashboard/hr?tab=leave`  
**Permission required:** `hr.view`

## What It Does

The Leave tab manages employee leave requests from submission through approval. Managers can review and approve or reject pending requests. Leave types cover statutory and discretionary categories.

![Leave tab](../../../screenshots/captured/module-ui/hr/hr/leave-tab.png)
*Leave Management tab showing leave requests with employee, type, date range, days, status, and review action.*

## New Leave Request Form

Button: **+ Request Leave** — opens an inline form.

![New Leave Request form](../../../screenshots/captured/module-ui/hr/leave/new-leave-form.png)
*New Leave Request inline form with Employee, Leave Type, Start Date, End Date, and Reason fields.*

![Leave type dropdown](../../../screenshots/captured/module-ui/hr/leave/leave-type-dropdown.png)
*Leave Type dropdown expanded: ANNUAL, SICK, MATERNITY, PATERNITY, UNPAID, COMPASSIONATE, OTHER.*

### Leave Request Fields

| Field | Label | Required | Description |
|---|---|---|---|
| `employee_id` | Employee | Yes | Employee submitting the leave |
| `leave_type` | Leave Type | Yes | See leave types below |
| `start_date` | Start Date | Yes | First day of leave |
| `end_date` | End Date | Yes | Last day of leave |
| `reason` | Reason | No | Optional reason text |

### Leave Types

| Type | Description |
|---|---|
| `ANNUAL` | Annual leave entitlement |
| `SICK` | Sick leave (medical) |
| `MATERNITY` | Maternity leave |
| `PATERNITY` | Paternity leave |
| `UNPAID` | Unpaid leave |
| `COMPASSIONATE` | Bereavement or compassionate leave |
| `OTHER` | Any other leave type |

## Leave Request Table Columns

| Column | Description |
|---|---|
| Employee | Employee name |
| Type | Leave type |
| Start | Start date |
| End | End date |
| Days | Number of days requested (system-calculated) |
| Status | Approval status badge |
| Notes | Review note from approver |

## Leave Approval Workflow

```
Employee submits leave request (status: PENDING)
    → Manager reviews: clicks "Review" on PENDING row
    → Review modal: select APPROVED or REJECTED, add note
    → Submit → status updated
    → APPROVED: leave days deducted from entitlement
    → REJECTED: request closed with note
```

## Approval Status Values

| Status | Badge | Meaning |
|---|---|---|
| `PENDING` | Yellow | Awaiting manager decision |
| `APPROVED` | Green | Leave approved |
| `REJECTED` | Red | Leave declined |
| `CANCELLED` | Gray | Cancelled by employee or HR |

## Filter

Filter leave requests by approval status using the status dropdown at the top of the list.
