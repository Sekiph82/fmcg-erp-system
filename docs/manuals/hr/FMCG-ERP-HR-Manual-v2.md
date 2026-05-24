# FMCG ERP — HR Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** HR Managers, HR Officers, Payroll Officers, Department Managers, Employees (ESS)  
**Modules Covered:** HR · Employees · Attendance · Leave · Payroll · Shifts · Recruitment · ESS · Appraisals · Training · Timesheets

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [HR Dashboard](#2-hr-dashboard)
3. [Employee Management](#3-employee-management)
4. [Attendance](#4-attendance)
5. [Leave Management](#5-leave-management)
6. [Payroll (HR View)](#6-payroll-hr-view)
7. [Shifts & Scheduling](#7-shifts--scheduling)
8. [Recruitment](#8-recruitment)
9. [Employee Self-Service (ESS)](#9-employee-self-service-ess)
10. [Appraisals & Performance](#10-appraisals--performance)
11. [Training & Development](#11-training--development)
12. [Timesheets](#12-timesheets)
13. [HR Expenses](#13-hr-expenses)
14. [Common Mistakes & Troubleshooting](#14-common-mistakes--troubleshooting)
15. [Related Modules](#15-related-modules)

---

## 1. Module Overview

**What it does:** Full human resources management — employee records, attendance tracking, leave administration, shift planning, recruitment, performance management, training, and employee self-service.

**Who uses it:**
- HR Manager — oversees all HR processes, approves leave and appraisals
- HR Officer — maintains employee records, processes attendance, manages recruitment
- Payroll Officer — syncs attendance and leave data to payroll
- Department Manager — approves leave requests, views team attendance
- Employee — submits leave, views payslips, updates personal details via ESS

**When to use it:**
- When onboarding a new employee
- When processing monthly leave summaries for payroll
- When running a recruitment campaign
- When scheduling shifts for factory workers
- When conducting annual performance appraisals
- When tracking training certifications

**Module overview:**

| Feature | Route | Purpose |
|---------|-------|---------|
| HR Hub | `/dashboard/hr` | All HR functions |

![HR Overview](../../user-manual/screenshots/captured/module-ui/hr/hr/overview-tab.png)
*HR module overview — headcount KPIs, attendance today, pending leave, and open vacancies.*

---

## 2. HR Dashboard

**Tab:** Overview

KPI cards:
- Total Headcount
- Active Employees
- Present Today (attendance)
- On Leave Today
- Pending Leave Requests
- Open Vacancies
- Upcoming Appraisals

Charts: Department headcount breakdown, attendance trend, leave utilization.

---

## 3. Employee Management

**Tab:** Employees  
**Required permission:** `hr.employees.view`

### What it does
Central employee master — personal details, employment information, contract type, department, role, salary grade, and emergency contacts.

![Employees Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/employees-tab.png)
*Employees list with name, department, job title, employment type, and status.*

### Creating a New Employee

Click **+ New Employee**:

![New Employee Form](../../user-manual/screenshots/captured/module-ui/hr/employees/new-employee-form.png)

| Section | Fields |
|---------|--------|
| Personal | Full Name, Date of Birth, Gender, Nationality, ID Number, Tax PIN (KRA) |
| Contact | Email, Phone, Emergency Contact Name/Phone |
| Employment | Department, Job Title, Employment Type, Start Date |
| Payroll | Salary Grade, Basic Salary, Bank Account, NSSF No, NHIF No |
| Contract | Contract Type (Permanent/Contract/Casual), Contract End Date |

**Employee Dropdowns:**

![Employee Dropdowns](../../user-manual/screenshots/captured/module-ui/hr/employees/employee-dropdowns.png)
*Department, job title, employment type, and salary grade dropdowns.*

### Employee Status Values

| Status | Meaning |
|--------|---------|
| ACTIVE | Currently employed |
| ON_PROBATION | Within probation period |
| ON_LEAVE | Currently on approved leave |
| SUSPENDED | Suspended pending investigation |
| TERMINATED | Employment ended |

### Required Before Payroll Can Process
- KRA PIN entered (required for PAYE calculation)
- NSSF number (for statutory deductions)
- NHIF/SHIF number
- Bank account details (for salary payment)
- Payroll profile linked (in Finance → Payroll)

---

## 4. Attendance

**Tab:** Attendance

### What it does
Record and track daily employee attendance — clock-in/out times, late arrivals, early departures, absent records.

![Attendance Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/attendance-tab.png)
*Attendance dashboard — today's attendance, absent report, and time analysis.*

### Recording Attendance

Click **+ Record Attendance**:

![Record Attendance Form](../../user-manual/screenshots/captured/module-ui/hr/attendance/record-attendance-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Employee | Yes | Select employee |
| Date | Yes | Default today |
| Time In | Yes | Clock-in time |
| Time Out | No | Clock-out time (can update later) |
| Status | Yes | Present / Absent / Late / Half Day |
| Notes | No | Reason for absence or note |

**Attendance Dropdowns:**

![Attendance Dropdowns](../../user-manual/screenshots/captured/module-ui/hr/attendance/attendance-dropdowns.png)
*Status dropdown and shift selection.*

### Biometric/RFID Integration
If biometric devices are integrated, attendance is auto-imported daily. Manual records supplement biometric data for exceptions.

### Attendance and Payroll Link
At month-end, attendance data feeds payroll:
- Absent days deducted from basic salary
- Late arrivals may trigger deduction (if policy configured)
- Overtime hours (if time-in/out tracked) added to payroll

---

## 5. Leave Management

**Tab:** Leave

### What it does
Manage employee leave — annual leave, sick leave, maternity/paternity, compassionate, and unpaid leave. Tracks leave balances, approvals, and calendar.

![Leave Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/leave-tab.png)
*Leave management — pending approvals, leave calendar, and balance summary.*

### Submitting Leave (HR on behalf of employee or via ESS)

Click **+ New Leave**:

![New Leave Form](../../user-manual/screenshots/captured/module-ui/hr/leave/new-leave-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Employee | Yes | |
| Leave Type | Yes | See below |
| Start Date | Yes | First day of leave |
| End Date | Yes | Last day of leave |
| Number of Days | Auto | Calculated (excludes weekends/public holidays) |
| Reason | No | Required for sick/compassionate |
| Attachment | No | Medical certificate for sick leave |

**Leave Type Dropdown:**

![Leave Type Dropdown](../../user-manual/screenshots/captured/module-ui/hr/leave/leave-type-dropdown.png)

### Leave Types

| Type | Annual Entitlement | Paid? |
|------|--------------------|-------|
| Annual Leave | 21 working days | Yes |
| Sick Leave | 7 days (30 days with certificate) | Yes |
| Maternity Leave | 90 days | Yes |
| Paternity Leave | 14 days | Yes |
| Compassionate Leave | 3 days | Yes |
| Study Leave | As approved | Partial |
| Unpaid Leave | As approved | No |

### Leave Approval Workflow
1. Employee submits (or HR submits on behalf)
2. Line manager notified — approves or rejects
3. HR receives final notification
4. Approved leave deducted from balance
5. Leave calendar updated — visible to team

### Leave Balance
Each employee has a leave balance per type. Balance updated at year-end (unused annual leave carried forward per policy). HR can manually adjust balances.

---

## 6. Payroll (HR View)

**Tab:** Payroll

![Payroll Tab (HR)](../../user-manual/screenshots/captured/module-ui/hr/hr/payroll-tab.png)
*HR payroll view — payroll run status and employee payslip access.*

HR view shows payroll periods and employee payslips. Processing done in Finance → Payroll. For full payroll documentation see Finance & Payroll Manual.

---

## 7. Shifts & Scheduling

**Tab:** Shifts

### What it does
Configure shift templates and assign employees to shifts. Used for factory workers, security, and shift-based operations.

![Shifts Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/shifts-tab.png)
*Shift management — shift templates and employee schedule.*

### Creating a Shift Template

Click **+ New Shift Template**:

![New Template Form](../../user-manual/screenshots/captured/module-ui/hr/shifts/new-template-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Shift Name | Yes | e.g. "Morning Shift A" |
| Start Time | Yes | e.g. 06:00 |
| End Time | Yes | e.g. 14:00 |
| Break Duration | No | Minutes (e.g. 30) |
| Night Shift | No | Toggle if crosses midnight |
| Overtime Threshold | No | Hours before OT applies |
| Days Active | Yes | Mon–Sun checkboxes |

### Assigning Employees to Shifts

Click **+ Assign Shift**:

![Assign Shift Form](../../user-manual/screenshots/captured/module-ui/hr/shifts/assign-shift-form.png)

| Field | Required |
|-------|----------|
| Employee | Yes |
| Shift Template | Yes |
| Effective From | Yes |
| Effective To | No (blank = indefinite) |

### Shift Handover
Shop floor shift handover managed in Manufacturing → Shop Floor → Handover tab (linked to production context).

---

## 8. Recruitment

**Tab:** Recruitment

### What it does
Manage the full recruitment lifecycle — job postings, applications, shortlisting, interviews, offers, and onboarding.

![Recruitment Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/recruitment-tab.png)
*Recruitment pipeline — open vacancies, candidates by stage, and hiring metrics.*

**Recruitment stages:**
`JOB_POSTED → APPLICATIONS_OPEN → SHORTLISTING → INTERVIEWS → OFFER → ACCEPTED → ONBOARDED`

**Creating a job posting:**
1. Recruitment → **+ New Vacancy**
2. Set job title, department, number of positions, salary range
3. Write job description
4. Set application deadline
5. Publish (internal / external)
6. Applications captured; move through pipeline stages

---

## 9. Employee Self-Service (ESS)

**Tab:** ESS

### What it does
Employee portal — employees can view payslips, submit leave, update personal details, view attendance, and access company documents.

![ESS Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/ess-tab.png)
*ESS configuration — manage which self-service features are enabled and employee portal access.*

**ESS features available to employees:**
- View and download payslips
- Submit leave requests
- View leave balances and history
- View attendance record
- Update personal details (address, emergency contact, bank details)
- View employment letter and contract
- Access company policy documents

**ESS access:** Employees log in via the same ERP login URL with their employee credentials (separate from admin accounts).

---

## 10. Appraisals & Performance

**Tab:** Appraisals

### What it does
Manage employee performance reviews — annual appraisals, KPI setting, and competency assessment.

![Appraisals Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/appraisals-tab.png)
*Appraisals — upcoming reviews, completed reviews, and performance scores.*

**Appraisal workflow:**
1. HR creates appraisal cycle (e.g. Annual 2026)
2. Employees receive self-assessment form
3. Manager completes manager assessment
4. HR reviews and calibrates scores
5. Employee acknowledges results
6. Salary review linked to performance score

---

## 11. Training & Development

**Tab:** Training

### What it does
Track employee training — planned, in progress, and completed training programs. Certification tracking.

![Training Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/training-tab.png)
*Training management — training calendar, individual training records, and certification expiry.*

**Training record fields:**
- Employee
- Training Name
- Category (Technical / Safety / Compliance / Soft Skills)
- Provider
- Start/End Date
- Certification (if applicable)
- Certification Expiry Date
- Status (Planned / Completed / Failed)
- Cost

**Certification alerts:** System flags certificates expiring within 60 days.

---

## 12. Timesheets

**Tab:** Timesheets

### What it does
Project-based or task-based time tracking for professional/salaried staff.

![Timesheets Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/timesheets-tab.png)
*Timesheets — weekly time entries by employee, project, and task.*

Timesheets feed into project costing and can trigger overtime calculations in payroll.

---

## 13. HR Expenses

**Tab:** Expenses (HR view)

![HR Expenses Tab](../../user-manual/screenshots/captured/module-ui/hr/hr/expenses-tab.png)
*Expense claims submitted by employees — view and approval status.*

Full expense management in Finance → Expenses. HR view shows claims pending manager approval.

---

## 14. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Payroll can't find employee | Employee not linked to payroll profile | Create payroll profile in Finance → Payroll → Profiles |
| Leave days not reducing balance | Leave type not configured with balance tracking | Check leave type settings: `deduct_from_balance = true` |
| Attendance not syncing to payroll | Payroll period closed before attendance finalized | Reopen period or adjust manually in payroll |
| Employee can't access ESS | ESS not enabled for their user account | Enable ESS in HR → ESS → manage user access |
| Appraisal cycle not appearing | Cycle date range doesn't include today | Check appraisal cycle start/end dates |
| Recruitment stage stuck | No interviewer assigned | Assign interviewer before moving to Interview stage |
| Shift not appearing in attendance | Shift not assigned to employee for this period | Assign shift in Shifts → Assign Shift with correct date range |

---

## 15. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Employee attendance finalized | Finance → Payroll (hours and deductions) |
| Leave approved | HR calendar + Payroll (leave deduction) |
| New employee onboarded | Finance → Payroll (profile creation) |
| Training certification | Compliance → Regulatory Certs (if operator certification required) |
| Timesheet approved | Finance → Project Costing |
| Expense approved | Finance → Expenses → Reimbursement |

---

*End of HR Manual v2*
