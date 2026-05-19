# Payroll Management

**Route:** `/dashboard/hr?tab=payroll`  
**Permission required:** `payroll.view`

## What It Does

The HR Payroll tab manages payroll periods — monthly groupings of employee salary lines. Each period starts as DRAFT, gets employee lines added manually, then is approved to lock it. Salary disbursement is handled via the Finance → M-Pesa bulk payment or bank transfer flow.

> **Note:** The payroll tab is a scaffold module. Automated PAYE/NSSF/NHIF calculations are handled outside this interface. Line values are entered manually or imported.

![Payroll tab](../../../screenshots/captured/module-ui/hr/hr/payroll-tab.png)
*Payroll tab showing payroll periods with period, status, and notes columns.*

## New Payroll Period Form

Button: **+ New Period** — opens an inline form.

![New Payroll Period form](../../../screenshots/captured/module-ui/hr/payroll/new-period-form.png)
*New Payroll Period form with Month, Year, and Notes fields.*

![Payroll month dropdown](../../../screenshots/captured/module-ui/hr/payroll/payroll-month-dropdown.png)
*Month dropdown expanded showing Jan through Dec.*

### New Period Fields

| Field | Label | Description |
|---|---|---|
| `period_month` | Month | Calendar month (Jan–Dec) |
| `period_year` | Year | Four-digit year |
| `notes` | Notes | Optional notes |

## Payroll Period Status Values

| Status | Badge | Meaning |
|---|---|---|
| `DRAFT` | Yellow | Open for editing — lines can be added |
| `APPROVED` | Green | Period locked — ready for payment |
| `PAID` | Blue | Payment disbursed |
| `CANCELLED` | Red | Period cancelled |

## Period Detail

Clicking **Open** on any period row opens the period detail view, which shows:

- Period header with status, employee count, total Gross, and total Net
- Payroll lines table (one row per employee)
- **+ Add Line** button (available when period is DRAFT)
- **Approve Period** button (available when period is DRAFT)

### Add Payroll Line Fields

| Field | Description |
|---|---|
| Employee | Employee for this line |
| Payment Method | MPESA / BANK / CASH (defaults to employee's method if blank) |
| Gross Pay (KES) | Gross salary amount |
| Net Pay (KES) | Net salary after deductions |
| Salary Components (JSON) | Optional JSON breakdown, e.g. `{"basic":50000,"transport":3000,"paye":-3000}` |

### Payroll Line Columns

| Column | Description |
|---|---|
| Employee | Employee full name |
| Dept | Department |
| Gross (KES) | Gross pay amount |
| Net (KES) | Net pay after deductions |
| Method | Payment method |
| Paid | Whether the line has been marked paid |
| Ref | Payment reference |

## Export

Approved periods can be exported via API:  
`GET /api/v1/hr/payroll/periods/{id}/export`

Use Finance → M-Pesa or bank transfer to disburse payments after approval.
