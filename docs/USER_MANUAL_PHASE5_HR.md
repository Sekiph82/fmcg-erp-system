# PHASE 5 — HR & PAYROLL
## FMCG ERP User Manual

---

<a name="expenses"></a>
# MODULE 31: EXPENSE CLAIMS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Expense Claims manages the complete process of employee expense reimbursement — from submission through manager approval, finance approval, to payment. It enforces expense policies (per-diem limits, receipt requirements, approval thresholds) and tracks advances.

**Why it exists in FMCG context:**  
Field sales teams, supply chain staff, and management travel extensively. Without a structured system, employees submit hand-written receipts months late, managers approve expenses without reviewing policy compliance, and Finance has no visibility into outstanding reimbursements. The system enforces policy consistently and provides real-time expense visibility.

---

## 2. USER ROLES

| Role | Responsibilities |
|---|---|
| **Employee** | Submits claims, checks status |
| **Line Manager** | First-level approval of team's claims |
| **Finance Manager** | Final approval, policy override |
| **Payroll Officer** | Processes reimbursement payments |

---

## 3. KEY CONCEPTS

**Expense Category:** Type of expense — Accommodation, Meals, Transport, Communication, Fuel, Training. Each category has a daily/per-trip limit.

**Expense Policy:** Rules per employee grade — e.g., Grade A staff: hotel up to KES 8,000/night. Grade B: KES 5,000/night.

**Receipt Threshold:** Minimum expense amount requiring a receipt (e.g., above KES 500 requires receipt).

**Expense Advance:** Money given to employee before a trip — must be settled within 7 days of return.

**Claim Status:** DRAFT → SUBMITTED → MANAGER_APPROVED → FINANCE_APPROVED → PAID → REJECTED

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: New Expense Claim (`/dashboard/expenses/claims/new`)

**Fields:**
| Field | Description | Required? |
|---|---|---|
| Claim Title | Brief description | Yes |
| Business Purpose | Why was this expense incurred? | Yes |
| Trip Start / End Date | Date range of travel/activity | Yes |

**Per expense line:**
| Field | Description |
|---|---|
| Date | Date expense was incurred |
| Category | Accommodation / Meals / Transport / etc. |
| Description | What specifically? (e.g., "Lunch with Carrefour buyer") |
| Amount (KES) | Amount spent |
| Receipt | Upload photo of receipt |
| Billable to Customer? | If this was a client-entertainment expense |

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Employee Submitting an Expense Claim

**Step 1 — During or immediately after activity**
- Keep all receipts (physical or photo)
- Take photos of receipts immediately (they fade quickly)

**Step 2 — Create claim**
- Go to `/dashboard/expenses/claims/new`
- Enter claim title: "Mombasa Sales Visit — May 5–6, 2024"
- Business purpose: "Customer visits: 5 distributors in Mombasa"

**Step 3 — Add expense lines**
- Line 1: Travel — Bus fare Nairobi-Mombasa — KES 1,800 — Upload bus ticket photo
- Line 2: Accommodation — Hotel Serena — 1 night — KES 5,500 — Upload receipt
- Line 3: Meals — 2 days × per-diem KES 800 — KES 1,600 (no receipt needed for per-diem)
- Line 4: Transport — Local taxi — KES 400 (below receipt threshold)

**Step 4 — Review totals**
- Total claim: KES 9,300
- System checks against policy: All amounts within limits? Yes
- Click **Submit**

**Step 5 — Manager review**
- Line Manager receives notification
- Reviews claim: is this trip legitimate? Are amounts reasonable?
- If any line looks questionable: sends back with comment
- If all OK: clicks **Approve**

**Step 6 — Finance review** (for claims above threshold)
- Finance Manager reviews and approves
- Checks: were advances already given? Deduct if so.
- Confirms budget availability for cost center

**Step 7 — Payment**
- Approved claims go to Payroll queue
- Paid with next payroll run (or ad-hoc payment if urgent)
- Employee receives notification: "Your claim of KES 9,300 has been approved for payment"

---

### Workflow: Managing an Expense Advance

