# HR and Payroll

**URLs:** `/dashboard/hr`, `/dashboard/payroll`  
**Module:** HR  
**Permission:** `hr.view`, `payroll_ke.view`

---

## Screenshot

> Screenshot pending: HR workspace — Employees tab

---

## HR Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | — | HR dashboard |
| Employees | ?tab=employees | Employee master |
| Attendance | ?tab=attendance | Time and attendance |
| Leave | ?tab=leave | Leave management |
| Payroll | ?tab=payroll | Payroll run (shortcut to Payroll workspace) |
| Shifts | ?tab=shifts | Shift scheduling |
| Recruitment | ?tab=recruitment | Hiring pipeline |
| ESS | ?tab=ess | Employee Self-Service portal |
| Appraisals | ?tab=appraisals | Performance reviews |
| Training | ?tab=training | Training records |
| Timesheets | ?tab=timesheets | Time-based billing/tracking |
| Expenses | ?tab=expenses | Expense claims |

---

## Kenya Payroll Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Overview | — | Payroll run summary |
| Profiles | ?tab=profiles | Employee payroll configs |
| Reports | ?tab=reports | P9, NHIF, NSSF, payslips |

---

## Kenya Statutory Obligations

| Deduction | Rate | Frequency |
|---|---|---|
| PAYE | Progressive (KRA bands) | Monthly |
| NHIF | Per income bracket | Monthly |
| NSSF | 6% employee + 6% employer | Monthly |
| Housing Levy | 1.5% + 1.5% | Monthly |

All filed via:
- PAYE: KRA iTax portal
- NHIF: NHIF portal
- NSSF: NSSF portal

---

## ESS (Employee Self-Service)

Employees can:
- View their payslips
- Apply for leave
- Submit expense claims
- Update personal details

Access via `/dashboard/hr?tab=ess` (admin/HR view) or employee-facing portal.

---

## Related Workspaces

- Finance (Expenses tab) — expense claims cross-posted
- Admin (Users tab) — employee users linked to HR records
