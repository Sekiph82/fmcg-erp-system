# Shop Floor Operations

**Route:** `/dashboard/shop-floor`  
**Permission required:** authenticated ERP access plus `production.view`, or an assigned production-line scope with `shop_floor.view_own_scope` / `production.view_own_scope`
**Workspace tabs:** Overview, Terminal, Supervisor, Queue, Downtime, Handover  
**Auto-refresh:** Every 30 seconds

---

## What It Does

The Shop Floor module is the real-time factory execution layer. Operators log in at the terminal to start, pause, and finish work orders. Supervisors monitor all lines from the supervisor console. Downtime events are logged and categorised. Shifts are handed over with documented records.

The dashboard auto-refreshes every 30 seconds to reflect live factory status.

![Shop Floor workspace](../../../screenshots/captured/module-ui/manufacturing/shop-floor/overview-tab.png)
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

![Shop Floor — Operator Terminal](../../../screenshots/captured/module-ui/manufacturing/shop-floor/terminal-tab.png)
*Operator Terminal: full-screen touch interface for starting, pausing, and completing work orders.*

The Operator Terminal is a full-screen, simplified interface designed for use on touch screens and shared factory tablets.

Before recording an action, start an operator session. The session captures an operator name (optionally linked to an operator profile), line/station, work center, machine, and shift. The terminal shows the selected context and includes the session on work-order activity and downtime records. Equipment and shift choices come from the configured master records; those fields remain optional when no virtual-factory record is configured. End the session explicitly when leaving the shared terminal. A typed virtual operator name is contextual data, not authentication or proof of employee identity.

### Connectivity requirement

Shop Floor is online-only for current work-order reads and authoritative production, material, QC, scrap, downtime, and note writes. Offline actions are not queued or replayed. If connectivity fails during a save, treat the result as unconfirmed; reconnect, refresh the work order/session state, and reconcile the server record before retrying. This is the initial virtual ERP policy; no real factory network or device acceptance is implied. See [`M23_S03_T002_OFFLINE_POLICY_V01.md`](../../../../coordination/milestones/M23/M23_S03_T002_OFFLINE_POLICY_V01.md) for the implementation boundary.

### Access and action permissions

Every Shop Floor API request requires an authenticated ERP user. Aggregate dashboards, supervisor alerts, active-session listings, overrides, and AI recommendations require broad production view access. A scoped viewer must request a specific production line and have that line in their assigned `production_line` view scope.

Starting an operator session or recording work-order activity requires `production.edit` / `production.edit_all`, or `production.edit_own_scope` / `production_execution.update_own_line` together with edit access to the assigned production line. The work order must match the active session's line, and the session is bound to the authenticated ERP user. A typed operator label and optional operator profile remain contextual fields; they cannot grant access or impersonate an ERP user.

Approving a shift handover, applying a supervisor override, running shop-floor AI, or accepting/rejecting a recommendation requires `production.approve`. The authenticated user ID is retained separately from the virtual operator/supervisor display name on session, activity, downtime, handover, override, and recommendation action records. Frontend visibility and disabled controls improve usability; the API permission checks remain authoritative.

Key functions:
- **Start** a work order — operator selects the work order to begin; records start time and the active session context
- **Pause** a work order — records pause time and reason (downtime category)
- **Resume** a paused work order
- **Finish** a work order — records completion time, final good/scrap/rework quantities, and optional actual run time in minutes. The operation start and completion timestamps are captured by the system; an unknown actual runtime remains unset rather than being fabricated.
- **Confirm material consumption** — the Materials panel lists only materials assigned to the started execution operation. Consumption requires an active authenticated operator session, a previously issued quantity, and (when multiple issued lot references exist) a selection from those recorded lots. It updates the separate `exec_*` material totals and appends an operation activity record; it does not post inventory movements or infer a link to the standard production-order model. Lot references are trace labels only because the current model does not allocate issued quantity per lot.
- **Record in-process QC checkpoints** — a quality user with line and product-category permissions can append a named PASS/FAIL observation, optional measured value/unit, and notes to the active operation. Each checkpoint is actor-attributed; retesting a failed checkpoint updates its current outcome while preserving history. Operations marked QC-required cannot finish until at least one checkpoint exists and every recorded checkpoint currently passes. This lightweight execution record does not invent specification limits or replace configured QMS inspection templates; the entered result is the quality user's recorded observation.
- **Record scrap / waste** — records a positive operation-level quantity, an optional normal/abnormal classification, and an optional reason against the active `exec_*` work order. Shop Floor keeps this separate from `waste_records`; no production-order crosswalk or duplicate posting is inferred.
- **Log downtime** — an active operator session may record downtime against its matching work order and line. An authenticated user with line edit permission may also record line-level downtime without an operator session; work-order-linked downtime still requires the matching authenticated session. The system derives operation and parent execution links from the work order and calculates duration when the event is stopped.

The terminal is accessible directly at `/dashboard/shop-floor/terminal` (standalone page, no sidebar).

---

## Supervisor Tab

**Tab key:** `supervisor`  
**Route:** `/dashboard/shop-floor/supervisor/page`

![Shop Floor — Supervisor Console](../../../screenshots/captured/module-ui/manufacturing/shop-floor/supervisor-tab.png)
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

![Shop Floor — Queue tab](../../../screenshots/captured/module-ui/manufacturing/shop-floor/queue-tab.png)
*Work Center Queue — Kanban board showing work orders organised by production line.*

The Work Center Queue is a Kanban-style board showing all work orders organised by production line. Columns represent production lines; cards represent work orders with their current status, target quantity, and operator.

Supervisors can drag work orders between time slots or reassign them to different work centers from this view.

---

## Downtime Tab

**Tab key:** `downtime`  
**Route:** `/dashboard/shop-floor/downtime/page`

![Shop Floor — Downtime tab](../../../screenshots/captured/module-ui/manufacturing/shop-floor/downtime-tab.png)
*Downtime tab showing open and resolved downtime events with category and impact level.*

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

![Shop Floor — Handover tab](../../../screenshots/captured/module-ui/manufacturing/shop-floor/handover-tab.png)
*Handover tab with shift transfer records, approval status, and open items being handed over.*

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