**Step 1** — Employee requests advance before trip  
**Step 2** — Go to `/dashboard/expenses/advances`  
**Step 3** — Click **New Advance Request**  
**Step 4** — Enter: Amount needed, purpose, expected return date  
**Step 5** — Manager approves  
**Step 6** — Finance releases advance  
**Step 7** — After trip: employee submits expense claim  
**Step 8** — System automatically deducts advance from reimbursable amount  
**Step 9** — If employee spent less than advance: **returns balance** to Finance  
**Step 10** — If no claim within 7 days: system escalates to HR  

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Submit claims within 7 days of expense date
- ✅ Take photos of receipts immediately — they fade and tear
- ✅ Always state the business purpose (who did you meet, why, outcome)
- ✅ Settle advances within 7 days of return

### DON'T:
- ❌ Never submit personal expenses as business expenses
- ❌ Don't inflate amounts above what was actually paid
- ❌ Never claim for entertainment without stating who was entertained and the business purpose
- ❌ Don't submit paper receipts weeks later — photo immediately

---

## QUICK TRAINING SUMMARY — Expense Claims

> **What:** Digital expense submission, approval workflow, and reimbursement tracking.  
> **Status:** Draft → Submitted → Manager Approved → Finance Approved → Paid.  
> **Receipt rule:** Above KES 500 = receipt required. Per-diem = no receipt needed.  
> **Golden rule:** Submit within 7 days. Advance settlement within 7 days of return.

---

<a name="recruitment"></a>
# MODULE 32: RECRUITMENT / ATS

---

## 1. MODULE OVERVIEW

**What this module does:**  
The Applicant Tracking System (ATS) manages the full recruitment lifecycle: job requisition (request to hire), job posting, candidate applications, interview scheduling, offer management, and onboarding trigger. It ensures a consistent, fair, and documented hiring process.

**Why it exists in FMCG context:**  
FMCG companies have high staff turnover — particularly in sales and production. Unstructured recruitment leads to poor hires, legal risks (undocumented interview decisions), and long vacancy periods that affect output. The ATS provides a professional, consistent process that builds a talent pipeline over time.

---

## 3. KEY CONCEPTS

**Job Requisition:** A formal request from a department head to hire a person for a specific role. Must be approved before recruiting begins.

**Job Posting:** The advertisement for the role (internal and/or external).

**Pipeline Stage:**
1. Applied
2. Screening
3. Phone Interview
4. Technical Interview / Assessment
5. Final Interview
6. Reference Check
7. Offer
8. Hired

**Pipeline Board:** Kanban-style view showing candidates at each stage.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Full Recruitment Process

**Step 1 — Raise Job Requisition**
- Department Head goes to `/dashboard/recruitment/requisitions`
- Clicks **New Requisition**
- Fills: Job Title, Department, Grade, Number of Positions, Budget, Justification
- Submits for approval (HR Manager and Finance)
- Once approved: HR team can begin recruiting

**Step 2 — Post Job**
- HR creates Job Posting from the approved requisition
- Job description, requirements, salary range (if disclosable)
- Select posting channels: Internal noticeboard, External job sites, LinkedIn, WhatsApp
- Click **Publish**

**Step 3 — Screen Applications**
- Applications arrive in candidate list
- HR screens against minimum requirements
- Move suitable candidates to "Phone Interview" stage
- Send automated rejection to non-qualifying candidates

**Step 4 — Interview Process**
- For each stage:
  - Schedule interview from candidate record (links to Calendar module)
  - Interviewers complete feedback form after interview
  - System calculates average score across all interviewers
- Move candidates forward or reject at each stage

**Step 5 — Make Offer**
- Final candidate selected
- Go to `/dashboard/recruitment/offers`
- Click **New Offer** for candidate
- Enter: Salary, start date, benefits, any conditions
- System sends offer letter via email
- Candidate accepts/declines through portal or email reply

**Step 6 — Hire**
- Once candidate accepts:
- Click **Mark Hired** in system
- HR receives notification to prepare onboarding
- Employee profile created in HR module
- Payroll profile setup triggered

---

## QUICK TRAINING SUMMARY — Recruitment / ATS

> **What:** End-to-end hiring process from job requisition to offer letter.  
> **Pipeline:** Applied → Screened → Interviews → Offer → Hired. Track all candidates in one place.  
> **Key rule:** Document every interview feedback score. It protects against legal disputes.  
> **AI:** CV screening assistance, candidate ranking — always human-verified.

---

<a name="ess"></a>
# MODULE 33: EMPLOYEE SELF-SERVICE (ESS)

