# HR Overview Dashboard

**Route:** `/dashboard/hr?tab=overview`  
**Permission required:** `hr.view`

## What It Does

The HR Overview tab is the entry point for the HR workspace. It displays four KPI tiles giving an at-a-glance view of the current workforce state.

![HR Overview tab](../../../screenshots/captured/module-ui/hr/hr/overview-tab.png)
*HR Overview tab showing KPI tiles for Active Employees, Present Today, Pending Leave, and Draft Payrolls.*

## KPI Tiles

| KPI | Description |
|---|---|
| Active Employees | Count of employees with status `ACTIVE` |
| Present Today | Employees with an attendance record of `PRESENT` for today's date |
| Pending Leave | Leave requests in `PENDING` approval status |
| Draft Payrolls | Payroll periods in `DRAFT` status |
