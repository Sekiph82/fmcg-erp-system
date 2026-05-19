# Timesheets & Expense Claims

---

## Timesheet Management

**Route:** `/dashboard/hr?tab=timesheets`  
**Permission required:** `hr.view`

### What It Does

The Timesheets tab tracks employee time entries by project or task. Timesheets go through a multi-level approval workflow (employee → manager → finalized). The dashboard shows total hours, overtime, and project-level breakdowns.

![Timesheets tab](../../../screenshots/captured/module-ui/hr/hr/timesheets-tab.png)
*Timesheets tab showing KPI summary, project hours breakdown, and navigation links.*

### Timesheet KPIs

| KPI | Description |
|---|---|
| Total Timesheets | All timesheet records |
| Pending Approval | Timesheets submitted, awaiting manager |
| Manager Approved | Approved by manager, not yet finalized |
| Rejected | Timesheets rejected |
| Finalized | Fully approved and closed |
| Employees | Distinct employees with timesheets this period |
| Total Hours | Total hours logged this period |
| Overtime Hours | Hours logged above standard working hours |
| Avg Hours/Employee | Average hours per employee |

### Timesheet Approval Workflow

```
Employee submits timesheet
    → Manager reviews in Approval Queue
    → Manager approves or rejects
    → HR/Finance finalizes
```

### Timesheets Navigation

| Section | Route |
|---|---|
| My Timesheets | `/dashboard/timesheets/my-timesheets` |
| New Time Entry | `/dashboard/timesheets/time-entry` |
| Weekly View | `/dashboard/timesheets/weekly-view` |
| Approval Queue | `/dashboard/timesheets/approval-queue` |
| Reports | `/dashboard/timesheets/reports` |
| AI Insights | `/dashboard/timesheets/ai` |

---

## Expense Claims

**Route:** `/dashboard/hr?tab=expenses`  
**Permission required:** `hr.view`

### What It Does

The Expenses tab manages employee expense claims: submission, line-manager approval, finance approval, and reimbursement. It supports cash advances, policy enforcement, and AI-flagged anomalies.

![Expenses tab](../../../screenshots/captured/module-ui/hr/hr/expenses-tab.png)
*Expense Claims tab showing KPI dashboard with claim counts, pending approvals, reimbursement totals, and AI alerts.*

### Expense KPIs

| KPI | Description |
|---|---|
| Total Claims | All expense claim records |
| Pending Approval | Claims awaiting manager or finance review |
| Finance Approved (Unpaid) | Approved but not yet reimbursed |
| Reimbursed This Month | Total amount reimbursed this month |
| Claimed This Month | Total amount claimed this month |
| Policy Violations | Open claims flagged for policy breach |
| Overdue Advances | Cash advances not yet settled |
| AI Alerts | AI-flagged duplicate or anomalous claims |

### Expense Claim Workflow

```
Employee submits claim (+ New Claim)
    → Manager reviews → approves or rejects
    → Finance approves → marks for reimbursement
    → Payment processed (M-Pesa or bank transfer)
    → Claim marked Reimbursed
```

### Expenses Navigation

| Section | Route |
|---|---|
| My Claims | `/dashboard/expenses/claims` |
| New Claim | `/dashboard/expenses/claims/new` |
| Approval Queue | `/dashboard/expenses/approval` |
| Reimbursement | `/dashboard/expenses/reimbursement` |
| Advances | `/dashboard/expenses/advances` |
| Categories | `/dashboard/expenses/categories` |
| Policies | `/dashboard/expenses/policies` |
| Reports | `/dashboard/expenses/reports` |
| AI Insights | `/dashboard/expenses/ai` |
