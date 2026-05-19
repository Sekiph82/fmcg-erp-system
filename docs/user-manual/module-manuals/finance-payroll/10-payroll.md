# Kenya Payroll

**Route:** `/dashboard/payroll`  
**Permission required:** `payroll_ke.view` (view), `payroll_ke.create` (create runs)  
**Workspace tabs:** Overview, Profiles, Reports

---

## What It Does

The Kenya Payroll module calculates monthly statutory deductions in compliance with Kenya Finance Act 2023/2024 and generates payslips. Each payroll period is processed as a discrete "run" that can be reviewed before approval.

![Payroll Overview tab](../../../screenshots/captured/module-ui/finance-payroll/payroll/overview-tab.png)
*Payroll Overview showing four KPI tiles and the payroll runs table with PAYE, NHIF, NSSF, and net amounts.*

---

## Statutory Deductions

| Deduction | Description |
|---|---|
| **PAYE** | Pay As You Earn — progressive income tax bands per KRA |
| **NHIF / SHA** | National Hospital Insurance Fund / Social Health Authority |
| **NSSF** | National Social Security Fund — Tier I and Tier II |
| **AHL** | Affordable Housing Levy — 1.5% employee, 1.5% employer |

---

## Overview Tab — KPI Tiles

| Tile | Description |
|---|---|
| Total Runs | Count of all payroll runs |
| Latest Employees | Employee count on the most recent run |
| Latest Net Payroll | Net payroll total for the most recent run (KES) |
| YTD Net Paid | Year-to-date net paid across APPROVED and PAID runs |

---

## Payroll Runs Table

| Column | Field | Notes |
|---|---|---|
| Run No | `run_no` | Unique reference (monospace) |
| Period | `period_month`, `period_year` | e.g. January 2025 |
| Employees | `employee_count` | Headcount for this run |
| Gross | `total_gross` | Total gross pay |
| PAYE | `total_paye` | Income tax deducted; red |
| NHIF | `total_nhif` | Health fund deduction; orange |
| NSSF | `total_nssf` | Pension deduction; yellow |
| Net | `total_net` | Take-home pay total; green |
| Status | `status` | Run status badge |
| Action | link | "Open" → run detail page |

### Run Status Values

| Status | Colour |
|---|---|
| `DRAFT` | Gray |
| `PROCESSING` | Blue |
| `CALCULATED` | Yellow |
| `APPROVED` | Green |
| `PAID` | Green |
| `CANCELLED` | Red |

---

## New Payroll Run

**Requires:** `payroll_ke.create` permission.

Button: **+ New Payroll Run** (visible only if permission is granted).

### New Payroll Run Modal Fields

| Field | Label | Required | Notes |
|---|---|---|---|
| `period_month` | Month | Yes | January–December select |
| `period_year` | Year | Yes | Numeric year |
| `notes` | Notes | No | Optional context for this run |

Period start and end dates are automatically calculated from month and year (`first day` to `last day of month`).

After creation, the run enters `PROCESSING` state. Open the run detail page to review line items, approve, and mark as paid.

---

## Profiles Tab

**Tab key:** `profiles`

![Payroll Profiles tab](../../../screenshots/captured/module-ui/finance-payroll/payroll/profiles-tab.png)
*Profiles tab showing employee payroll profiles with salary, tax band, allowances, and deduction configuration.*

Employee payroll profiles store the standing pay data used in each run:

| Field | Description |
|---|---|
| Employee | Linked employee record |
| Basic Salary | Monthly gross salary |
| PAYE Band | Applicable KRA income tax band |
| Allowances | Housing, transport, and other taxable/non-taxable allowances |
| Deductions | Loan repayments, pension top-ups |
| Active | Whether profile is included in payroll runs |

---

## Reports Tab

**Tab key:** `reports`

![Payroll Reports tab](../../../screenshots/captured/module-ui/finance-payroll/payroll/reports-tab.png)
*Reports tab showing payroll statutory summary reports: PAYE, NHIF, NSSF, and P9A.*

Available reports:

| Report | Description |
|---|---|
| PAYE Summary | Monthly PAYE liability per employee for KRA filing |
| NHIF / SHA Schedule | Health fund contributions list |
| NSSF Schedule | Pension contributions list |
| P9A Annual Return | Annual employee tax certificate |
| Payslips | Individual payslip PDF for each employee |

---

## Payroll → Finance Integration

After a run is **APPROVED**, the payroll journal entry is posted to the General Ledger:

```
Debit:  Salaries Expense (Gross)
Credit: PAYE Payable
Credit: NHIF Payable
Credit: NSSF Payable
Credit: AHL Payable
Credit: Net Salary Payable
```

When the payment is processed, the **Net Salary Payable** is cleared via a cashbook payment entry.