---

## 1. MODULE OVERVIEW

**What this module does:**  
Employee Self-Service gives every employee access to their own HR information — payslips, leave balance, attendance records, HR documents, and requests — without needing to contact the HR team for every query.

**Why it exists in FMCG context:**  
HR teams in FMCG handle 200–500 employees across multiple sites. Employees calling HR to ask "How many leave days do I have?" or "Can I see my last payslip?" consumes hours that HR could use for strategic work. ESS reduces HR administrative queries by 60%.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Employee Applying for Leave

**Step 1** — Employee logs into ESS portal: `/dashboard/ess`  
**Step 2** — Goes to **Leave** section  
**Step 3** — Sees their leave balance: Annual (12 days remaining), Sick (3 days remaining), etc.  
**Step 4** — Clicks **Apply for Leave**  
**Step 5** — Fills:
   - Leave type: Annual Leave
   - Start date: 20-May-2024
   - End date: 24-May-2024 (5 working days)
   - Reason: Family vacation  
**Step 6** — Clicks **Submit**  
**Step 7** — Line Manager receives notification  
**Step 8** — Manager reviews: Is this period OK? Are there other team members on leave? Can we cover?  
**Step 9** — Manager clicks **Approve** or **Decline** with reason  
**Step 10** — Employee notified immediately  
**Step 11** — On 20-May: leave days deducted from balance automatically  

---

### Workflow: Employee Viewing Payslip

**Step 1** — Employee goes to ESS  
**Step 2** — Clicks **Documents → Payslips**  
**Step 3** — List of all payslips by month  
**Step 4** — Click any month to view detailed breakdown:
   - Basic salary
   - Allowances
   - Deductions (PAYE, NHIF, NSSF, NSSF AHL)
   - Net pay  
**Step 5** — Download as PDF for records  

---

## QUICK TRAINING SUMMARY — ESS

> **What:** Employee self-service — leave, attendance, payslips, documents, HR requests.  
> **Key benefit:** Employees handle their own queries 24/7 without calling HR.  
> **Leave approval:** Submit → Manager approves/declines → Balance updated automatically.

---

<a name="appraisals"></a>
# MODULE 34: PERFORMANCE APPRAISALS

---

## 1. MODULE OVERVIEW

**What this module does:**  
Performance Appraisals manages the complete performance review cycle — KPI setting, self-review, manager review, HR calibration, final rating, and development planning. Supports both annual and mid-year reviews.

**Why it exists in FMCG context:**  
Performance management in FMCG is critical for retention and productivity. Without a structured appraisal process, reviews are inconsistent ("my manager gives everyone the same rating"), demotivating, and legally risky. A systematic appraisal process builds trust and links performance to rewards.

---

## 3. KEY CONCEPTS

**Appraisal Period:** The timeframe being reviewed (e.g., Jan–Dec 2023).

**KPI:** Key Performance Indicator — a specific, measurable target (e.g., "Achieve sales of KES 5,000,000 in Q2").

**Competency:** A behavioral quality evaluated (e.g., "Teamwork", "Problem Solving", "Customer Focus").

**Rating Scale:** Typically 1–5:
- 1: Significantly Below Expectations
- 2: Below Expectations
- 3: Meets Expectations
- 4: Exceeds Expectations
- 5: Outstanding

**Calibration:** The HR review process where all ratings are reviewed together to ensure consistency across managers.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Annual Appraisal Cycle

**Step 1 — HR opens appraisal period**
- HR Manager goes to `/dashboard/appraisals/periods`
- Creates new period: "FY2024 Annual Review"
- Sets: review period, template to use, deadlines for each stage
- Clicks **Open** — all employees in scope receive notification

**Step 2 — Employee completes self-review**
- Employee goes to Self Review section
- For each KPI: rate achievement (1–5) and write evidence
- For each competency: self-rate and describe examples
- Submit by deadline

**Step 3 — Manager review**
- Manager opens team members' appraisals in Manager Queue
- For each employee: review their self-ratings, add manager ratings and comments
- Manager can accept or adjust employee's self-ratings (with justification)
- Submit manager review

**Step 4 — HR calibration**
- HR reviews all ratings across the company
- Checks for rating distribution (too many 5s? Everyone rated 3?)
- Discusses outliers with department heads
- Makes calibration adjustments if needed (must be documented with reason)

