# HR & People Management — Module Overview

The HR & People Management module manages the full employee lifecycle: hiring, attendance, leave, payroll, shift planning, appraisals, training, and expense claims. All HR functions are accessible from the `/dashboard/hr` workspace.

## HR Workspace Tabs

| Tab | Key | Description |
|---|---|---|
| Overview | `overview` | KPI dashboard — Active Employees, Present Today, Pending Leave, Draft Payrolls |
| Employees | `employees` | Employee master records, create/edit/delete |
| Attendance | `attendance` | Daily attendance recording and reporting |
| Leave | `leave` | Leave requests and approvals |
| Payroll | `payroll` | Payroll periods, lines, and approval |
| Shifts | `shifts` | Shift templates and employee assignments |
| Recruitment | `recruitment` | Applicant Tracking System (ATS) |
| ESS | `ess` | Employee Self-Service portal |
| Appraisals | `appraisals` | Performance appraisal cycles |
| Training | `training` | Training programs, sessions, certifications |
| Timesheets | `timesheets` | Time tracking and approval |
| Expenses | `expenses` | Employee expense claims and reimbursement |

## Permission

All HR tabs require `hr.view`. The Payroll tab additionally requires `payroll.view`.

## Route

`/dashboard/hr?tab=<key>`
