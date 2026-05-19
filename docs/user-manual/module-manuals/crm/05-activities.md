# Activity Timeline

**Route:** `/dashboard/crm?tab=activities`  
**Permission required:** `crm.view`

## What It Does

The Activities tab shows a chronological timeline of all CRM activities across all records. Each activity card displays the type, subject, status, assigned rep, due date, and description. Overdue planned activities are highlighted in red.

![Activities tab](../../../screenshots/captured/module-ui/crm/crm/activities-tab.png)
*Activities timeline showing colored activity cards with type, status, rep, and due date.*

## Filters

| Filter | Description |
|---|---|
| Overdue Only | Shows only planned activities past their due date |
| Status | Filter by result status |
| Type | Filter by activity type |

## Activity Card

Each card shows:
- **Type abbreviation** (colored circle) — first two letters of activity type
- **Subject** — activity title
- **Type label** — e.g., Call, Email, Meeting
- **Result status** — colored text
- **Assigned rep** (if set)
- **Due date** — red if overdue
- **Description** — free text detail
- **Next step** — next action planned
- **Outcome code** — if completed
- **View Record** link — navigates to the parent CRM record

## Activity Types

| Value | Label |
|---|---|
| `CALL` | Call |
| `EMAIL` | Email |
| `MEETING` | Meeting |
| `WHATSAPP` | WhatsApp |
| `VISIT` | Site Visit |
| `TASK` | Task |
| `NOTE` | Note |
| `DEMO` | Demo |
| `SAMPLE_SENT` | Sample Sent |
| `QUOTATION_SENT` | Quotation Sent |
| `NEGOTIATION` | Negotiation |
| `COMPLAINT_FOLLOWUP` | Complaint Follow-up |
| `OTHER` | Other |

## Result Statuses

| Value | Color | Description |
|---|---|---|
| `PLANNED` | Blue | Scheduled, not yet done |
| `COMPLETED` | Green | Done |
| `NO_RESPONSE` | Amber | Attempted, no reply |
| `RESCHEDULED` | Purple | Moved to new date |
| `CANCELLED` | Grey | Cancelled |

## Completing an Activity

Click `Complete` on any PLANNED activity card to mark it `COMPLETED`. This calls `POST /api/v1/crm/activities/{id}/complete` with `result_status: "COMPLETED"`.

## Creating Activities

Activities are created from the record detail page at `/dashboard/crm/records/{id}`, not from the timeline view directly.
