# Pipeline Board

**Route:** `/dashboard/crm?tab=pipeline`  
**Permission required:** `crm.view`

## What It Does

The Pipeline Board is a Kanban view of all open CRM records grouped by stage. Cards can be dragged between columns to move a record to a different stage. Terminal stages are hidden from the board.

![Pipeline Board tab](../../../screenshots/captured/module-ui/crm/crm/pipeline-tab.png)
*Pipeline Board showing stage columns with draggable deal cards.*

## Board Layout

Each stage column shows:
- Stage name and color accent (top border)
- Record count badge
- Total expected revenue for that stage
- Cards for each open record

## Deal Cards

Each card displays:
- Company name
- Temperature dot (color: Cold = grey, Warm = amber, Hot = red)
- Lead code or opportunity code
- Expected revenue (if set)
- Probability percentage
- Expected close date (if set)
- `View` link → `/dashboard/crm/records/{id}`
- "View only" badge if record is outside the user's territory scope

## Drag-and-Drop

Users with edit permission can drag a card from one stage to another. On drop, the system calls `PATCH /api/v1/crm/records/{id}` with the new `stage_id`. Records marked `can_edit: false` cannot be dragged.

## Pipeline Summary Footer

| Field | Description |
|---|---|
| Total Open | Count of all open records |
| Pipeline Value | Sum of `expected_revenue` |
| Weighted Value | Sum of `expected_revenue × probability_pct / 100` |

## Stage Types

| Type | Behavior |
|---|---|
| `LEAD` | Lead stage — appears on board |
| `OPPORTUNITY` | Opportunity stage — appears on board |
| `NURTURING` | Long-term nurture — appears on board |
| `TERMINAL` | Won/Lost — hidden from board |