**Step 5 — Development planning**
- Based on appraisal outcome, manager and employee co-create development plan:
  - Training needs
  - Stretch assignments
  - Mentoring arrangements
  - Skills to develop
- Go to Development Plans section, enter plan items

**Step 6 — Close period**
- HR closes the appraisal period
- Final ratings locked — no further changes
- Reports generated for compensation team (salary review, bonus recommendations)

---

## QUICK TRAINING SUMMARY — Performance Appraisals

> **What:** Structured annual performance review with KPI scoring, competency rating, and development planning.  
> **Cycle:** Self-review → Manager review → HR calibration → Development plans.  
> **Key rule:** Be specific and evidence-based in ratings. "Good performance" is not evidence.  
> **AI assistance:** Suggests development plan items, detects rating inconsistencies.

---

<a name="training"></a>
# MODULE 35: TRAINING & SKILLS MANAGEMENT

---

## 1. MODULE OVERVIEW

**What this module does:**  
Training Management tracks all employee training — programs, sessions, attendance, certifications, and skills. The Skill Matrix shows the skills coverage across the team, enabling gap analysis and succession planning.

**Why it exists in FMCG context:**  
Regulatory compliance (GMP, HACCP, food safety) requires documented training. Equipment certifications (forklift, boiler operation) require regular renewal. Without a system, tracking who needs retraining and when certifications expire is a spreadsheet nightmare.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Managing a Training Session

**Step 1** — Go to `/dashboard/training/sessions`, click **New Session**  
**Step 2** — Link to Training Program (e.g., "Food Safety & Hygiene — Level 1")  
**Step 3** — Set: Date, Time, Venue, Trainer, Max Participants  
**Step 4** — Add attendees: select employees from HR master  
**Step 5** — Day of training: trainer marks attendance (Present / Absent)  
**Step 6** — After training: trainer enters assessment results (pass/fail %)  
**Step 7** — Click **Complete Session**  
**Step 8** — System:
   - Updates each attendee's skill profile
   - Issues certifications to those who passed
   - Calculates certification expiry date
   - Updates Skill Matrix  
**Step 9** — Employees with failed assessment: system schedules retraining  

---

## QUICK TRAINING SUMMARY — Training & Skills

> **What:** Track training programs, sessions, attendance, assessments, and certifications.  
> **Skill Matrix:** Visual map showing which skills are covered by which employees.  
> **Certification alerts:** System warns 30 days before any certification expires.  
> **Compliance note:** All GMP and HACCP training must be recorded here for audit evidence.

---

<a name="timesheets"></a>
# MODULE 36: TIMESHEET MANAGEMENT

---

## 1. MODULE OVERVIEW

**What this module does:**  
Timesheet Management enables employees to record their daily working hours across different cost centers, projects, or activities. Provides the data for payroll, project costing, and compliance with the Employment Act (overtime tracking).

**Why it exists in FMCG context:**  
Production workers in Kenya are governed by working hours regulations. Overtime must be paid at premium rates. Without timesheet records, overtime is either missed (underpayment, legal risk) or overpaid (cost leakage). Timesheets also enable project costing — how many hours did the new product launch consume?

---

## 3. KEY CONCEPTS

**Timesheet Header:** One timesheet per employee per week.

**Timesheet Line:** One row per day per activity (e.g., "Monday — Production Line A — 8 hours").

**Daily Cap:** System enforces maximum 16 hours per day (legal + practical limit).

**Auto-Fill from Attendance:** If attendance system (biometric) is integrated, timesheet can be auto-populated from punch records.

**Overtime:** Hours beyond 8 per day or 40 per week — flagged for payroll premium calculation.

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Employee Completing Weekly Timesheet

**Step 1** — Go to `/dashboard/timesheets/time-entry`  
**Step 2** — Week is pre-populated with date columns  
**Step 3** — For each day:
   - Click the day
   - Enter hours worked
   - Select activity/project/cost center
   - Notes (optional)  
**Step 4** — System shows daily totals and weekly total  
**Step 5** — Review: are there any days missing? Any overtime flags?  
**Step 6** — Click **Submit**  
**Step 7** — Line Manager receives notification  
**Step 8** — Manager reviews and approves (or sends back with comment)  
**Step 9** — Once manager approves: timesheet locked, feeds to payroll calculation  

