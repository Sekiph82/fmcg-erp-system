# Kenya Go-Live ERP Training Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** All Kenya staff — first-time ERP users going live  
**Purpose:** Step-by-step visual guide for the Kenya go-live. Covers login, navigation, daily tasks for each role, and the first 30 days.

---

## Table of Contents

1. [Welcome & Getting Started](#1-welcome--getting-started)
2. [Logging In](#2-logging-in)
3. [Navigating the ERP](#3-navigating-the-erp)
4. [Your Daily Workflow — Quick Visual Tour](#4-your-daily-workflow--quick-visual-tour)
5. [Role-Based Quick Start Guides](#5-role-based-quick-start-guides)
   - [Procurement Officer](#procurement-officer)
   - [Finance / Accountant](#finance--accountant)
   - [Production Manager](#production-manager)
   - [Quality Officer](#quality-officer)
   - [Warehouse / Store Keeper](#warehouse--store-keeper)
   - [Sales Representative](#sales-representative)
   - [HR Officer](#hr-officer)
   - [System Administrator](#system-administrator)
6. [Kenya-Specific Configurations](#6-kenya-specific-configurations)
7. [Go-Live Checklist](#7-go-live-checklist)
8. [First 30 Days Guide](#8-first-30-days-guide)
9. [Common Questions (FAQ)](#9-common-questions-faq)
10. [Support Contacts](#10-support-contacts)

---

## 1. Welcome & Getting Started

**Congratulations on going live with FMCG ERP!**

This manual is your first visual guide. It does not cover every feature — it covers what you need to know to start working effectively from Day 1.

**What this system does for your business:**
- Replaces manual Excel-based ordering, stock tracking, and payroll
- Connects all departments so everyone sees the same real-time data
- Provides automated compliance (eTIMS for KRA, NSSF, NHIF)
- Gives management instant visibility into business performance

**House rules for the system:**
1. Never share your password with anyone
2. Log out when leaving your desk
3. If you make a mistake, do not delete — speak to your supervisor
4. If something looks wrong, raise a Helpdesk ticket — do not try to fix it yourself

---

## 2. Logging In

![Login Page](../../user-manual/screenshots/captured/001_login.png)
*The ERP login page — enter your email and password provided by IT.*

**URL:** `http://[your-company-erp-address]/login`

**Steps:**
1. Open Chrome or Edge (do not use Internet Explorer)
2. Type the ERP URL in the address bar
3. Enter your username (given to you by IT)
4. Enter your password (given to you by IT at training)
5. Click **Sign In**

**First login:** You will be prompted to change your password. Choose something you will remember — at least 8 characters with a number.

**Forgot password:** Click "Forgot password?" on the login page → enter your email → check your inbox for a reset link.

**Account locked?** Contact IT or your System Administrator — your account locks after 5 wrong password attempts.

---

## 3. Navigating the ERP

![Dashboard](../../user-manual/screenshots/captured/002_dashboard.png)
*Main dashboard after login — KPI cards, quick links, and notifications.*

### The Left Sidebar

![Sidebar Navigation](../../user-manual/screenshots/captured/module-ui/kenya-go-live/sidebar-navigation.png)
*The left sidebar — your main navigation. Modules listed depend on your role and permissions.*

The left sidebar shows all modules you have access to. Click any item to go to that module. If you don't see a module, your role doesn't have access — contact your administrator.

**Common sidebar items:**

| Sidebar Item | What you find there |
|-------------|---------------------|
| Dashboard | Home screen with KPIs |
| Procurement | Purchase requests and orders |
| Inventory | Stock management |
| Production | Work orders and planning |
| Quality | QC inspections |
| Sales | Customer orders and invoicing |
| Finance | Accounts, cashbook, payroll |
| HR | Employee records and leave |
| Documents | Document library |
| Helpdesk | Raise a support ticket |
| Approvals | Items waiting for your approval |

### The Top Navigation
- **Bell icon** — notifications (approvals waiting, alerts, system messages)
- **User icon (top right)** — your profile, logout, settings
- **Search bar** — search across all modules

### Tabs within a Module
Most modules have multiple tabs at the top. Click a tab to switch section. Your current tab is underlined.

### Common Buttons
| Button | Meaning |
|--------|---------|
| **+ New [Item]** | Create a new record |
| **Save** | Save changes |
| **Submit** | Submit for approval |
| **Approve** | Approve a pending request |
| **Export** | Download as Excel or PDF |
| **Filter** | Narrow down the list |

---

## 4. Your Daily Workflow — Quick Visual Tour

### What a Module Looks Like

![Module Overview Example](../../user-manual/screenshots/captured/module-ui/kenya-go-live/module-overview-example.png)
*Example module view — Procurement. Notice the tabs at top, list of records in the middle, and action buttons.*

Every module has the same layout pattern:
1. **Tabs** across the top — switch between sections (e.g. Requests, Orders, Deliveries)
2. **Filter / Search** bar — narrow down the list
3. **Table of records** — the main data list
4. **Action buttons** — top-right: "+ New", Export, etc.
5. **Row actions** — click a row to open detail; icons on right for quick actions

### Creating Something New (Sales Example)

![Create Workflow Example](../../user-manual/screenshots/captured/module-ui/kenya-go-live/create-workflow-example.png)
*Sales module — orders list with "New Order" button and filters. Same layout pattern for all create workflows.*

**Every "create" workflow follows the same steps:**
1. Click **+ New [Item]** button
2. A form or modal appears — fill in required fields (marked with \*)
3. Click **Save** or **Submit**
4. Record appears in the list

### The Approvals Queue

![Approvals Queue](../../user-manual/screenshots/captured/module-ui/kenya-go-live/approvals-queue.png)
*Approvals queue — everything waiting for your decision in one place.*

If you have an approval role (manager, department head, finance officer), you will see pending items in:
- **Left sidebar → Approvals**
- **Bell notification** (number badge)

Click any pending item to review and approve or reject.

### Analytics and Reports

![Reports and Filters](../../user-manual/screenshots/captured/module-ui/kenya-go-live/reports-filter-example.png)
*Analytics module — select date range, module, and KPI to view business performance.*

Management uses the Analytics module to review performance. You do not need to know this on Day 1 but your manager will show you which reports relate to your department.

---

## 5. Role-Based Quick Start Guides

### Procurement Officer

**Your modules:** Procurement · Inventory  
**Route:** `/dashboard/procurement`

![Procurement Overview](../../user-manual/screenshots/captured/029_procurement.png)
*Procurement module — your main workspace.*

**Your daily job in ERP:**

**Morning:**
1. Check **Approvals** → any approved PRs to convert to POs?
2. Check **Procurement → Deliveries** → any expected deliveries today? Confirm receipt when supplier delivers.
3. Check **Procurement → Suggestions** → any reorder alerts?

**Creating a Purchase Requisition:**
1. Procurement → **+ New Request**
2. Fill in: Item, Quantity, Required Date, Priority, Department
3. Click **Submit** → goes to your manager for approval

**Receiving Goods from a Supplier:**
1. Procurement → Deliveries → find the expected delivery
2. Click **Receive**
3. Enter actual quantities received (can be less than ordered)
4. Record batch numbers if required
5. Click **Confirm Receipt**

**What to do if a supplier delivers the wrong item:**
1. Do NOT accept wrong goods into the system
2. Record a discrepancy on the delivery
3. Contact supplier immediately
4. Raise a Helpdesk ticket if unsure how to handle

---

### Finance / Accountant

**Your modules:** Finance · Cashbook · Payroll  
**Route:** `/dashboard/finance`

![Finance Overview](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/overview-tab.png)
*Finance hub — your workspace for accounts, cashbook, and payroll.*

**Your daily job in ERP:**

**Morning:**
1. Check **Approvals** → any journals or invoices to approve?
2. Check **Finance → Receivables** → any overdue invoices to follow up?
3. Check **Finance → eTIMS** → any failed submissions to fix?

**Posting a Journal Entry:**
1. Finance → Accounting → **+ New Journal**
2. Set date and reference
3. Add debit lines and credit lines (must balance)
4. Click **Save Draft**
5. When ready, click **Submit for Approval**

**Reconciling Bank:**
1. Download statement from your bank
2. Finance → Bank Reconciliation → **Import Statement**
3. Review auto-matched items (green)
4. Match remaining items manually
5. Post any bank charges as journals
6. Close period when complete

**Running Payroll:**
1. Finance → Payroll → **New Payroll Period**

![Payroll Overview](../../user-manual/screenshots/captured/module-ui/finance-payroll/payroll/overview-tab.png)
*Payroll workspace — click "New Payroll Period" to start monthly payroll.*

2. Select month and year
3. Click **Generate**
4. Review exceptions
5. **Approve** → **Post** → **Pay**

---

### Production Manager

**Your modules:** Production · Planning · Shop Floor  
**Route:** `/dashboard/production`

![Production Overview](../../user-manual/screenshots/captured/038_production.png)
*Production module — plans, work orders, scheduling, OEE.*

**Your daily job in ERP:**

**Morning:**
1. Check **Production → Plans** → any plans to confirm today?
2. Check **Production → Work Orders** → any work orders to release to shop floor?
3. Check **Production → OEE** → last shift OEE performance
4. Check **Approvals** → any work orders awaiting your approval?

**Creating a Production Plan:**
1. Production → Plans → **+ New Plan**
2. Set name, dates, and products
3. Add work orders (or they will be added individually)
4. Click **Confirm Plan**

**Releasing a Work Order:**
1. Production → Work Orders → find CONFIRMED work order
2. Click **Release** → status changes to RELEASED
3. Work order now visible on Shop Floor terminal

**Handling a Breakdown:**
1. Shop Floor → Breakdowns → **+ Log Breakdown** (or let maintenance log it)
2. Notify Maintenance team
3. Update production plan if schedule affected

---

### Quality Officer

**Your modules:** Quality · Compliance  
**Route:** `/dashboard/quality`

![Quality Overview](../../user-manual/screenshots/captured/062_quality.png)
*Quality module — QC inspections, certificates, allergens, and complaints.*

**Your daily job in ERP:**

**Morning:**
1. Quality → Inspections → filter by Status = PENDING
2. Complete pending inspections
3. Check Quality → Consumer Complaints → any new complaints?

**Creating an Inspection:**
1. Quality → Inspections → **+ New Inspection**
2. Select inspection type, product, batch
3. Set inspector and scheduled date
4. Click **Save**

**Recording Inspection Results:**
1. Open the inspection
2. Enter test results against each parameter
3. If all within spec → set Decision = **PASS**
4. If outside spec → set Decision = **FAIL** → system creates non-conformance record
5. Submit

**What to do if QC fails:**
1. Immediately quarantine the batch (Inventory → WMS → Quarantine)
2. Notify Production Manager
3. Complete the Non-Conformance Report in Quality
4. Await disposition decision (rework / reject / accept with deviation)

---

### Warehouse / Store Keeper

**Your modules:** Inventory · WMS · Warehouses  
**Route:** `/dashboard/inventory`

![Inventory Overview](../../user-manual/screenshots/captured/017_inventory.png)
*Inventory module — stock levels, movements, and transactions.*

![WMS Overview](../../user-manual/screenshots/captured/025_wms.png)
*WMS — zones, bin locations, quarantine, and pick waves.*

**Your daily job in ERP:**

**Morning:**
1. Inventory → Stock → check stock levels for items flagged low
2. WMS → Quarantine → any items to release after QC clearance?
3. Check pending deliveries for today

**Receiving Goods:**
1. Procurement → Deliveries → find your delivery
2. Count physical goods against delivery note
3. Record quantities and batch numbers in ERP
4. Click **Confirm Receipt**
5. Put away stock in correct bin location
6. Update WMS → Locations if manually tracking bins

**Issuing Stock to Production:**
1. Inventory → Issue tab → **+ New Issue**
2. Select material, quantity, and work order reference
3. Confirm → stock reduces immediately

**Doing a Stock Count:**
1. Inventory → Cycle Count → find your assigned count
2. Print count sheet
3. Physically count items
4. Enter actual counts in ERP
5. Submit for review (supervisor approves adjustment)

---

### Sales Representative

**Your modules:** Sales · CRM  
**Route:** `/dashboard/sales`

![Sales Overview](../../user-manual/screenshots/captured/module-ui/sales/sales/overview-tab.png)
*Sales module — orders, invoices, customers, and performance KPIs.*

**Your daily job in ERP:**

**Morning:**
1. Sales → Orders → filter by your name as Sales Rep
2. Check status of pending orders — any to confirm or dispatch?
3. CRM → Activities → what follow-ups are due today?

**Creating a Sales Order:**
1. Sales → Orders → **+ New Order**
2. Select customer (must exist in system)
3. Set delivery date and payment terms
4. Add product lines with quantities
5. Click **Confirm Order**

**Checking Available Stock Before Promising Delivery:**
Before confirming a date, check:
- Inventory → Stock → Available column for the product
- Available = On Hand minus Reserved

**Creating a Quote:**
1. Sales → Quotes → **+ New Quote**
2. Fill in customer, products, prices, and expiry date
3. Save and email to customer
4. When customer accepts → **Convert to Order**

---

### HR Officer

**Your modules:** HR  
**Route:** `/dashboard/hr`

![HR Overview](../../user-manual/screenshots/captured/module-ui/hr/hr/overview-tab.png)
*HR module — employees, attendance, leave, and payroll.*

**Your daily job in ERP:**

**Morning:**
1. HR → Attendance → record today's attendance (or confirm biometric import)
2. HR → Leave → check pending leave requests for approval

**Adding a New Employee:**
1. HR → Employees → **+ New Employee**
2. Fill all required fields: Name, ID, KRA PIN, NSSF, NHIF, Department, Start Date
3. Save
4. Create payroll profile in Finance → Payroll → Profiles

**Processing Leave:**
1. HR → Leave → **+ New Leave** (or employee submits via ESS)
2. Verify days against leave balance
3. Click **Submit** → goes to line manager for approval

**Monthly Attendance Summary:**
1. HR → Attendance → filter by month
2. Export to Excel
3. Share with Payroll Officer for deduction calculation

---

### System Administrator

**Your modules:** Admin · All modules  
**Route:** `/dashboard/admin`

![Admin Dashboard](../../user-manual/screenshots/captured/003_admin.png)
*Admin hub — user management, roles, permissions, and security settings.*

![Admin Users](../../user-manual/screenshots/captured/004_admin-users.png)
*Users list — create, edit, and manage user accounts.*

**Your daily job in ERP:**

**Morning:**
1. Admin → Logs → Security → check for failed login spikes
2. Admin → Users → any locked accounts to unlock?
3. Finance → eTIMS → any failed submissions from yesterday?

**Creating a New User:**
1. Admin → Users → **+ New User**
2. Enter email, name, role
3. Send welcome email with temporary password
4. Ask user to change password on first login

**Troubleshooting "I can't see X" Reports:**
1. Admin → Users → find user
2. Check their role
3. Admin → Permissions → check that role has the required permission
4. If missing → add the permission → save
5. Ask user to log out and back in

---

## 6. Kenya-Specific Configurations

### eTIMS (KRA Electronic Tax Invoice)

All customer invoices must be submitted to KRA via eTIMS. The ERP does this automatically when you post a sales invoice.

![eTIMS Tab](../../user-manual/screenshots/captured/module-ui/finance-payroll/finance/etims-tab.png)
*eTIMS submission log — status of all KRA invoice submissions.*

**For this to work:**
- Each customer must have a valid KRA PIN in their profile
- Finance → Integrations → eTIMS must be configured with your TIMS credentials

**If eTIMS submission fails:**
1. Finance → eTIMS tab
2. Find rejected invoice
3. Check error code (E001 = bad PIN, E002 = description too long, etc.)
4. Fix the issue
5. Click **Resubmit**

### PAYE Calculation

The ERP calculates PAYE using Kenya's graduated tax bands as per KRA. Ensure:
- Each employee's KRA PIN is entered
- Employee tax relief (personal relief KES 2,400/month) is set in payroll profile
- Pension contributions entered if applicable

### NSSF & NHIF/SHIF Contributions

Updated rates apply automatically. Verify in Finance → Payroll → Settings that rates match the current gazette rates.

### VAT (16%)

VAT is 16% standard rate in Kenya. Zero-rated categories (exports, basic foodstuffs) must be configured in the product master with the correct VAT code.

### M-Pesa Integration

![M-Pesa Integration](../../user-manual/screenshots/captured/134_integrations-mpesa.png)
*M-Pesa Daraja API configuration for receiving customer payments.*

M-Pesa payments auto-match to invoices when the customer uses the invoice number as their M-Pesa payment reference.

---

## 7. Go-Live Checklist

### Week Before Go-Live

- [ ] All users created and passwords communicated
- [ ] Roles and permissions configured and tested
- [ ] Opening balances entered (stock, AR, AP, bank)
- [ ] Customer master data imported and verified
- [ ] Supplier master data imported and verified
- [ ] Product and materials master data imported
- [ ] Price lists configured
- [ ] Chart of accounts configured
- [ ] eTIMS credentials configured and tested
- [ ] M-Pesa integration configured and tested
- [ ] Approval chains configured
- [ ] Users trained on their specific role workflows
- [ ] Parallel run completed (manual + ERP simultaneously)

### Go-Live Day

- [ ] Data migration complete and verified
- [ ] All users able to log in
- [ ] First live transactions created and confirmed
- [ ] IT support on standby for Day 1
- [ ] Escalation contact list shared with all department heads
- [ ] Backup confirmed for that night

### Week 1 After Go-Live

- [ ] All daily workflows running through ERP
- [ ] No critical issues unresolved
- [ ] First week report reviewed with management
- [ ] Helpdesk tickets triaged and responded to

---

## 8. First 30 Days Guide

| Period | Focus |
|--------|-------|
| Days 1–5 | Core transactions only — orders, GRNs, invoices |
| Days 6–10 | Payroll set up; first payroll run reviewed |
| Days 11–15 | Quality inspections workflow bedded in |
| Days 16–20 | First month-end bank reconciliation |
| Days 21–25 | Reports and analytics reviewed with managers |
| Days 26–30 | VAT return prepared; eTIMS audit; lessons learned session |

**Common issues in first 30 days and fixes:**

| Issue | How to handle |
|-------|--------------|
| Supplier doesn't exist in system | Add supplier before raising PO |
| Customer invoice bouncing on eTIMS | Check KRA PIN; update and resubmit |
| Stock balance wrong | Check opening balances; may need adjustment |
| User can't find their module | Check role — may need permission added |
| Payroll amount incorrect | Check payroll profile — verify salary and deductions |

---

## 9. Common Questions (FAQ)

**Q: Can I undo an action in the ERP?**  
A: Depends on the action. You can edit DRAFT documents before posting. Posted journals require a reversal entry — do not delete. Contact Finance Manager or raise a Helpdesk ticket.

**Q: The system is slow — what do I do?**  
A: Check your internet connection first. If internet is fine, raise a Helpdesk ticket with the time it happened and what you were doing.

**Q: I entered the wrong quantity on a goods receipt — can I fix it?**  
A: If not yet confirmed: edit the delivery record. If already confirmed: contact your Warehouse Manager — a correction entry must be made.

**Q: Someone else can see my sensitive data — is that right?**  
A: Contact your System Administrator. Role permissions may need adjusting.

**Q: The month is over — can I still post a transaction last month?**  
A: Depends on whether the period is closed. Contact Finance — they control period closure. Do not post backdated entries without Finance approval.

**Q: How do I print from the ERP?**  
A: Open the document (invoice, PO, etc.) → click **Print** or **Export to PDF** → print from your browser.

---

## 10. Support Contacts

**Internal IT Helpdesk:**
- Route: Helpdesk module (in the ERP left sidebar)

![Helpdesk](../../user-manual/screenshots/captured/140_helpdesk.png)
*Helpdesk — raise a support ticket from anywhere in the system.*

- Email: it@[company].co.ke
- Phone: [internal extension]

**ERP System Administrator:**
- Name: [Admin name]
- Email: [admin email]
- Available: Monday–Friday 8am–5pm

**Finance Queries:**
- Contact your Finance Manager for eTIMS, payroll, and tax questions

**Emergency (system down):**
- Contact IT Manager directly: [mobile number]

---

*End of Kenya Go-Live ERP Training Manual v2*
