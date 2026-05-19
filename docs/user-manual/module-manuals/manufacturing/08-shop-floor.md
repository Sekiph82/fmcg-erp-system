# Shop Floor Operations

**Route:** `/dashboard/shop-floor`  
**Permission required:** `production.view`  
**Workspace tabs:** Overview, Terminal, Supervisor, Queue, Downtime, Handover  
**Auto-refresh:** Every 30 seconds

---

## What It Does

The Shop Floor module is the real-time factory execution layer. Operators log in at the terminal to start, pause, and finish work orders. Supervisors monitor all lines from the supervisor console. Downtime events are logged and categorised. Shifts are handed over with documented records.

The dashboard auto-refreshes every 30 seconds to reflect live factory status.

![Shop Floor workspace](../../../screenshots/captured/tabs/shop-floor-overview.png)
*Shop Floor dashboard showing live KPI tiles: active sessions, running work orders, good quantity today, and help requests.*

---

## Overview Tab

**Tab key:** `overview`

### Dashboard KPIs

| KPI | Field | Colour |
|-----|-------|--------|
| Active Sessions | `active_sessions` | Indigo |
| Running WOs | `running_work_orders` | Green |
| Paused WOs | `paused_work_orders` | Yellow |
| QC Holds | `qc_hold_count` | Purple |
| Active Downtime | `active_downtime_count` | Red |
| Help Requests | `help_requests_open` | Orange |
| Good Qty Today | `total_good_qty_today` (rounded to 0 dp) | Teal |
| Scrap Today | `total_scrap_today` (rounded to 0 dp) | Red-400 |
| Pending AI Recs | `pending_ai_recs` | Blue |
| Overrides Today | `supervisor_overrides_today` | Grey |

### Alerts Panel

Active alerts are shown when present. Alerts with severity `HIGH` or `CRITICAL` are displayed on a red background; others on yellow. Each alert shows:
- `type` — alert category (e.g. "QC_HOLD", "DOWNTIME", "HELP_REQUEST")
- `message` — human-readable description

### Active Downtime Panel

Shows currently open downtime events with:
- `downtime_category` — displayed as human-readable label
- `line_id` — production line identifier
- `machine_name` — specific machine affected
- Elapsed minutes since `start_time`
- `impact_level` — coloured badge

### Recent Handovers Panel

Shows the 4 most recent shift handover records with:
- `shift_from_name` → `shift_to_name`
- `line_id` or "All lines"
- `outgoing_supervisor`
- Approved / Pending status badge

### Quick Navigation Cards

| Card | Route | Description |
|------|-------|-------------|
| Operator Terminal | `/dashboard/shop-floor/terminal` | Start, pause, finish work orders |
| Work Center Queue | `/dashboard/shop-floor/queue` | Live WO board by production line |
| Downtime Board | `/dashboard/shop-floor/downtime` | Track and categorise interruptions |
| Shift Handover | `/dashboard/shop-floor/handover` | Document shift transfer records |

### Action Buttons (header)

| Button | Action |
|--------|--------|
| **Run AI Agents** | Triggers AI analysis of current shop floor state; invalidates dashboard cache on completion |
| **Operator Terminal** | Direct link to `/dashboard/shop-floor/terminal` |
| **Supervisor Console** | Direct link to `/dashboard/shop-floor/supervisor` |

---

## Terminal Tab

**Tab key:** `terminal`  
**Route:** `/dashboard/shop-floor/terminal/page`

![Shop Floor — Operator Terminal](../../../screenshots/captured/tabs/shop-floor-terminal.png)
*Operator Terminal: full-screen touch interface for starting, pausing, and completing work orders.*

The Operator Terminal is a full-screen, simplified interface designed for use on touch screens and shared factory tablets.

Key functions:
- **Start** a work order — operator selects their work center and the work order to begin; records start time and operator ID
- **Pause** a work order — records pause time and reason (downtime category)
- **Resume** a paused work order
- **Finish** a work order — records completion time, good quantity produced, and scrap quantity

The terminal is accessible directly at `/dashboard/shop-floor/terminal` (standalone page, no sidebar).

---

## Supervisor Tab

**Tab key:** `supervisor`  
**Route:** `/dashboard/shop-floor/supervisor/page`

![Shop Floor — Supervisor Console](../../../screenshots/captured/tabs/shop-floor-supervisor.png)
*Supervisor Console showing all lines, active work orders, and override controls.*

The Supervisor Console provides a manager-level view of all active work orders across all lines. Key capabilities:
- Override AI recommendations (recorded as `supervisor_overrides`)
- Approve or reject help requests from operators
- Trigger QC holds on specific batches or lines
- View real-time OEE per work center

The supervisor console is accessible directly at `/dashboard/shop-floor/supervisor` (standalone page).

---

## Queue Tab

**Tab key:** `queue`  
**Route:** `/dashboard/shop-floor/queue/page`

The Work Center Queue is a Kanban-style board showing all work orders organised by production line. Columns represent production lines; cards represent work orders with their current status, target quantity, and operator.

Supervisors can drag work orders between time slots or reassign them to different work centers from this view.

---

## Downtime Tab

**Tab key:** `downtime`  
**Route:** `/dashboard/shop-floor/downtime/page`

### Downtime Categories

Downtime events are categorised to enable root-cause analysis and OEE calculation. The `DOWNTIME_CAT_LABEL` map translates category codes to human-readable labels. Typical categories:

| Category Code | Display Label |
|---------------|---------------|
| `BREAKDOWN` | Machine Breakdown |
| `PLANNED_MAINTENANCE` | Planned Maintenance |
| `CHANGEOVER` | Product Changeover |
| `MATERIAL_SHORTAGE` | Material Shortage |
| `QUALITY_HOLD` | Quality Hold |
| `UTILITIES` | Utilities Failure |
| `OPERATOR_ABSENCE` | Operator Absence |
| `OTHER` | Other |

### Impact Level

| Level | Badge Colour | Meaning |
|-------|-------------|---------|
| `LOW` | Grey | Minor delay; line continues |
| `MEDIUM` | Yellow | Significant delay; partial output |
| `HIGH` | Orange | Line stopped; production halted |
| `CRITICAL` | Red | Multi-line or extended stoppage |

### Downtime Record Fields

| Field | Description |
|-------|-------------|
| `line_id` | Production line affected |
| `machine_name` | Specific machine (optional) |
| `downtime_category` | Root cause category |
| `impact_level` | LOW / MEDIUM / HIGH / CRITICAL |
| `start_time` | When downtime started |
| `end_time` | When downtime ended (null if still active) |

---

## Handover Tab

**Tab key:** `handover`  
**Route:** `/dashboard/shop-floor/handover/page`

Shift handover documents the formal transfer of production responsibility between shifts.

### Handover Record Fields

| Field | Description |
|-------|-------------|
| `shift_from_name` | Outgoing shift name (e.g. "Morning Shift") |
| `shift_to_name` | Incoming shift name (e.g. "Afternoon Shift") |
| `line_id` | Production line(s) covered; "All lines" if facility-wide |
| `outgoing_supervisor` | Name of outgoing supervisor |
| `is_approved` | Whether incoming supervisor has approved the handover |

A handover is not complete until the incoming supervisor marks `is_approved = true`. Pending handovers (not yet approved) are shown with a yellow badge.

### What a Handover Records

- Active work orders at shift end (status, quantity produced so far)
- Open downtime events being passed over
- Quality holds in effect
- Help requests unresolved
- Machine status notes
- Any safety incidents during the shift