---

## QUICK TRAINING SUMMARY — Timesheets

> **What:** Weekly recording of working hours per employee for payroll, compliance, and project costing.  
> **Submit by:** Every Friday for the current week.  
> **Approval:** Line manager approves within 2 working days.  
> **Overtime:** System auto-calculates. Any hours above 8/day or 40/week flagged as overtime.

---

<a name="payroll"></a>
# MODULE 37: KENYA PAYROLL

---

## 1. MODULE OVERVIEW

**What this module does:**  
Kenya Payroll calculates statutory payroll for all employees: PAYE (income tax per Finance Act 2024 progressive bands), NHIF (17-tier National Health Insurance Fund), NSSF (6% contribution subject to cap), and AHL (1.5% Affordable Housing Levy). It generates payslips and statutory reports for KRA and government agencies.

**Why it exists in FMCG context:**  
Kenyan payroll is highly regulated with complex tax tables that change annually. Manual PAYE calculation is error-prone, and non-compliance attracts KRA penalties. The system auto-calculates all deductions per the current Finance Act and generates the exact KRA-format reports required for remittance.

**Business impact:**  
- Eliminates PAYE calculation errors
- Generates KRA P10 and P9A reports automatically
- Ensures NHIF and NSSF deductions are accurate
- AHL (new in Finance Act 2023) handled automatically
- Full payslip for every employee

---

## 3. KEY CONCEPTS

**PAYE (Pay As You Earn):** Income tax deducted from gross salary on a progressive scale:
| Monthly Taxable Income | PAYE Rate |
|---|---|
| Up to KES 24,000 | 10% |
| KES 24,001 – 32,333 | 25% |
| KES 32,334 – 500,000 | 30% |
| Above KES 500,000 | 35% |

**Personal Relief:** KES 2,400/month deducted from PAYE liability. All employees receive this.

**NHIF:** National Health Insurance Fund. 17-tier table based on gross salary (ranges from KES 150 for lowest earners to KES 1,700 for highest).

**NSSF (2013 Act):** 6% of gross salary, maximum KES 12,000/month employer + KES 12,000/month employee.

**AHL (Affordable Housing Levy):** 1.5% of gross salary. Employer matches 1.5%. Effective 2023.

**Payroll Profile:** Per-employee record with: KRA PIN, NHIF number, NSSF number, salary structure, bank account.

**Payroll Run:** A monthly calculation batch for all employees in the group.

---

## 4. SCREEN-BY-SCREEN GUIDE

### Screen: Kenya Payroll Dashboard (`/dashboard/payroll`)

**Shows:**
- Current period (month)
- Status of current payroll run
- Total gross payroll vs. last month
- Total PAYE due to KRA
- Total NHIF due
- Total NSSF due
- Net pay total (what employees actually receive)

### Screen: Employee Payroll Profile (`/dashboard/payroll/profiles`)

**Per employee:**
| Field | Description |
|---|---|
| KRA PIN | Required for PAYE filing |
| NHIF Number | Required for NHIF deduction |
| NSSF Number | Required for NSSF |
| Gross Salary | Monthly gross before deductions |
| Payment Bank | Bank and account number for salary payment |
| Bank Name | Employee's bank |
| Tax Exemptions | Any approved tax relief (disability, mortgage interest) |

### Screen: Payroll Run (`/dashboard/payroll/runs`)

**Creating a new run:**
1. Click **New Payroll Run**
2. Select month
3. Click **Calculate**
4. System processes every employee

**For each employee, system calculates:**
1. Gross salary (from profile)
2. NHIF: look up 17-tier table → deduction amount
3. NSSF: 6% of gross, capped at KES 12,000
4. AHL: 1.5% of gross
5. Taxable income: Gross minus NHIF (NHIF is pre-tax)
6. PAYE: Apply progressive bands to taxable income
7. Subtract personal relief (KES 2,400)
8. Net PAYE payable
9. Net Pay: Gross – NHIF – NSSF – AHL – PAYE – any other deductions

---

## 5. STEP-BY-STEP WORKFLOWS

### Workflow: Monthly Payroll Processing

**Frequency:** Once per month, typically by the 28th

**Step 1 — Verify employee profiles**
- Go to `/dashboard/payroll/profiles`
- Check no employees are missing KRA PIN, NHIF, NSSF numbers
- System blocks payroll for employees with missing statutory data (business guard active)
- Fix any missing data before proceeding

