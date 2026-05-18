# HR User Manual

**Audience:** HR Officer, Payroll Clerk  
**URLs:** `/dashboard/hr`, `/dashboard/payroll`  
**Permission required:** `hr.view`, `hr.create`, `payroll_ke.view`

---

## Your Role

You manage employee records, attendance, leave, and payroll. Kenya statutory deductions (PAYE, NHIF, NSSF, Housing Levy) must be calculated and filed correctly.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| HR workspace | /dashboard/hr | All HR activities |
| Kenya Payroll | /dashboard/payroll | Monthly payroll processing |

---

## Screenshot

> Screenshot pending: HR workspace — Employees tab

---

## Create an Employee Record

1. Go to `/dashboard/hr?tab=employees`
2. Click **+ New Employee**
3. Fill in:
   - Full name
   - National ID number
   - KRA PIN (required for PAYE)
   - NHIF number
   - NSSF number
   - Date of birth
   - Job title / department
   - Hire date
   - Employment type: Permanent / Contract / Casual
   - Bank account details (for payroll payment)
4. Save

> Screenshot pending: HR — Employees tab with employee list

---

## Payroll Profile Setup

For each employee, set up their payroll profile:
1. HR → Payroll tab (or use Payroll workspace directly)
2. Find the employee → **Payroll Profile**
3. Enter:
   - Basic salary (KES)
   - Housing allowance
   - Transport allowance
   - Other allowances
   - Standard deductions (pension, SACCO)
4. System calculates PAYE, NHIF, NSSF, Housing Levy automatically
5. Verify net pay
6. Save

> Screenshot pending: Payroll — Profiles tab

---

## Run Monthly Payroll

1. Go to `/dashboard/payroll`
2. Click **+ New Payroll Run**
3. Select:
   - Period: Month / Year
   - Employees: All or specific department
4. System calculates:
   - Gross pay (basic + allowances)
   - PAYE (per KRA tax bands)
   - NHIF (per NHIF contribution rates)
   - NSSF (6% employee + 6% employer)
   - Housing Levy (1.5% employee + 1.5% employer)
   - Net pay
5. Review payroll summary
6. Click **Approve Run**
7. Generate payslips (email or PDF)
8. Process payment (bank transfer, M-Pesa)

> Screenshot pending: Kenya Payroll workspace — overview

---

## Attendance Management

Daily attendance tracking:
1. HR → Attendance tab
2. View: Present, Absent, Late, On Leave
3. Mark attendance manually or confirm biometric import
4. Late arrivals: enter actual arrival time

> Screenshot pending: HR — Attendance tab

---

## Leave Management

Employee leave application:
1. HR → Leave tab
2. Click **+ New Leave Application**
3. Employee, leave type, from date, to date, reason
4. Submit for approval (supervisor approves)
5. After approval: attendance shows "On Leave"

Leave types: Annual, Sick, Maternity, Paternity, Compassionate.

**Ensure leave balances are set up in payroll profiles before go-live.**

---

## Recruitment

1. HR → Recruitment tab
2. Click **+ New Job Posting**
3. Fill in: job title, department, qualifications, closing date
4. Applicants tracked through: Applied → Shortlisted → Interviewed → Offered → Hired

---

## Employee Expenses

Employee submits expense claim:
1. HR → Expenses tab
2. Click **+ New Expense**
3. Employee name, date, description, amount, receipt upload
4. Submit for approval
5. Approved expenses paid in next payroll run

---

## Payroll Reports

1. Payroll → Reports tab
2. Available reports:
   - **P9 Form** (annual PAYE return to KRA)
   - **NHIF schedule** (monthly submission to NHIF)
   - **NSSF schedule** (monthly submission to NSSF)
   - **Payroll summary** by department
   - **Payslip export** (PDF or Excel)

> Screenshot pending: Payroll — Reports tab

---

## Kenya Statutory Deductions Reference

| Deduction | Rate | Who pays |
|---|---|---|
| PAYE | Progressive per KRA bands | Employee |
| NHIF | Per income bracket | Employee |
| NSSF | 6% of gross (capped) | Employee + Employer |
| Housing Levy | 1.5% of gross | Employee + Employer |

System calculates these automatically based on current rates. Update rates in Payroll Settings when KRA/NHIF/NSSF announce changes.

---

## Common Mistakes

| Mistake | How to Avoid |
|---|---|
| Missing KRA PIN | KRA PIN is mandatory for PAYE — add before running payroll |
| Wrong bank account | Double-check bank account number before approving payroll payment |
| Payroll run for wrong period | Check month/year before approving |
| Leave not deducted from pay | Ensure leave type is configured as "unpaid" if applicable |

---

## Troubleshooting

**Problem:** PAYE calculation seems wrong  
**Solution:** Check KRA tax bands in Payroll Settings — may need update if KRA changed rates

**Problem:** Employee payslip shows no NHIF deduction  
**Solution:** Check employee payroll profile — NHIF number must be entered

**Problem:** Cannot approve payroll run — "Pending approvals"  
**Solution:** Check admin approval workflow — payroll runs may need manager sign-off

---

## Training Checklist

- [ ] Can create a complete employee record with statutory numbers
- [ ] Can set up a payroll profile with allowances and deductions
- [ ] Can run and approve a monthly payroll
- [ ] Can generate payslips and email to employees
- [ ] Can generate P9, NHIF schedule, NSSF schedule reports
- [ ] Can process an employee leave application
- [ ] Can record and approve an employee expense claim
- [ ] Understands current PAYE, NHIF, NSSF, and Housing Levy rates
