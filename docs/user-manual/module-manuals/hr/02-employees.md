# Employee Management

**Route:** `/dashboard/hr?tab=employees`  
**Permission required:** `hr.view`

## What It Does

The Employees tab is the master record for all workforce members. It supports creating, editing, deleting, and searching employees. Each employee record stores identity, department, contact, payroll, and status information.

![Employees tab](../../../screenshots/captured/module-ui/hr/hr/employees-tab.png)
*Employees tab showing the employee list with code, name, department, role, and status columns.*

## New Employee Form

Button: **+ New Employee** — appears top-right of the Employees tab. Clicking opens an inline form (not a modal).

![New Employee form](../../../screenshots/captured/module-ui/hr/employees/new-employee-form.png)
*New Employee inline form showing all employee fields.*

![Employee dropdowns](../../../screenshots/captured/module-ui/hr/employees/employee-dropdowns.png)
*Status and Payment Method dropdown options expanded.*

### Employee Fields

| Field | Label | Type | Notes |
|---|---|---|---|
| `employee_code` | Employee Code | Text | Unique identifier, e.g. `EMP-001` |
| `full_name` | Full Name | Text | Employee full name |
| `department` | Department | Text | Department name |
| `role` | Role / Job Title | Text | Job title |
| `phone` | Phone | Text | Contact phone |
| `email` | Email | Text | Work email |
| `hire_date` | Hire Date | Date | Date employee joined |
| `salary_grade` | Salary Grade | Text | Grade tier, e.g. `G3` |
| `mpesa_number` | M-Pesa Number | Text | Mobile money number for salary |
| `bank_account` | Bank Account | Text | Bank account number |
| `status` | Status | Select | ACTIVE / INACTIVE / ON_LEAVE / TERMINATED |
| `payment_method` | Payment Method | Select | MPESA / BANK / CASH |

### Employee Status Values

| Status | Badge | Meaning |
|---|---|---|
| `ACTIVE` | Green | Currently employed |
| `INACTIVE` | Gray | Not active (e.g. probation hold) |
| `ON_LEAVE` | Yellow | On approved leave |
| `TERMINATED` | Red | Employment ended |

## Filters

| Filter | Description |
|---|---|
| Search | Text search on name or employee code |
| Department | Filter by department (populated from existing records) |
| Status | Filter by employee status |

## Import

The Employees tab includes an **Import** button (ImportModal component) for bulk employee uploads via CSV.

## Edit and Delete

Each row has **Edit** and **Delete** links. Edit opens the same inline form pre-populated. Delete triggers a confirmation modal before removing the record.