**Step 2 — Capture salary changes**
- Were there any promotions or salary adjustments this month?
- Update affected employee profiles before running payroll

**Step 3 — Create payroll run**
- Click **New Payroll Run**
- Select month: May 2024
- Click **Calculate**
- Wait 30–60 seconds

**Step 4 — Review payroll output**
- System shows: each employee's earnings and deductions
- Check totals: are PAYE/NHIF/NSSF totals consistent with previous months?
- Flag any unusual amounts (large increase/decrease from last month?)
- Check: any employee with zero net pay? (may indicate setup error)

**Step 5 — Approve payroll**
- HR Manager reviews
- Finance Manager reviews and approves
- Click **Approve Run**
- Payroll is now locked — no further changes

**Step 6 — Generate payslips**
- Click **Generate Payslips**
- Individual payslips created for each employee
- Employees can view in ESS portal immediately
- Optionally: email payslips to employees

**Step 7 — Generate statutory reports**
- Click **Generate Reports**
- Reports generated:
  - **P10 (Monthly PAYE Return):** Submit to KRA via iTax
  - **NHIF Schedule:** Submit to NHIF portal
  - **NSSF Schedule:** Submit to NSSF portal
  - **AHL Return:** Submit as required
- Download each report in required format (Excel/CSV for KRA)

**Step 8 — Process payments**
- Payroll export: total net pay per employee
- Treasury uploads to bank for employee salary payments
- Government remittances: PAYE to KRA by 9th of following month, NHIF and NSSF by the 15th

---

## 6. REAL BUSINESS SCENARIOS

### Scenario: New Employee Joining Mid-Month
**Situation:** New Production Manager joins 15th May. How is May salary calculated?

**Action:**
1. Set up employee payroll profile with start date 15-May
2. System auto-calculates pro-rated salary: (16 working days in May ÷ 22 total working days) × full month salary
3. PAYE, NHIF, NSSF calculated on the pro-rated amount
4. First payslip shows pro-rated figures

---

### Scenario: KRA Objection to PAYE Filing
**Situation:** KRA sends query about PAYE for employee John Kamau — mismatch with iTax.

**Action:**
1. Pull John Kamau's payslip for the disputed month
2. Download PAYE calculation breakdown
3. System shows: gross, NHIF deduction, taxable income, progressive tax calculation, personal relief applied
4. Compare to KRA's calculation — find the discrepancy
5. If KRA is correct: process adjustment in next payroll run
6. If system is correct: prepare reconciliation statement to submit to KRA

---

## 7. DO'S AND DON'TS

### DO:
- ✅ Collect all KRA PINs and NHIF/NSSF numbers before first payroll run — system blocks without them
- ✅ Process payroll by 28th to allow time for bank processing before month-end
- ✅ Submit PAYE to KRA by 9th of following month (penalty = 5% per month)
- ✅ Keep payroll records for 7 years (KRA requirement)
- ✅ Reconcile payroll to GL (General Ledger) every month

### DON'T:
- ❌ Never process payroll for an employee without a KRA PIN — it is illegal
- ❌ Don't submit NHIF payment with wrong employee IDs — they may be rejected
- ❌ Never share payslip data outside the system — salary information is confidential

---

## 8. COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "Employee X blocked — missing KRA PIN" | KRA PIN not set up in payroll profile | Add KRA PIN to employee's payroll profile |
| "PAYE calculation differs from previous month significantly" | Salary change or new employee joining | Review change log for that employee |
| "NHIF deduction shows zero" | NHIF number not set / salary below minimum | Verify NHIF number is registered in the profile |
| "P10 report shows different total from payroll summary" | Terminated employees included | Check that terminated employees are properly closed in the period |

---

## QUICK TRAINING SUMMARY — Kenya Payroll

> **What:** Complete Kenya payroll — PAYE (Finance Act 2024), NHIF, NSSF, AHL — with statutory reports.  
> **Statutory deadlines:** PAYE to KRA by 9th. NHIF/NSSF by 15th.  
> **Required data:** Every employee needs: KRA PIN, NHIF number, NSSF number, bank account.  
> **Reports:** P10 (PAYE), NHIF schedule, NSSF schedule — all generated automatically.

---
