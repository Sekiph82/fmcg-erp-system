# Production Plans

**Route:** `/dashboard/production` (default tab: Plans)  
**Permission required:** `production.view`  
**Tab key:** `plans`

---

## What It Does

Production Plans group related work orders under a single planning event. A plan defines a target date, a reference number, and a name. Work orders are then raised against a confirmed plan. Plans must be **Confirmed** before work orders can be executed.

![Production workspace](../../../screenshots/captured/038_production.png)
*Production workspace showing the Plans tab with plan list, status badges, and workspace navigation.*

---

## Plans Tab

### Search

Free-text search filters by plan name or plan number (`plan_no`).

### Table Columns

| Column | Field | Notes |
|--------|-------|-------|
| **Plan No** | `plan_no` | Monospace; clickable link to plan detail at `/dashboard/production/plans/{id}` |
| **Name** | `name` | Plan description name |
| **Status** | `status` | Status badge (see Status Values below) |
| **Planned Date** | `planned_date` | Formatted as locale date string |
| **Actions** | — | Confirm button (DRAFT only) + View button |

### Status Values

| Status | Badge Colour | Meaning |
|--------|-------------|---------|
| `DRAFT` | Blue | Plan created; not yet confirmed; work orders cannot be started |
| `CONFIRMED` | Green | Plan approved; work orders can proceed |
| `IN_PROGRESS` | Green | At least one work order has started |
| `COMPLETED` | Green | All work orders completed |
| `CANCELLED` | Red | Plan cancelled; no further operations allowed |

### Confirm Action

The **Confirm** button appears on any row where `status === "DRAFT"`. Clicking it transitions the plan to `CONFIRMED` immediately. There is no additional confirmation dialog.

---

## Creating a Production Plan

**Button:** `+ New Plan` (`data-testid="production-create-plan-button"`)

### New Production Plan Modal Fields

| Field | Label | Required | Default | Notes |
|-------|-------|----------|---------|-------|
| `plan_no` | Plan No | Yes | — | User-assigned reference; e.g. `PP-2026-001` |
| `name` | Name | Yes | — | Descriptive name for this plan |
| `planned_date` | Planned Date | Yes | — | `datetime-local` input — includes time |
| `description` | Description | No | — | Optional notes |

**Submit** is disabled until both `plan_no` and `name` are filled. The `planned_date` is required by the form but the submit button enables as soon as plan_no and name are present (the datetime-local field validation is enforced by HTML5).

New plans are always created in `DRAFT` status.

---

## Plan Detail Page

**Route:** `/dashboard/production/plans/{id}`

The plan detail page shows all work orders assigned to this plan, progress tracking, and links to individual work order detail pages. From here you can also confirm the plan (same action as the list confirm button).

---

## Production Workspace Tabs

The `/dashboard/production` page contains 20 tabs covering the full production lifecycle:

| Tab Key | Label | Content |
|---------|-------|---------|
| `plans` | Plans | Production plan list and creation (this chapter) |
| `orders` | Work Orders | Work order management |
| `scheduling` | Scheduling | Gantt and scheduling board |
| `work-centers` | Work Centers | Work center capacity and configuration |
| `routing` | Routing | Operation routing for products |
| `batch-lots` | Batch / Lots | Batch and lot tracking |
| `quality-control` | QC | In-process quality control |
| `labor` | Labor | Labour assignment and tracking |
| `time-tracking` | Time Tracking | Operator time recording |
| `oee` | OEE | Overall Equipment Effectiveness |
| `downtime` | Downtime | Downtime events and root causes |
| `waste-yield` | Waste & Yield | Waste recording and yield calculations |
| `wip` | WIP | Work-in-progress inventory |
| `costing` | Costing | Production cost actuals |
| `variance` | Variance | Cost variance analysis |
| `reports` | Reports | Production reports |
| `execution` | Execution | Production execution dashboard |
| `machine-ops` | Machine Ops | Machine operations and maintenance |
| `material-flow` | Material Flow | Material movement during production |
| `projects` | Projects | Production project management |

All tabs require `production.view` permission.
