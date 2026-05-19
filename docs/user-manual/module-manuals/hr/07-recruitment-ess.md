# Recruitment (ATS) & Employee Self-Service

---

## Recruitment — Applicant Tracking System

**Route:** `/dashboard/hr?tab=recruitment`  
**Permission required:** `hr.view`

### What It Does

The Recruitment tab embeds the full Applicant Tracking System (ATS) within the HR workspace. It manages job requisitions, candidate pipelines, interviews, offers, and hire tracking.

![Recruitment tab](../../../screenshots/captured/module-ui/hr/hr/recruitment-tab.png)
*Recruitment tab showing KPI dashboard with open requisitions, candidates, active pipelines, interviews, pending offers, hires, and time-to-hire.*

### Recruitment KPIs

| KPI | Description |
|---|---|
| Open Requisitions | Active job openings |
| Total Candidates | Candidates in the system |
| Active Pipelines | Requisitions with candidates in progress |
| Interviews This Week | Scheduled interviews in the current week |
| Pending Offers | Offers awaiting candidate decision |
| Hires This Month | Successful hires in the current month |
| Avg Time to Hire (days) | Average days from requisition to hire |
| AI Alerts | AI-generated hiring insights |

### Recruitment Navigation

| Section | Route | Description |
|---|---|---|
| Requisitions | `/dashboard/recruitment/requisitions` | All job requisitions |
| New Requisition | `/dashboard/recruitment/requisitions/new` | Create a new job opening |
| Candidates | `/dashboard/recruitment/candidates` | Candidate profiles |
| Pipeline Board | `/dashboard/recruitment/pipeline` | Kanban pipeline view |
| Interviews | `/dashboard/recruitment/interviews` | Scheduled interviews |
| Offers | `/dashboard/recruitment/offers` | Job offers |
| Pipeline Stages | `/dashboard/recruitment/stages` | Configure pipeline stages |
| Reports | `/dashboard/recruitment/reports` | Recruitment analytics |
| AI Insights | `/dashboard/recruitment/ai` | AI-generated insights |

---

## Employee Self-Service (ESS)

**Route:** `/dashboard/hr?tab=ess`  
**Permission required:** `hr.view`

### What It Does

The ESS tab gives employees direct access to their own HR records without going through HR staff. Employees can view their profile, submit leave, check attendance, download documents, and submit requests.

![ESS tab](../../../screenshots/captured/module-ui/hr/hr/ess-tab.png)
*Employee Self-Service tab showing personal KPIs and navigation links.*

### ESS KPIs (Personal Dashboard)

| KPI | Description |
|---|---|
| Annual Leave Available | Remaining annual leave days |
| Pending Leave Requests | Leave requests awaiting approval |
| Attendance This Month | Days attended in the current month |
| Pending Requests | Other pending HR requests |
| Unread Notifications | Unread ESS notifications |

### ESS Navigation

| Section | Route | Description |
|---|---|---|
| My Profile | `/dashboard/ess/profile` | Employee personal and contact details |
| Leave | `/dashboard/ess/leave` | Submit and track leave requests |
| Attendance | `/dashboard/ess/attendance` | View own attendance records |
| Documents | `/dashboard/ess/documents` | Download payslips, contracts, letters |
| My Requests | `/dashboard/ess/requests` | All submitted HR requests |
| Notifications | `/dashboard/ess/notifications` | HR notifications |
| AI Insights | `/dashboard/ess/ai` | AI-generated personal insights |
| HR Admin | `/dashboard/ess/admin` | HR admin panel (admin only) |
